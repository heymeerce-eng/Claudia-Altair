"""
CRM de ALTAIR conectado a Google Sheets.
Campos: Nombre, Avatar, Precio Total, Etapa, Precio Pagado,
        Fecha Sesion, Notas, Estado, Ultimo Contacto, Telefono,
        Email, Tipo Negocio, Setter
"""
import os
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import date, datetime, timedelta

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The 3 columns we add if they don't exist yet
NEW_HEADERS = ["Email", "Tipo Negocio", "Setter", "Situacion actual"]

# How to detect each field by header name (lowercase)
FIELD_ALIASES = {
    "nombre":          ["llamadas de claridad", "nombre"],
    "avatar":          ["avatar", "programa"],
    "precio_total":    ["precio total"],
    "etapa_pago":      ["etapa"],
    "precio_pagado":   ["precio pagado"],
    "fecha_sesion":    ["fecha sesion", "fecha sesión"],
    "notas":           ["notas"],
    "estado":          ["estado"],
    "ultimo_contacto": ["ultimo contacto", "último contacto"],
    "telefono":        ["numero", "teléfono", "telefono"],
    "email":           ["email", "correo"],
    "tipo_negocio":    ["tipo negocio"],
    "setter":          ["setter"],
    "situacion_actual":["situacion actual", "situación actual", "situacion", "anexo"],
}


PIPELINE_HEADERS = [
    "Nombre", "Avatar", "Precio Total", "Etapa", "Precio Pagado",
    "Fecha Sesion", "Notas", "Estado", "Ultimo Contacto",
    "Telefono", "Email", "Tipo Negocio", "Setter", "Situacion actual",
]


def _get_sheet():
    creds_path = Path(__file__).parent.parent.parent / os.environ.get(
        "GOOGLE_CREDENTIALS_FILE", "google_credentials.json"
    )
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.Client(auth=creds)
    spreadsheet = client.open_by_key(os.environ["GOOGLE_SHEETS_CRM_ID"])
    ws = None
    for sheet in spreadsheet.worksheets():
        tl = sheet.title.lower()
        if "pipeline" in tl or "crm" in tl:
            ws = sheet
            break
    if ws is None:
        ws = spreadsheet.sheet1
    if not ws.row_values(1):
        ws.append_row(PIPELINE_HEADERS, value_input_option="USER_ENTERED")
    return ws


def _build_col_map(headers: list) -> dict:
    """Maps field names to 0-indexed positions."""
    col_map = {}
    for i, header in enumerate(headers):
        h = header.lower().strip()
        for field, aliases in FIELD_ALIASES.items():
            if field not in col_map and any(a == h or h.startswith(a) for a in aliases):
                col_map[field] = i
                break
    return col_map


def _ensure_new_columns(ws) -> dict:
    """Adds Email, Tipo Negocio, Setter if missing. Returns col_map."""
    headers = ws.row_values(1)
    col_map = _build_col_map(headers)
    to_add = [h for h in NEW_HEADERS
              if not any(h.lower().startswith(a)
                         for aliases in FIELD_ALIASES.values()
                         for a in aliases
                         if any(h.lower().startswith(a) for a in FIELD_ALIASES.get(
                             next((f for f, al in FIELD_ALIASES.items()
                                   if any(h.lower().startswith(a) for a in al)), ""), [])))]
    # Simpler check: just verify the field is in col_map
    field_for_header = {"Email": "email", "Tipo Negocio": "tipo_negocio", "Setter": "setter", "Situacion actual": "situacion_actual"}
    to_add = [h for h, f in field_for_header.items() if f not in col_map]
    if to_add:
        next_col = len(headers) + 1
        ws.add_cols(len(to_add))
        for i, h in enumerate(to_add):
            ws.update_cell(1, next_col + i, h)
        headers = ws.row_values(1)
        col_map = _build_col_map(headers)
    return col_map


def _row_to_dict(row: list, col_map: dict) -> dict:
    return {field: (row[idx] if idx < len(row) else "") for field, idx in col_map.items()}


