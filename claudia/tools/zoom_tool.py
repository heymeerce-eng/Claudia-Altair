"""
Herramienta de Zoom para Claudia.
Usa Server-to-Server OAuth (sin intervención del usuario).
"""
import os
import requests
from datetime import datetime
from typing import Optional
import pytz

ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"
TZ = "Europe/Madrid"

_token_cache: dict = {"token": None, "expires_at": 0}


def _get_token() -> str:
    import time
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    account_id = os.environ["ZOOM_ACCOUNT_ID"]
    client_id = os.environ["ZOOM_CLIENT_ID"]
    client_secret = os.environ["ZOOM_CLIENT_SECRET"]

    resp = requests.post(
        ZOOM_TOKEN_URL,
        params={"grant_type": "account_credentials", "account_id": account_id},
        auth=(client_id, client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


def create_meeting(topic: str, start_datetime: str, duration_minutes: int,
                   agenda: str = "", password: str = "",
                   zoom_user: str = "me") -> str:
    """Creates a Zoom meeting and returns the join URL."""
    try:
        tz = pytz.timezone(TZ)
        fmt = "%Y-%m-%dT%H:%M:%S"
        dt = tz.localize(datetime.strptime(start_datetime, fmt))
        start_iso = dt.strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "topic": topic,
            "type": 2,  # Scheduled
            "start_time": start_iso,
            "duration": duration_minutes,
            "timezone": TZ,
            "agenda": agenda,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "waiting_room": True,
                "auto_recording": "cloud",
            },
        }
        if password:
            payload["password"] = password

        resp = requests.post(
            f"{ZOOM_API_BASE}/users/{zoom_user}/meetings",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        join_url = data["join_url"]
        meeting_id = data["id"]
        start_str = dt.strftime("%d/%m/%Y a las %H:%M")

        return (
            f"Reunión '{topic}' creada para el {start_str} ({duration_minutes} min).\n"
            f"Link: {join_url}\n"
            f"ID: {meeting_id}"
        )
    except Exception as e:
        return f"Error al crear la reunión de Zoom: {str(e)}"


def list_meetings(zoom_user: str = "me") -> str:
    """Lists upcoming scheduled Zoom meetings."""
    try:
        resp = requests.get(
            f"{ZOOM_API_BASE}/users/{zoom_user}/meetings",
            headers=_headers(),
            params={"type": "upcoming", "page_size": 10},
            timeout=15,
        )
        resp.raise_for_status()
        meetings = resp.json().get("meetings", [])

        if not meetings:
            return "No hay reuniones de Zoom programadas."

        tz = pytz.timezone(TZ)
        lines = []
        for m in meetings:
            raw_start = m.get("start_time", "")
            if raw_start:
                try:
                    dt = datetime.strptime(raw_start, "%Y-%m-%dT%H:%M:%SZ")
                    dt = pytz.utc.localize(dt).astimezone(tz)
                    start_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    start_str = raw_start
            else:
                start_str = "Sin fecha"
            duration = m.get("duration", "?")
            lines.append(
                f"• {m['topic']} — {start_str} ({duration} min)\n"
                f"  Link: {m.get('join_url', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error al obtener reuniones de Zoom: {str(e)}"


def get_recording_transcript(meeting_id: str) -> str:
    """Gets the transcript of a recorded Zoom meeting."""
    try:
        resp = requests.get(
            f"{ZOOM_API_BASE}/meetings/{meeting_id}/recordings",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        recording_files = data.get("recording_files", [])

        # Look for transcript file
        transcript_file = next(
            (f for f in recording_files if f.get("file_type") == "TRANSCRIPT"),
            None
        )

        if not transcript_file:
            # No transcript, return list of available recordings
            types = [f.get("file_type") for f in recording_files]
            if not types:
                return f"No se encontraron grabaciones para la reunión {meeting_id}."
            return (
                f"La reunión {meeting_id} tiene grabaciones pero sin transcripción automática. "
                f"Archivos disponibles: {', '.join(types)}. "
                "Activa 'Audio transcript' en la configuración de Zoom para obtener transcripciones."
            )

        # Download transcript content
        download_url = transcript_file.get("download_url")
        token = _get_token()
        transcript_resp = requests.get(
            f"{download_url}?access_token={token}",
            timeout=30,
        )
        transcript_resp.raise_for_status()

        text = transcript_resp.text
        # Clean up VTT format if needed
        if text.startswith("WEBVTT"):
            lines = text.split("\n")
            content_lines = [
                l for l in lines
                if l.strip()
                and not l.strip().startswith("WEBVTT")
                and not l.strip().startswith("NOTE")
                and "-->" not in l
                and not l.strip().isdigit()
            ]
            text = "\n".join(content_lines)

        topic = data.get("topic", "Reunión")
        start = data.get("start_time", "")
        if start:
            try:
                tz = pytz.timezone(TZ)
                dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
                dt = pytz.utc.localize(dt).astimezone(tz)
                start = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

        return f"Transcripción de '{topic}' ({start}):\n\n{text[:8000]}"
    except Exception as e:
        return f"Error al obtener la transcripción: {str(e)}"


def backfill_crm_from_zoom(days: int = 90) -> str:
    """Checks past Zoom recordings and creates/updates CRM entries with fecha_sesion."""
    import re
    from .crm_tool import search_lead, create_lead as crm_create, update_lead as crm_update

    def _extract_name(topic: str) -> str:
        for pattern in [r"(?:con|with)\s+(.+?)(?:\s*[-—].*)?$", r"[-—]\s*(.+)$"]:
            m = re.search(pattern, topic, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return topic.strip()

    try:
        zoom_users = []
        i = 1
        while True:
            email = os.environ.get(f"USER_{i}_ZOOM_EMAIL")
            if not email:
                break
            zoom_users.append(email)
            i += 1
        if not zoom_users:
            zoom_users = ["me"]

        from datetime import timedelta
        tz_obj = pytz.timezone(TZ)
        end = datetime.utcnow()
        start_dt = end - timedelta(days=days)

        all_meetings = []
        seen_ids: set = set()
        for zoom_user in zoom_users:
            try:
                resp = requests.get(
                    f"{ZOOM_API_BASE}/users/{zoom_user}/recordings",
                    headers=_headers(),
                    params={
                        "from": start_dt.strftime("%Y-%m-%d"),
                        "to": end.strftime("%Y-%m-%d"),
                        "page_size": 50,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                for m in resp.json().get("meetings", []):
                    if m["id"] not in seen_ids:
                        seen_ids.add(m["id"])
                        all_meetings.append(m)
            except Exception:
                continue

        if not all_meetings:
            return f"No hay grabaciones de Zoom en los últimos {days} días."

        created = []
        updated = []
        skipped = []

        for m in all_meetings:
            topic = m.get("topic", "")
            start_raw = m.get("start_time", "")
            duration = m.get("duration", 0)

            fecha = ""
            if start_raw:
                try:
                    dt = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M:%SZ")
                    dt = pytz.utc.localize(dt).astimezone(tz_obj)
                    fecha = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha = start_raw[:10]

            lead_name = _extract_name(topic)
            if len(lead_name) < 3:
                continue

            crm_result = search_lead(lead_name)

            if "No encontre" in crm_result:
                crm_create(
                    nombre=lead_name,
                    fecha_sesion=fecha,
                    notas=f"Sesion Zoom: {topic} ({duration} min)",
                )
                created.append(f"{lead_name} ({fecha})")
            elif "Sesion:" not in crm_result:
                crm_update(lead_name, fecha_sesion=fecha)
                updated.append(f"{lead_name} ({fecha})")
            else:
                skipped.append(lead_name)

        lines = [f"Backfill Zoom → CRM ({days} días, {len(all_meetings)} grabaciones):"]
        if created:
            lines.append(f"\nCreados ({len(created)}): " + ", ".join(created))
        if updated:
            lines.append(f"\nFechas actualizadas ({len(updated)}): " + ", ".join(updated))
        if skipped:
            lines.append(f"\nYa completos ({len(skipped)}): " + ", ".join(skipped))
        if not created and not updated and not skipped:
            lines.append("\nNo se encontraron leads que actualizar.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error en backfill: {e}"


def get_last_recording_transcript(zoom_user: str = "me") -> str:
    """Gets the transcript of the most recent Zoom recording."""
    try:
        from datetime import timedelta
        end = datetime.utcnow()
        start = end - timedelta(days=30)

        resp = requests.get(
            f"{ZOOM_API_BASE}/users/{zoom_user}/recordings",
            headers=_headers(),
            params={
                "from": start.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
                "page_size": 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        meetings = resp.json().get("meetings", [])

        if not meetings:
            return "No hay grabaciones de Zoom en los últimos 30 días."

        # Most recent first
        meetings.sort(key=lambda m: m.get("start_time", ""), reverse=True)
        latest = meetings[0]
        return get_recording_transcript(str(latest["id"]))
    except Exception as e:
        return f"Error al obtener la última grabación: {str(e)}"
