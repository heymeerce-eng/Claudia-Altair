import os
import hashlib
import hmac
import logging
import threading
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from .agent import run_agent
from .db import init_db, save_message, get_history, clear_history
from .users import get_profile, get_all_profiles
from .tools.crm_tool import create_lead as crm_create_lead, search_lead, update_lead as crm_update_lead

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "documentos"
app = Flask(__name__)


def _is_allowed(from_number: str) -> bool:
    return True


def _twilio_client() -> Client:
    return Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def _send_reply(to: str, text: str):
    """Sends a text reply via Twilio API, splitting if needed."""
    client = _twilio_client()
    from_number = os.environ["TWILIO_WHATSAPP_NUMBER"]
    if len(text) > 1500:
        parts = [text[i:i+1500] for i in range(0, len(text), 1500)]
        for part in parts:
            client.messages.create(from_=from_number, to=to, body=part)
    else:
        client.messages.create(from_=from_number, to=to, body=text)


def _send_pdf(to: str, pdf_path: str, public_url: str):
    """Sends a PDF as a media message via Twilio."""
    try:
        client = _twilio_client()
        filename = Path(pdf_path).name
        media_url = f"{public_url.rstrip('/')}/documents/{filename}"
        client.messages.create(
            from_=os.environ["TWILIO_WHATSAPP_NUMBER"],
            to=to,
            body="Aquí tienes el documento",
            media_url=[media_url],
        )
    except Exception as e:
        logger.error(f"Error sending PDF: {e}")


def _process_message(from_number: str, body: str, user_id: int, user, history: list):
    """Runs the agent in background and sends response via Twilio API."""
    try:
        response_text, pdf_path = run_agent(history, body, user=user)
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        try:
            _send_reply(from_number, "Ha habido un error. Inténtalo de nuevo.")
        except Exception:
            pass
        return

    save_message(user_id, "assistant", response_text)

    try:
        _send_reply(from_number, response_text)
    except Exception as e:
        logger.error(f"Error sending reply: {e}")

    if pdf_path and Path(pdf_path).exists():
        public_url = os.environ.get("PUBLIC_URL", "")
        if public_url:
            _send_pdf(from_number, pdf_path, public_url)
        else:
            logger.warning("PUBLIC_URL not set — cannot send PDF")


@app.route("/documents/<path:filename>")
def serve_document(filename):
    return send_from_directory(str(DOCS_DIR), filename)


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()

    if not _is_allowed(from_number):
        logger.warning(f"Unauthorized message from {from_number}")
        return "", 200

    if not body:
        return "", 200

    resp = MessagingResponse()

    # Commands — respond immediately via TwiML
    if body.lower() in ("/reset", "reset", "reiniciar"):
        user_id = hash(from_number)
        clear_history(user_id)
        resp.message("Conversacion reiniciada. En que te ayudo?")
        return str(resp)

    if body.lower() in ("/help", "ayuda", "help"):
        resp.message(
            "Lo que puedo hacer:\n\n"
            "Calendario: que tengo esta semana / crea una reunion el martes a las 10\n\n"
            "Documentos PDF: genera una propuesta para [marca] / presupuesto para [proyecto]\n\n"
            "Contenido: escribeme un guion para un Reel sobre [tema] / ideas para esta semana\n\n"
            "Memoria: recuerda que... / no olvides que...\n\n"
            "Escribe reset para reiniciar la conversacion."
        )
        return str(resp)

    user_id = hash(from_number)
    user = get_profile(from_number)
    if user:
        logger.info(f"Recognized user: {user.name} ({from_number})")
    else:
        logger.warning(f"Unknown number: {from_number} — check USER_N_WHATSAPP vars in Railway")
    history = get_history(user_id, limit=10)
    save_message(user_id, "user", body)

    # Process in background — avoids Twilio's 15-second webhook timeout
    threading.Thread(
        target=_process_message,
        args=(from_number, body, user_id, user, history),
        daemon=True,
    ).start()

    # Return empty TwiML immediately (response comes via API when ready)
    return str(resp)