def _format_lead(d: dict) -> str:
    lines = [f"*{d.get('nombre', '?')}*"]
    if d.get("avatar"):          lines.append(f"Avatar: {d['avatar']}")
    if d.get("telefono"):        lines.append(f"Tel: {d['telefono']}")
    if d.get("email"):           lines.append(f"Email: {d['email']}")
    if d.get("estado"):          lines.append(f"Estado: {d['estado']}")
    if d.get("setter"):            lines.append(f"Setter: {d['setter']}")
    if d.get("situacion_actual"): lines.append(f"Situacion: {d['situacion_actual']}")
    if d.get("tipo_negocio"):    lines.append(f"Negocio: {d['tipo_negocio']}")
    if d.get("precio_total"):
        precio = d["precio_total"]
        if d.get("etapa_pago"):  precio += f" — {d['etapa_pago']}"
        if d.get("precio_pagado"): precio += f" (pagado: {d['precio_pagado']})"
        lines.append(f"Precio: {precio}")
    if d.get("fecha_sesion"):    lines.append(f"Sesion: {d['fecha_sesion']}")
    if d.get("ultimo_contacto"): lines.append(f"Ultimo contacto: {d['ultimo_contacto']}")
    if d.get("notas"):           lines.append(f"Notas: {d['notas']}")
    return "\n".join(lines)


# ── Public functions ───────────────────────────────────────────────────────────

def search_lead(query: str) -> str:
    try:
        ws = _get_sheet()
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
            return "El CRM esta vacio."
        col_map = _build_col_map(all_rows[0])
        q = query.lower()
        results = []
        for row in all_rows[1:]:
            d = _row_to_dict(row, col_map)
            haystack = " ".join(filter(None, [
                d.get("nombre"), d.get("telefono"), d.get("email")
            ])).lower()
            if q in haystack:
                results.append(_format_lead(d))
        if not results:
            return f"No encontre a nadie con '{query}' en el CRM."
        return f"{len(results)} resultado(s):\n\n" + "\n\n---\n\n".join(results[:5])
    except Exception as e:
        return f"Error buscando en CRM: {e}"


def create_lead(
    nombre: str,
    avatar: str = "",
    precio_total: str = "",
    etapa_pago: str = "",
    precio_pagado: str = "",
    fecha_sesion: str = "",
    notas: str = "",
    estado: str = "",
    telefono: str = "",
    email: str = "",
    tipo_negocio: str = "Negocio",
    setter: str = "",
    situacion_actual: str = "",
) -> str:
    try:
        ws = _get_sheet()
        col_map = _ensure_new_columns(ws)
        today = date.today().strftime("%d/%m/%Y")
        values = {
            "nombre": nombre, "avatar": avatar, "precio_total": precio_total,
            "etapa_pago": etapa_pago, "precio_pagado": precio_pagado,
            "fecha_sesion": fecha_sesion, "notas": notas, "estado": estado,
            "ultimo_contacto": today, "telefono": telefono, "email": email,
            "tipo_negocio": tipo_negocio, "setter": setter,
            "situacion_actual": situacion_actual,
        }
        headers = ws.row_values(1)
        row = [""] * len(headers)
        for field, val in values.items():
            if field in col_map:
                row[col_map[field]] = val
        ws.append_row(row, value_input_option="USER_ENTERED")
        return f"Lead '{nombre}' creado en el CRM."
    except Exception as e:
        return f"Error creando lead: {e}"


def update_lead(query: str, **fields) -> str:
    try:
        ws = _get_sheet()
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
            return "El CRM esta vacio."
        col_map = _ensure_new_columns(ws)
        q = query.lower()
        row_index = None
        for i, row in enumerate(all_rows[1:], start=2):
            d = _row_to_dict(row, col_map)
            haystack = " ".join(filter(None, [
                d.get("nombre"), d.get("telefono"), d.get("email")
            ])).lower()
            if q in haystack:
                row_index = i
                break
        if not row_index:
            return f"No encontre a nadie con '{query}' en el CRM."
        today = date.today().strftime("%d/%m/%Y")
        updated = []
        for field, value in fields.items():
            if field in col_map and value:
                ws.update_cell(row_index, col_map[field] + 1, value)
                updated.append(field)
        if "ultimo_contacto" in col_map:
            ws.update_cell(row_index, col_map["ultimo_contacto"] + 1, today)
        nombre = all_rows[row_index - 1][col_map.get("nombre", 0)] if "nombre" in col_map else query
        return f"'{nombre}' actualizado en el CRM."
    except Exception as e:
        return f"Error actualizando CRM: {e}"


