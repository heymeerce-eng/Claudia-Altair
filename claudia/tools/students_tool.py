"""
CRM de Alumnos ALTAIR — Google Sheets.
Programas: CUMBRE (vitalicio), CRIBA (3 meses, 3 sesiones), CEO (6 meses, 5 sesiones).
Hojas: cumbre, criba, ceo.
"""
import os
import calendar
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from datetime import date, datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

FIELD_ALIASES = {
    "nombre":            ["nombre", "alumno", "nombre completo"],
    "email":             ["email", "correo"],
    "telefono":          ["teléfono", "telefono", "tel", "móvil", "movil", "whatsapp"],
    "fecha_pago":        ["fecha de pago", "fecha pago", "fecha ingreso", "fecha entrada"],
    "importe":           ["importe", "precio pagado", "precio", "cantidad"],
    "tipo_negocio":      ["tipo de negocio", "negocio", "actividad", "sector"],
    "contrato":          ["contrato firmado", "contrato"],
    "proteccion_datos":  ["protección de datos", "proteccion de datos", "rgpd", "proteccion"],
    "bienvenida":        ["bienvenida enviada", "bienvenida"],
    "estado":            ["estado"],
    "fecha_fin":         ["fecha fin", "fecha de fin", "fecha finalización", "fecha finalizacion"],
    "notas_alumno":      ["notas del alumno", "📝 notas", "notas alumno", "notas"],
    "alerta_renovacion": ["alerta renovación", "alerta renovacion", "⚠️ alerta", "alerta"],
    "skool_activo":      ["skool activado", "skool activo", "acceso skool", "skool"],
    "skool_fecha":       ["fecha activación skool", "fecha skool", "activación skool", "fecha activacion"],
}

SESSION_ALIASES = {
    "s1": ["s1", "sesión 1", "sesion 1", "onboarding", "1"],
    "s2": ["s2", "sesión 2", "sesion 2", "estratégica 1", "estrategica 1", "2"],
    "s3": ["s3", "sesión 3", "sesion 3", "estratégica 2", "estrategica 2", "3"],
    "s4": ["s4", "sesión 4", "sesion 4", "4"],
    "s5": ["s5", "sesión 5", "sesion 5", "5"],
}


def _get_spreadsheet():
    creds_path = Path(__file__).parent.parent.parent / os.environ.get(
        "GOOGLE_CREDENTIALS_FILE", "google_credentials.json"
    )
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.Client(auth=creds)
    return client.open_by_key(os.environ["GOOGLE_SHEETS_STUDENTS_ID"])


PROGRAM_HEADERS = {
    "cumbre": [
        "Nombre", "Email", "Teléfono", "Fecha de pago", "Importe", "Tipo de negocio",
        "Contrato firmado", "Protección de datos", "Bienvenida enviada",
        "Skool activo", "Fecha activación Skool",
        "Estado", "Notas del alumno",
    ],
    "criba": [
        "Nombre", "Email", "Teléfono", "Fecha de pago", "Importe", "Tipo de negocio",
        "Fecha fin", "Contrato firmado", "Protección de datos", "Bienvenida enviada",
        "S1 Fecha", "S1 Realizada", "S1 Notas",
        "S2 Fecha", "S2 Realizada", "S2 Notas",
        "S3 Fecha", "S3 Realizada", "S3 Notas",
        "Estado", "Notas del alumno", "Alerta renovacion",
    ],
    "ceo": [
        "Nombre", "Email", "Teléfono", "Fecha de pago", "Importe", "Tipo de negocio",
        "Fecha fin", "Contrato firmado", "Protección de datos", "Bienvenida enviada",
        "S1 Fecha", "S1 Realizada", "S1 Notas",
        "S2 Fecha", "S2 Realizada", "S2 Notas",
        "S3 Fecha", "S3 Realizada", "S3 Notas",
        "S4 Fecha", "S4 Realizada", "S4 Notas",
        "S5 Fecha", "S5 Realizada", "S5 Notas",
        "Estado", "Notas del alumno", "Alerta renovacion",
    ],
}


def _get_sheet(programa: str):
    """Returns worksheet matching the program name (handles emojis in sheet name)."""
    ss = _get_spreadsheet()
    prog = programa.lower().strip()
    for ws in ss.worksheets():
        if prog in ws.title.lower():
            # Initialize headers if sheet is empty
            if not ws.row_values(1):
                headers = PROGRAM_HEADERS.get(prog, [])
                if headers:
                    ws.append_row(headers, value_input_option="USER_ENTERED")
            return ws
    raise ValueError(f"No encontré hoja para el programa '{programa}'")