@app.route("/calendly", methods=["POST"])
def calendly_webhook():
    """Auto-creates a CRM lead when someone books a Calendly call."""
    try:
        data = request.get_json(silent=True) or {}
        event_type = data.get("event", "")

        if event_type != "invitee.created":
            return "", 200

        payload = data.get("payload", {})
        invitee = payload.get("invitee", {})
        scheduled = payload.get("scheduled_event", {})

        name = invitee.get("name", "")
        email = invitee.get("email", "")
        call_name = scheduled.get("name", "Llamada de claridad")
        start_time = scheduled.get("start_time", "")

        # Parse custom questions (phone, instagram, etc.)
        telefono = ""
        instagram = ""
        notas_extra = []
        for qa in invitee.get("questions_and_answers", []):
            q = qa.get("question", "").lower()
            a = qa.get("answer", "")
            if not a:
                continue
            if any(k in q for k in ["telefono", "teléfono", "phone", "whatsapp", "número", "numero"]):
                telefono = a
            elif any(k in q for k in ["instagram", "ig", "@"]):
                instagram = a if a.startswith("@") else f"@{a}"
            else:
                notas_extra.append(f"{qa.get('question', '')}: {a}")

        # Format date
        fecha = ""
        if start_time:
            try:
                from datetime import datetime
                import pytz
                tz = pytz.timezone("Europe/Madrid")
                dt = datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S")
                dt = pytz.utc.localize(dt).astimezone(tz)
                fecha = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha = start_time[:10]

        notas = f"Reserva via Calendly: {call_name}"
        if fecha:
            notas += f" — {fecha}"
        if notas_extra:
            notas += " | " + " | ".join(notas_extra)

        if instagram:
            notas += f" | IG: {instagram}"

        if name:
            result = crm_create_lead(
                nombre=name,
                email=email,
                telefono=telefono,
                fecha_sesion=fecha,
                notas=notas,
                situacion_actual=f"Reserva via Calendly: {call_name}",
            )
            logger.info(f"Calendly lead created: {name} — {result}")

    except Exception as e:
        logger.error(f"Calendly webhook error: {e}", exc_info=True)

    return "", 200