def _parse_date(s: str):
    """Parses Spanish dates in any common format. Returns date or None."""
    s = s.strip()
    # Normalize: replace dots with slashes, remove spaces
    s = s.replace(".", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Handle short year like 12/5/6 → treat as DD/M/YY adding 2000
    parts = s.split("/")
    if len(parts) == 3:
        try:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 100:
                y += 2000
            return date(y, m, d)
        except (ValueError, TypeError):
            pass
    return None


def _followup_days(estado: str):
    """
    Returns (days_threshold, emoji, action) based on estado.
    None means skip (closed / not aligned).
    """
    e = estado.lower()
    if any(k in e for k in ["muy caliente", "🔥"]):
        return 1, "🔥", "Mantener decision viva (24-72h)"
    if any(k in e for k in ["caliente"]):
        return 1, "🔥", "Mantener decision viva (24-72h)"
    if any(k in e for k in ["interesado", "🟡", "tibio"]):
        return 7, "🟡", "Subir consciencia (7 dias)"
    if any(k in e for k in ["potencial", "🔵", "futuro"]):
        return 30, "🔵", "Mantener conexion (1 mes)"
    if any(k in e for k in ["cerrado", "no alineado", "perdido", "❌", "no cualifica"]):
        return None, None, None
    return None, None, None


def get_followups_today() -> str:
    """Calculates who needs follow-up today based on estado + ultimo_contacto/fecha_sesion."""
    try:
        ws = _get_sheet()
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
            return "El CRM esta vacio."
        col_map = _build_col_map(all_rows[0])
        today = date.today()
        overdue = []
        due = []

        for row in all_rows[1:]:
            d = _row_to_dict(row, col_map)
            if not d.get("nombre"):
                continue
            estado = d.get("estado", "")
            days_threshold, emoji, accion = _followup_days(estado)
            if days_threshold is None:
                continue

            # Reference date: ultimo_contacto first, then fecha_sesion
            ref_str = d.get("ultimo_contacto") or d.get("fecha_sesion") or ""
            ref_date = _parse_date(ref_str)
            if not ref_date:
                continue

            due_date = ref_date + timedelta(days=days_threshold)
            days_late = (today - due_date).days

            if days_late >= 0:
                entry = {
                    "nombre": d.get("nombre", "?"),
                    "telefono": d.get("telefono", ""),
                    "email": d.get("email", ""),
                    "estado": estado,
                    "setter": d.get("setter", ""),
                    "emoji": emoji,
                    "accion": accion,
                    "days_late": days_late,
                    "ref_date": ref_str,
                }
                if days_late == 0:
                    due.append(entry)
                else:
                    overdue.append(entry)

        if not overdue and not due:
            return "No hay seguimientos pendientes para hoy."

        # Sort overdue most urgent first
        overdue.sort(key=lambda x: x["days_late"], reverse=True)

        lines = []
        if overdue:
            lines.append(f"*ATRASADOS ({len(overdue)}):*")
            for e in overdue:
                label = f"lleva {e['days_late']} dia(s) sin contacto"
                line = f"{e['emoji']} *{e['nombre']}* — {label}"
                if e["telefono"]: line += f"\n   Tel: {e['telefono']}"
                if e["setter"]:   line += f" | Setter: {e['setter']}"
                line += f"\n   Accion: {e['accion']}"
                lines.append(line)

        if due:
            lines.append(f"\n*PARA HOY ({len(due)}):*")
            for e in due:
                line = f"{e['emoji']} *{e['nombre']}*"
                if e["telefono"]: line += f"\n   Tel: {e['telefono']}"
                if e["setter"]:   line += f" | Setter: {e['setter']}"
                line += f"\n   Accion: {e['accion']}"
                lines.append(line)

        total = len(overdue) + len(due)
        result = f"Seguimientos pendientes — {total} lead(s):\n\n" + "\n\n".join(lines)

        # Also include student session alerts
        try:
            from .students_tool import get_students_briefing
            students_part = get_students_briefing()
            if students_part:
                result += f"\n\n---\n\n{students_part}"
        except Exception:
            pass

        return result

    except Exception as e:
        return f"Error calculando seguimientos: {e}"


def list_leads(avatar: str = "", estado: str = "", setter: str = "") -> str:
    try:
        ws = _get_sheet()
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
            return "El CRM esta vacio."
        col_map = _build_col_map(all_rows[0])
        results = []
        for row in all_rows[1:]:
            d = _row_to_dict(row, col_map)
            if not d.get("nombre"):
                continue
            if avatar and avatar.lower() not in d.get("avatar", "").lower():
                continue
            if estado and estado.lower() not in d.get("estado", "").lower():
                continue
            if setter and setter.lower() not in d.get("setter", "").lower():
                continue
            results.append(_format_lead(d))
        if not results:
            return "No hay leads con esos filtros."
        return f"{len(results)} leads:\n\n" + "\n\n---\n\n".join(results[:15])
    except Exception as e:
        return f"Error listando CRM: {e}"