def _build_col_map(headers: list) -> dict:
    col_map = {}
    for i, header in enumerate(headers):
        h = header.lower().strip()
        for field, aliases in FIELD_ALIASES.items():
            if field not in col_map and any(a in h for a in aliases):
                col_map[field] = i
                break
    return col_map


def _parse_date(s: str):
    if not s:
        return None
    s = s.strip().replace(".", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
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


def _calc_fecha_fin(fecha_pago_str: str, programa: str) -> str:
    months = {"criba": 3, "ceo": 6}.get(programa.lower())
    if not months:
        return "Vitalicio"
    d = _parse_date(fecha_pago_str)
    if not d:
        return ""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).strftime("%d/%m/%Y")


def _find_student_row(ws, query: str):
    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        return None, None, None
    col_map = _build_col_map(all_rows[0])
    q = query.lower()
    for i, row in enumerate(all_rows[1:], start=2):
        nombre = row[col_map["nombre"]] if "nombre" in col_map and col_map["nombre"] < len(row) else ""
        email = row[col_map["email"]] if "email" in col_map and col_map["email"] < len(row) else ""
        tel = row[col_map["telefono"]] if "telefono" in col_map and col_map["telefono"] < len(row) else ""
        if q in f"{nombre} {email} {tel}".lower():
            return i, row, col_map
    return None, None, None


def _find_session_cols(headers: list, sesion_id: str) -> dict:
    sid = sesion_id.lower().strip()
    canonical = next(
        (k for k, aliases in SESSION_ALIASES.items() if sid in aliases or sid == k),
        sid,
    )
    aliases = SESSION_ALIASES.get(canonical, [canonical])
    result = {}
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(a in hl for a in aliases):
            if "fecha" in hl:
                result["fecha"] = i
            elif any(k in hl for k in ["realiz", "hecha", "completad", "sí/no", "si/no"]):
                result["realizada"] = i
            elif "nota" in hl:
                result["notas"] = i
    return result


# ── Public functions ───────────────────────────────────────────────────────────

def search_student(query: str) -> str:
    """Searches for a student by name, email or phone across all program sheets."""
    results = []
    for programa in ["cumbre", "criba", "ceo"]:
        try:
            ws = _get_sheet(programa)
            row_idx, row, col_map = _find_student_row(ws, query)
            if not row_idx:
                continue
            nombre = row[col_map["nombre"]] if "nombre" in col_map and col_map["nombre"] < len(row) else query
            lines = [f"*{nombre}* — {programa.upper()}"]
            for field in ["email", "telefono", "estado", "fecha_pago", "fecha_fin", "importe", "contrato", "proteccion_datos", "bienvenida"]:
                col = col_map.get(field)
                if col is not None and col < len(row) and row[col]:
                    label = {"fecha_pago": "Fecha pago", "fecha_fin": "Fecha fin",
                             "proteccion_datos": "Protección datos"}.get(field, field.capitalize())
                    lines.append(f"  {label}: {row[col]}")
            results.append("\n".join(lines))
        except Exception:
            continue
    if not results:
        return f"No encontré a nadie con '{query}' en el CRM de alumnos."
    return "\n\n".join(results)


def create_student(
    programa: str,
    nombre: str,
    email: str,
    fecha_pago: str,
    importe: str,
    tipo_negocio: str = "",
    telefono: str = "",
    contrato: str = "Pendiente",
    proteccion_datos: str = "Pendiente",
    bienvenida: str = "Pendiente",
    skool_activo: str = "Pendiente",
    skool_fecha: str = "",
) -> str:
    try:
        ws = _get_sheet(programa)
        headers = ws.row_values(1)
        col_map = _build_col_map(headers)
        fecha_fin = _calc_fecha_fin(fecha_pago, programa)

        values = {
            "nombre": nombre,
            "email": email.lower().strip(),
            "telefono": telefono,
            "fecha_pago": fecha_pago,
            "importe": str(importe).replace("€", "").replace("$", "").strip(),
            "tipo_negocio": tipo_negocio,
            "contrato": contrato,
            "proteccion_datos": proteccion_datos,
            "bienvenida": bienvenida,
            "estado": "Activo",
            "fecha_fin": fecha_fin,
            "skool_activo": skool_activo if programa.lower() == "cumbre" else "",
            "skool_fecha": skool_fecha if programa.lower() == "cumbre" else "",
        }

        row = [""] * len(headers)
        for field, val in values.items():
            if field in col_map:
                row[col_map[field]] = val

        ws.append_row(row, value_input_option="USER_ENTERED")

        pendientes = []
        if not telefono:
            pendientes.append("teléfono")
        if contrato == "Pendiente":
            pendientes.append("contrato firmado")
        if proteccion_datos == "Pendiente":
            pendientes.append("protección de datos")
        if bienvenida == "Pendiente":
            pendientes.append("bienvenida enviada")
        if programa.lower() == "cumbre" and skool_activo == "Pendiente":
            pendientes.append("acceso Skool")

        resumen = (
            f"✅ Registrado en CRM Alumnos — *{nombre}*\n"
            f"Programa: {programa.upper()}\n"
            f"Fecha pago: {fecha_pago}\n"
            f"Fecha fin: {fecha_fin}\n"
            f"Importe: {values['importe']} €\n"
            f"Contrato: {contrato} · Protección datos: {proteccion_datos} · Bienvenida: {bienvenida}\n"
            f"Estado: Activo"
        )
        if pendientes:
            resumen += f"\n\n⚠️ Pendiente de confirmar: {', '.join(pendientes)}"
        return resumen
    except Exception as e:
        return f"Error creando alumno: {e}"


