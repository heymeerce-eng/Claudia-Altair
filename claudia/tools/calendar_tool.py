import os
import caldav
import pytz
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid


def _get_client(email: str = None, password: str = None):
    email = email or os.environ.get("ICLOUD_EMAIL", "")
    password = password or os.environ.get("ICLOUD_APP_PASSWORD", "")
    return caldav.DAVClient(
        url="https://caldav.icloud.com",
        username=email,
        password=password,
    )


def _get_all_calendars(client):
    principal = client.principal()
    return principal.calendars()


def _get_default_calendar(client):
    """Returns the best calendar for creating new events."""
    calendars = _get_all_calendars(client)
    priority = ["eventos", "citas", "personal", "calendar", "home"]
    for keyword in priority:
        for cal in calendars:
            name = str(getattr(cal, "name", "")).lower()
            if keyword in name:
                return cal
    return calendars[0] if calendars else None


def get_events(start_date: str, end_date: str,
               email: str = None, password: str = None) -> str:
    try:
        client = _get_client(email, password)
        calendars = _get_all_calendars(client)
        if not calendars:
            return "No se encontró ningún calendario."

        tz = pytz.timezone("Europe/Madrid")
        start = tz.localize(datetime.strptime(start_date, "%Y-%m-%d"))
        end = tz.localize(datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))

        def _fetch_cal(cal):
            cal_name = str(getattr(cal, "name", ""))
            if "recordatorio" in cal_name.lower():
                return []
            lines = []
            try:
                events = cal.date_search(start=start, end=end, expand=True)
                for event in events:
                    try:
                        cal_data = Calendar.from_ical(event.data)
                        for component in cal_data.walk():
                            if component.name == "VEVENT":
                                summary = str(component.get("SUMMARY", "Sin título"))
                                dtstart = component.get("DTSTART").dt
                                dtend = component.get("DTEND").dt
                                location = str(component.get("LOCATION", ""))
                                if hasattr(dtstart, "strftime"):
                                    if hasattr(dtstart, "hour"):
                                        start_str = dtstart.strftime("%d/%m/%Y %H:%M")
                                        end_str = dtend.strftime("%H:%M") if hasattr(dtend, "hour") else ""
                                    else:
                                        start_str = dtstart.strftime("%d/%m/%Y")
                                        end_str = "(todo el día)"
                                    line = f"• [{cal_name}] {summary} — {start_str}"
                                    if end_str:
                                        line += f" a {end_str}"
                                    if location:
                                        line += f" | {location}"
                                    lines.append(line)
                    except Exception:
                        continue
            except Exception:
                pass
            return lines

        result = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(_fetch_cal, cal): cal for cal in calendars}
            for future in as_completed(futures):
                result.extend(future.result())

        return "\n".join(result) if result else f"No hay eventos entre {start_date} y {end_date}."
    except Exception as e:
        return f"Error al acceder al calendario: {str(e)}"


def create_event(title: str, start_datetime: str, end_datetime: str,
                 description: str = "", location: str = "",
                 email: str = None, password: str = None) -> str:
    try:
        client = _get_client(email, password)
        cal = _get_default_calendar(client)
        if not cal:
            return "No se encontró ningún calendario para crear el evento."

        tz = pytz.timezone("Europe/Madrid")

        fmt = "%Y-%m-%dT%H:%M:%S"
        start_dt = tz.localize(datetime.strptime(start_datetime, fmt))
        end_dt = tz.localize(datetime.strptime(end_datetime, fmt))

        event = Event()
        event.add("summary", title)
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("uid", str(uuid.uuid4()))
        if description:
            event.add("description", description)
        if location:
            event.add("location", location)

        ical = Calendar()
        ical.add("prodid", "-//Claudia Personal Agent//ES")
        ical.add("version", "2.0")
        ical.add_component(event)

        cal.save_event(ical.to_ical())
        return f"Evento '{title}' creado el {start_dt.strftime('%d/%m/%Y a las %H:%M')}."
    except Exception as e:
        return f"Error al crear el evento: {str(e)}"
