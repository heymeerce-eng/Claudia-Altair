"""
Herramienta de Calendly para Claudia.
Lee sesiones programadas con datos del invitado (nombre, tel, instagram).
"""
import os
import requests
from datetime import datetime, timezone, timedelta
import pytz

CALENDLY_API = "https://api.calendly.com"
TZ = "Europe/Madrid"

_user_uri_cache = {"uri": None}


def _headers() -> dict:
    token = os.environ.get("CALENDLY_API_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_user_uri() -> str:
    if _user_uri_cache["uri"]:
        return _user_uri_cache["uri"]
    resp = requests.get(f"{CALENDLY_API}/users/me", headers=_headers(), timeout=10)
    resp.raise_for_status()
    uri = resp.json()["resource"]["uri"]
    _user_uri_cache["uri"] = uri
    return uri


def _get_org_uri() -> str:
    resp = requests.get(f"{CALENDLY_API}/users/me", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["resource"]["current_organization"]


def _parse_invitees(event_uuid: str) -> list:
    """Returns list of dicts with invitee details."""
    try:
        resp = requests.get(
            f"{CALENDLY_API}/scheduled_events/{event_uuid}/invitees",
            headers=_headers(),
            params={"count": 10},
            timeout=10,
        )
        resp.raise_for_status()
        result = []
        for inv in resp.json().get("collection", []):
            telefono = ""
            instagram = ""
            notas = []
            for qa in inv.get("questions_and_answers", []):
                q = qa.get("question", "").lower()
                a = (qa.get("answer") or "").strip()
                if not a:
                    continue
                if any(k in q for k in ["telefono", "teléfono", "phone", "whatsapp", "número", "movil", "móvil"]):
                    telefono = a
                elif any(k in q for k in ["instagram", "ig", "@"]):
                    instagram = a if a.startswith("@") else f"@{a}"
                elif q not in ("nombre", "name", "email", "correo"):
                    notas.append(f"{qa.get('question', '')}: {a}")
            result.append({
                "nombre": inv.get("name", ""),
                "email":  inv.get("email", ""),
                "telefono": telefono,
                "instagram": instagram,
                "notas": " | ".join(notas),
                "uri": inv.get("uri", ""),
            })
        return result
    except Exception:
        return []


def _detect_setter(event_name: str) -> str:
    """Tries to identify the setter from the event name."""
    name_lower = event_name.lower()
    for setter in ["sofi", "tamara", "estefi"]:
        if setter in name_lower:
            return setter.capitalize()
    return ""


def get_upcoming_sessions(days: int = 7) -> str:
    """Returns upcoming Calendly sessions with full invitee info."""
    try:
        user_uri = _get_user_uri()
        org_uri = _get_org_uri()

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)

        resp = requests.get(
            f"{CALENDLY_API}/scheduled_events",
            headers=_headers(),
            params={
                "organization": org_uri,
                "status": "active",
                "min_start_time": now.isoformat(),
                "max_start_time": end.isoformat(),
                "count": 25,
                "sort": "start_time:asc",
            },
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json().get("collection", [])

        if not events:
            return f"No hay sesiones de Calendly en los proximos {days} dias."

        tz = pytz.timezone(TZ)
        lines = []
        for event in events:
            start_raw = event.get("start_time", "")
            event_name = event.get("name", "Llamada")
            event_uuid = event.get("uri", "").split("/")[-1]
            setter = _detect_setter(event_name)

            start_str = start_raw
            if start_raw:
                try:
                    dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    dt = dt.astimezone(tz)
                    start_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            invitees = _parse_invitees(event_uuid)
            block = [f"📅 {start_str} — {event_name}"]
            if setter:
                block.append(f"   Setter: {setter}")
            for inv in invitees:
                inv_line = f"   • {inv['nombre']}"
                if inv.get("telefono"):   inv_line += f" | Tel: {inv['telefono']}"
                if inv.get("instagram"):  inv_line += f" | IG: {inv['instagram']}"
                if inv.get("email"):      inv_line += f" | {inv['email']}"
                if inv.get("notas"):      inv_line += f"\n     Notas: {inv['notas']}"
                block.append(inv_line)
            lines.append("\n".join(block))

        return f"Sesiones proximas ({len(events)}):\n\n" + "\n\n".join(lines)

    except Exception as e:
        return f"Error obteniendo Calendly: {e}"


def export_sessions_to_sheet(sheet_name: str = "Leads calendly", days: int = 730) -> str:
    """Exports all past Calendly sessions with invitee form data to a Google Sheet."""
    import gspread
    from google.oauth2.service_account import Credentials
    from pathlib import Path
    from urllib.parse import urlparse, parse_qs

    try:
        org_uri = _get_org_uri()
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        all_events = []
        params = {
            "organization": org_uri,
            "status": "active",
            "min_start_time": start.isoformat(),
            "max_start_time": now.isoformat(),
            "count": 100,
            "sort": "start_time:desc",
        }

        while True:
            resp = requests.get(
                f"{CALENDLY_API}/scheduled_events",
                headers=_headers(),
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            all_events.extend(data.get("collection", []))
            next_page = data.get("pagination", {}).get("next_page")
            if not next_page:
                break
            token = parse_qs(urlparse(next_page).query).get("page_token", [None])[0]
            if not token:
                break
            params = {**params, "page_token": token}

        if not all_events:
            return f"No hay sesiones de Calendly en los últimos {days} días."

        # Open Google Sheet
        creds_path = Path(__file__).parent.parent.parent / os.environ.get(
            "GOOGLE_CREDENTIALS_FILE", "google_credentials.json"
        )
        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.Client(auth=creds)
        spreadsheet = client.open_by_key(os.environ["GOOGLE_SHEETS_CRM_ID"])

        try:
            ws = spreadsheet.worksheet(sheet_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows=2000, cols=10)

        headers = ["Fecha", "Nombre", "Email", "Teléfono", "A qué se dedica", "Punto actual", "Objetivo"]
        ws.append_row(headers, value_input_option="USER_ENTERED")

        tz = pytz.timezone(TZ)
        rows = []

        for event in all_events:
            start_raw = event.get("start_time", "")
            event_name = event.get("name", "Llamada")
            event_uuid = event.get("uri", "").split("/")[-1]
            setter = _detect_setter(event_name)

            start_str = start_raw
            if start_raw:
                try:
                    dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    dt = dt.astimezone(tz)
                    start_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            # Fetch raw invitee data to parse specific form fields
            try:
                resp_inv = requests.get(
                    f"{CALENDLY_API}/scheduled_events/{event_uuid}/invitees",
                    headers=_headers(),
                    params={"count": 10},
                    timeout=10,
                )
                resp_inv.raise_for_status()
                invitees_raw = resp_inv.json().get("collection", [])
            except Exception:
                invitees_raw = []

            for inv in invitees_raw:
                nombre = inv.get("name", "")
                email = inv.get("email", "")
                telefono = ""
                dedica = ""
                punto_actual = ""
                objetivo = ""

                for qa in inv.get("questions_and_answers", []):
                    q = qa.get("question", "").lower()
                    a = (qa.get("answer") or "").strip()
                    if not a:
                        continue
                    if any(k in q for k in ["telefono", "teléfono", "phone", "whatsapp", "número", "movil", "móvil"]):
                        telefono = a
                    elif any(k in q for k in ["dedicas", "vendes", "dedica"]):
                        dedica = a
                    elif any(k in q for k in ["punto exacto", "encuentras ahora", "en tu negocio", "punto actual"]):
                        punto_actual = a
                    elif any(k in q for k in ["objetivo de negocio", "próximos 6", "proximos 6"]):
                        objetivo = a

                rows.append([
                    start_str,
                    nombre,
                    email,
                    telefono,
                    dedica,
                    punto_actual,
                    objetivo,
                ])

        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")

        return f"{len(rows)} sesiones exportadas a la hoja '{sheet_name}'."

    except Exception as e:
        return f"Error exportando sesiones de Calendly: {e}"


def get_past_sessions(days: int = 7) -> str:
    """Returns past Calendly sessions."""
    try:
        org_uri = _get_org_uri()

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        resp = requests.get(
            f"{CALENDLY_API}/scheduled_events",
            headers=_headers(),
            params={
                "organization": org_uri,
                "status": "active",
                "min_start_time": start.isoformat(),
                "max_start_time": now.isoformat(),
                "count": 25,
                "sort": "start_time:desc",
            },
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json().get("collection", [])

        if not events:
            return f"No hay sesiones de Calendly en los ultimos {days} dias."

        tz = pytz.timezone(TZ)
        lines = []
        for event in events:
            start_raw = event.get("start_time", "")
            event_name = event.get("name", "Llamada")
            event_uuid = event.get("uri", "").split("/")[-1]
            setter = _detect_setter(event_name)

            start_str = start_raw
            if start_raw:
                try:
                    dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    dt = dt.astimezone(tz)
                    start_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            invitees = _parse_invitees(event_uuid)
            block = [f"📅 {start_str} — {event_name}"]
            if setter:
                block.append(f"   Setter: {setter}")
            for inv in invitees:
                inv_line = f"   • {inv['nombre']}"
                if inv.get("telefono"):  inv_line += f" | Tel: {inv['telefono']}"
                if inv.get("instagram"): inv_line += f" | IG: {inv['instagram']}"
                if inv.get("email"):     inv_line += f" | {inv['email']}"
                block.append(inv_line)
            lines.append("\n".join(block))

        return f"Sesiones recientes ({len(events)}):\n\n" + "\n\n".join(lines)

    except Exception as e:
        return f"Error obteniendo sesiones pasadas: {e}"