def update_student(query: str, programa: str, **fields) -> str:
    try:
        ws = _get_sheet(programa)
        row_idx, row, col_map = _find_student_row(ws, query)
        if not row_idx:
            return f"No encontré a '{query}' en {programa.upper()}."
        updated = []
        for field, value in fields.items():
            if field in col_map and value:
                ws.update_cell(row_idx, col_map[field] + 1, value)
                updated.append(field.replace("_", " "))
        nombre = row[col_map.get("nombre", 0)] if "nombre" in col_map else query
        return (f"✅ *{nombre}* actualizado en {programa.upper()}.\nCampos: {', '.join(updated)}"
                if updated else f"No se actualizó nada para {nombre}.")
    except Exception as e:
        return f"Error actualizando alumno: {e}"


def add_session(query: str, programa: str, sesion_id: str, fecha: str, realizada: str, notas: str = "") -> str:
    try:
        ws = _get_sheet(programa)
        all_rows = ws.get_all_values()
        row_idx, row, col_map = _find_student_row(ws, query)
        if not row_idx:
            return f"No encontré a '{query}' en {programa.upper()}."
        session_cols = _find_session_cols(all_rows[0], sesion_id)
        if not session_cols:
            return f"No encontré las columnas para la sesión '{sesion_id}' en {programa.upper()}."
        nombre = row[col_map.get("nombre", 0)] if "nombre" in col_map else query
        if "fecha" in session_cols:
            ws.update_cell(row_idx, session_cols["fecha"] + 1, fecha)
        if "realizada" in session_cols:
            ws.update_cell(row_idx, session_cols["realizada"] + 1, realizada)
        if "notas" in session_cols and notas:
            ws.update_cell(row_idx, session_cols["notas"] + 1, notas)
        return f"✅ Sesión {sesion_id} registrada para *{nombre}* ({programa.upper()}) — {fecha}"
    except Exception as e:
        return f"Error registrando sesión: {e}"


def add_student_note(query: str, programa: str, nota: str) -> str:
    try:
        ws = _get_sheet(programa)
        row_idx, row, col_map = _find_student_row(ws, query)
        if not row_idx:
            return f"No encontré a '{query}' en {programa.upper()}."
        col = col_map.get("notas_alumno")
        if col is None:
            return f"No encontré la columna de notas en {programa.upper()}."
        today = date.today().strftime("%d/%m/%Y")
        existing = row[col] if col < len(row) else ""
        new_val = f"{existing}\n[{today}] — {nota}".strip()
        ws.update_cell(row_idx, col + 1, new_val)
        nombre = row[col_map.get("nombre", 0)] if "nombre" in col_map else query
        return f"✅ Nota añadida para *{nombre}*."
    except Exception as e:
        return f"Error añadiendo nota: {e}"