def _extract_name_from_zoom_topic(topic: str) -> str:
    """Extracts probable invitee name from a Calendly-generated Zoom topic."""
    for pattern in [r"(?:con|with)\s+(.+?)(?:\s*[-—].*)?$", r"[-—]\s*(.+)$"]:
        m = re.search(pattern, topic, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return topic.strip()


def _get_socia_by_zoom_email(host_email: str):
    profiles = get_all_profiles()
    for profile in profiles.values():
        if profile.zoom_email and profile.zoom_email.lower() == host_email.lower():
            return profile
    return None


def _handle_zoom_recording(data: dict):
    """Processes recording.completed: updates CRM and sends WhatsApp prompt to host socia."""
    try:
        import pytz
        obj = data.get("payload", {}).get("object", {})
        topic = obj.get("topic", "Llamada")
        host_email = obj.get("host_email", "")
        start_raw = obj.get("start_time", "")
        duration = obj.get("duration", 0)

        fecha = ""
        if start_raw:
            try:
                tz = pytz.timezone("Europe/Madrid")
                dt = datetime.strptime(start_raw[:19], "%Y-%m-%dT%H:%M:%S")
                dt = pytz.utc.localize(dt).astimezone(tz)
                fecha = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha = start_raw[:10]

        lead_name = _extract_name_from_zoom_topic(topic)
        crm_result = search_lead(lead_name)

        if "No encontre" in crm_result:
            crm_create_lead(
                nombre=lead_name,
                fecha_sesion=fecha,
                notas=f"Sesion Zoom: {topic} ({duration} min)",
            )
            accion = "creado en el CRM"
        else:
            crm_update_lead(lead_name, fecha_sesion=fecha)
            accion = "fecha de sesión actualizada en el CRM"

        socia = _get_socia_by_zoom_email(host_email)
        if not socia:
            profiles = get_all_profiles()
            socia = next(iter(profiles.values()), None) if profiles else None

        if socia and socia.whatsapp:
            msg = (
                f"📞 Sesión terminada con *{lead_name}*\n"
                f"Fecha: {fecha} ({duration} min) — {accion}.\n\n"
                f"¿Me das estos datos para completar el CRM?\n"
                f"• Estado: 🔥 Caliente / 🟡 Interesada / 🔵 Potencial / ❌ No alineada\n"
                f"• Avatar: CRIBA (empieza) / CEO (escala)\n"
                f"• Precio total ofrecido\n"
                f"• Tipo de negocio\n"
                f"• Situación actual (breve contexto)\n"
                f"• Setter que hizo la llamada\n\n"
                f"Puedes responderme con lo que recuerdes y yo lo actualizo."
            )
            _send_reply(socia.whatsapp, msg)

    except Exception as e:
        logger.error(f"Zoom recording handler error: {e}", exc_info=True)


def _verify_zoom_signature(req) -> bool:
    secret = os.environ.get("ZOOM_WEBHOOK_SECRET", "")
    if not secret:
        return True
    timestamp = req.headers.get("x-zm-request-timestamp", "")
    signature = req.headers.get("x-zm-signature", "")
    body = req.get_data(as_text=True)
    message = f"v0:{timestamp}:{body}"
    expected = "v0=" + hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@app.route("/zoom-webhook", methods=["POST"])
def zoom_webhook():
    """Handles Zoom webhook events (endpoint validation + recording.completed)."""
    data = request.get_json(silent=True) or {}
    event_type = data.get("event", "")

    if event_type == "endpoint.url_validation":
        secret = os.environ.get("ZOOM_WEBHOOK_SECRET", "")
        plain_token = data.get("payload", {}).get("plainToken", "")
        encrypted = hmac.new(secret.encode(), plain_token.encode(), hashlib.sha256).hexdigest()
        return {"plainToken": plain_token, "encryptedToken": encrypted}, 200

    if not _verify_zoom_signature(request):
        return "", 403

    if event_type == "recording.completed":
        threading.Thread(target=_handle_zoom_recording, args=(data,), daemon=True).start()

    return "", 200


@app.route("/health")
def health():
    return {"status": "ok", "agent": "Claudia"}


@app.route("/debug/profiles")
def debug_profiles():
    """Dumps all USER_N_* env vars as Railway sees them, plus loaded profiles."""
    from .users import _normalize_whatsapp

    FIELDS = ["NAME", "WHATSAPP", "ROLE", "INSTAGRAM", "TARGET_PROGRAM",
              "ICLOUD_EMAIL", "ICLOUD_PASSWORD", "ZOOM_EMAIL"]
    REDACTED = {"ICLOUD_PASSWORD"}

    # Scan all USER_N blocks regardless of whether they loaded correctly
    raw_vars = {}
    for i in range(1, 10):
        block = {}
        found_any = False
        for field in FIELDS:
            key = f"USER_{i}_{field}"
            val = os.environ.get(key)
            if val is not None:
                found_any = True
            if field in REDACTED:
                block[key] = "SET" if (val and val != "xxxx-xxxx-xxxx-xxxx") else ("PLACEHOLDER" if val == "xxxx-xxxx-xxxx-xxxx" else "NOT SET")
            else:
                block[key] = val if val is not None else "NOT SET"
        if found_any:
            raw_vars[f"USER_{i}"] = block

    # Loaded profiles (from cache)
    profiles = get_all_profiles()
    loaded = {}
    for number, p in profiles.items():
        loaded[number] = {
            "name": p.name,
            "normalized": _normalize_whatsapp(number),
            "has_calendar": p.has_calendar(),
        }

    return {
        "profiles_loaded": len(loaded),
        "loaded_profiles": loaded,
        "raw_env_vars": raw_vars,
    }


def run_bot():
    init_db()
    DOCS_DIR.mkdir(exist_ok=True)

    port = int(os.environ.get("PORT", 5000))
    public_url = os.environ.get("PUBLIC_URL", "")

    if not public_url:
        try:
            from pyngrok import ngrok
            tunnel = ngrok.connect(port, "http")
            public_url = tunnel.public_url
            os.environ["PUBLIC_URL"] = public_url
            logger.info(f"ngrok tunnel: {public_url}")
            logger.info(f"Webhook URL para Twilio: {public_url}/webhook")
        except Exception as e:
            logger.warning(f"ngrok no disponible: {e}")
            logger.info(f"Webhook local: http://localhost:{port}/webhook")
    else:
        logger.info(f"Webhook: {public_url}/webhook")

    logger.info("Claudia esta online (WhatsApp).")
    app.run(host="0.0.0.0", port=port, debug=False)