def get_students_briefing() -> str:
    """Returns students with overdue sessions or long time without contact."""
    try:
        today = date.today()
        alerts = []

        program_sessions = {
            "criba": [("S1", "Onboarding"), ("S2", "Estratégica 1"), ("S3", "Estratégica 2")],
            "ceo":   [("S1", "Onboarding"), ("S2", "Seg. 2"), ("S3", "Seg. 3"), ("S4", "Seg. 4"), ("S5", "Seg. 5")],
        }

        for programa, sessions in program_sessions.items():
            try:
                ws = _get_sheet(programa)
                all_rows = ws.get_all_values()
                if len(all_rows) <= 1:
                    continue
                headers = all_rows[0]
                col_map = _build_col_map(all_rows[0])
                nombre_col = col_map.get("nombre")
                estado_col = col_map.get("estado")

                for row in all_rows[1:]:
                    nombre = row[nombre_col] if nombre_col is not None and nombre_col < len(row) else ""
                    estado = row[estado_col] if estado_col is not None and estado_col < len(row) else ""
                    if not nombre or estado.lower() != "activo":
                        continue

                    # Find last completed session and next pending
                    last_session_date = None
                    next_pending = None

                    for sid, sname in sessions:
                        s_cols = _find_session_cols(headers, sid)
                        fecha_col = s_cols.get("fecha")
                        real_col = s_cols.get("realizada")

                        fecha_val = row[fecha_col] if fecha_col is not None and fecha_col < len(row) else ""
                        real_val = row[real_col] if real_col is not None and real_col < len(row) else ""

                        if real_val.lower() == "sí" or real_val.lower() == "si":
                            d = _parse_date(fecha_val)
                            if d and (last_session_date is None or d > last_session_date):
                                last_session_date = d
                        elif not fecha_val and next_pending is None:
                            next_pending = sname

                    # Alert if last session was >30 days ago and there are pending sessions
                    if last_session_date and next_pending:
                        days_since = (today - last_session_date).days
                        threshold = 30 if programa == "criba" else 45
                        if days_since >= threshold:
                            alerts.append(
                                f"⚠️ *{nombre}* ({programa.upper()}) — sin sesión hace {days_since} días\n"
                                f"  Próxima pendiente: {next_pending}"
                            )
                    # Alert if no session at all and enrolled (nueva alumna sin onboarding)
                    elif last_session_date is None and next_pending:
                        alerts.append(
                            f"🔔 *{nombre}* ({programa.upper()}) — sin sesiones aún\n"
                            f"  Pendiente: {next_pending}"
                        )
            except Exception:
                continue

        # Also check renewal alerts
        for programa in ["criba", "ceo"]:
            try:
                ws = _get_sheet(programa)
                all_rows = ws.get_all_values()
                if len(all_rows) <= 1:
                    continue
                col_map = _build_col_map(all_rows[0])
                nombre_col = col_map.get("nombre")
                fin_col = col_map.get("fecha_fin")
                estado_col = col_map.get("estado")
                if fin_col is None:
                    continue
                for row in all_rows[1:]:
                    nombre = row[nombre_col] if nombre_col is not None and nombre_col < len(row) else ""
                    estado = row[estado_col] if estado_col is not None and estado_col < len(row) else ""
                    fecha_fin_str = row[fin_col] if fin_col < len(row) else ""
                    if not nombre or estado.lower() != "activo":
                        continue
                    fin = _parse_date(fecha_fin_str)
                    if fin and (fin - today).days <= 30:
                        days_left = (fin - today).days
                        alerts.append(
                            f"🔴 *{nombre}* ({programa.upper()}) — termina en {days_left} días ({fecha_fin_str})\n"
                            f"  ¿Renovación o siguiente nivel?"
                        )
            except Exception:
                continue

        if not alerts:
            return ""
        return "👩‍🎓 *Alumnos — pendientes:*\n\n" + "\n\n".join(alerts)
    except Exception as e:
        return f"Error en briefing de alumnos: {e}"


def get_renewal_alerts() -> str:
    try:
        today = date.today()
        alerts = []
        for programa in ["criba", "ceo"]:
            try:
                ws = _get_sheet(programa)
                all_rows = ws.get_all_values()
                if len(all_rows) <= 1:
                    continue
                col_map = _build_col_map(all_rows[0])
                nombre_col = col_map.get("nombre")
                fin_col = col_map.get("fecha_fin")
                estado_col = col_map.get("estado")
                if fin_col is None:
                    continue
                for row in all_rows[1:]:
                    nombre = row[nombre_col] if nombre_col is not None and nombre_col < len(row) else ""
                    estado = row[estado_col] if estado_col is not None and estado_col < len(row) else ""
                    fecha_fin_str = row[fin_col] if fin_col < len(row) else ""
                    if not nombre or estado.lower() != "activo":
                        continue
                    fin = _parse_date(fecha_fin_str)
                    if not fin:
                        continue
                    days_left = (fin - today).days
                    if days_left <= 30:
                        alerts.append({
                            "nombre": nombre, "programa": programa.upper(),
                            "fecha_fin": fecha_fin_str, "days_left": days_left,
                            "emoji": "🔴" if days_left <= 7 else "🟡",
                        })
            except Exception:
                continue
        if not alerts:
            return "No hay alertas de renovación activas."
        alerts.sort(key=lambda x: x["days_left"])
        lines = ["⚠️ *Alertas de renovación*\n"]
        for a in alerts:
            label = (f"venció hace {abs(a['days_left'])} días" if a["days_left"] < 0
                     else "vence HOY" if a["days_left"] == 0
                     else f"le quedan {a['days_left']} días")
            lines.append(f"{a['emoji']} *{a['nombre']}* — {a['programa']}\n  Fin: {a['fecha_fin']} ({label})")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error obteniendo alertas: {e}"
