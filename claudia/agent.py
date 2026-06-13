import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import anthropic

from .users import UserProfile
from .expertise import get_expertise
from .tools.calendar_tool import get_events, create_event
from .tools.pdf_tool import generate_pdf
from .tools.zoom_tool import (
    create_meeting,
    list_meetings,
    get_recording_transcript,
    get_last_recording_transcript,
    backfill_crm_from_zoom,
)
from .tools.miro_tool import create_board as miro_create_board, add_sticky_notes as miro_add_stickies
from .tools.presentation_tool import generate_presentation
from .tools.memory_tool import read_memory, save_memory as memory_save
from .tools.crm_tool import (
    search_lead, create_lead as crm_create, update_lead as crm_update,
    list_leads, get_followups_today,
)

from .tools.students_tool import (
    search_student, create_student, update_student,
    add_session, add_student_note, get_renewal_alerts,
)

TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Consulta los eventos del calendario personal de la usuaria para un rango de fechas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Fecha inicio YYYY-MM-DD"},
                "end_date":   {"type": "string", "description": "Fecha fin YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Crea un evento en el calendario personal de la usuaria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string", "description": "Título del evento"},
                "start_datetime": {"type": "string", "description": "Inicio YYYY-MM-DDTHH:MM:SS"},
                "end_datetime":   {"type": "string", "description": "Fin YYYY-MM-DDTHH:MM:SS"},
                "description":    {"type": "string", "description": "Notas del evento (opcional)"},
                "location":       {"type": "string", "description": "Lugar o enlace (opcional)"},
            },
            "required": ["title", "start_datetime", "end_datetime"],
        },
    },
    {
        "name": "create_zoom_meeting",
        "description": "Crea una reunión de Zoom y devuelve el enlace para compartir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":            {"type": "string",  "description": "Nombre de la reunión"},
                "start_datetime":   {"type": "string",  "description": "Inicio YYYY-MM-DDTHH:MM:SS"},
                "duration_minutes": {"type": "integer", "description": "Duración en minutos"},
                "agenda":           {"type": "string",  "description": "Descripción o agenda (opcional)"},
            },
            "required": ["topic", "start_datetime", "duration_minutes"],
        },
    },
    {
        "name": "list_zoom_meetings",
        "description": "Muestra las próximas reuniones de Zoom programadas.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_zoom_transcript",
        "description": (
            "Obtiene la transcripción automática de una reunión de Zoom grabada. "
            "Si no se especifica ID, devuelve la de la última reunión grabada. "
            "Muy útil para generar resúmenes de reuniones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "ID de la reunión de Zoom (opcional, sin ID usa la última grabación)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_miro_board",
        "description": (
            "Crea un tablero en Miro y devuelve el enlace para compartir. "
            "Ideal para customer journeys, calendarios de contenido, mapas de estrategia y brainstorming visual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string", "description": "Nombre del tablero"},
                "description": {"type": "string", "description": "Descripción (opcional)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_miro_sticky_notes",
        "description": (
            "Añade post-its organizados en columnas a un tablero de Miro. "
            "Útil para customer journeys, calendarios editoriales y mapas de empatía. "
            "Requiere el ID del tablero (obtenido al crear el tablero)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "ID del tablero Miro",
                },
                "sections": {
                    "type": "object",
                    "description": (
                        "Secciones como claves y arrays de textos como valores. "
                        "Ej: {\"Semana 1\": [\"Post de valor\", \"Reel\"], \"Semana 2\": [...]}"
                    ),
                },
            },
            "required": ["board_id", "sections"],
        },
    },
    {
        "name": "generate_presentation",
        "description": (
            "Genera una presentación PowerPoint (.pptx) con la identidad visual de ALTAIR. "
            "Úsala para pitch decks, presentaciones de programas, estrategias de contenido y propuestas comerciales."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title":    {"type": "string", "description": "Título de la portada"},
                "subtitle": {"type": "string", "description": "Subtítulo de portada (por defecto: ALTAIR ACADEMIA)"},
                "date":     {"type": "string", "description": "Fecha para la portada (opcional)"},
                "slides": {
                    "type": "array",
                    "description": "Lista de diapositivas",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type":        {"type": "string", "enum": ["section", "content", "quote"],
                                            "description": "'section' divisora, 'content' con bullets, 'quote' cita"},
                            "title":       {"type": "string", "description": "Título (section / content)"},
                            "body":        {"type": ["string", "array"],
                                            "description": "Cuerpo: string o lista de bullets (content)"},
                            "quote":       {"type": "string", "description": "Texto de cita (quote)"},
                            "attribution": {"type": "string", "description": "Autor de la cita (opcional)"},
                        },
                    },
                },
            },
            "required": ["title", "slides"],
        },
    },
    {
        "name": "buscar_lead",
        "description": "Busca a alguien en el CRM por nombre, teléfono o email. Úsalo siempre que se mencione a una clienta o lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Nombre, teléfono o email"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "crear_lead",
        "description": (
            "Crea un nuevo lead en el CRM. "
            "Si falta el avatar o el setter, pídelos antes de crear. "
            "tipo_negocio es 'Negocio' por defecto salvo que digan que es network marketing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre":        {"type": "string", "description": "Nombre completo"},
                "avatar":        {"type": "string", "description": "CRIBA / CEO / Cualifica / No cualifica"},
                "precio_total":  {"type": "string", "description": "Precio total acordado"},
                "etapa_pago":    {"type": "string", "description": "1 pago / 2 pagos / 3 pagos / Pago único"},
                "precio_pagado": {"type": "string", "description": "Cantidad ya pagada"},
                "fecha_sesion":  {"type": "string", "description": "Fecha de la sesión o llamada"},
                "notas":         {"type": "string", "description": "Resumen de lo hablado en la sesión"},
                "estado":        {"type": "string", "description": "Estado actual del lead"},
                "telefono":      {"type": "string", "description": "Número de teléfono"},
                "email":         {"type": "string", "description": "Correo electrónico"},
                "tipo_negocio":    {"type": "string", "description": "Negocio (por defecto) o Network marketing"},
                "setter":          {"type": "string", "description": "Quién hizo la llamada: Tamara, Estefi, Sofi, Merce, Anabel, Diana"},
                "situacion_actual":{"type": "string", "description": "Descripción ampliada de su situación actual o anexo relevante"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "actualizar_lead",
        "description": "Actualiza la ficha de un lead existente en el CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":           {"type": "string", "description": "Nombre, teléfono o email del lead"},
                "avatar":          {"type": "string"},
                "precio_total":    {"type": "string"},
                "etapa_pago":      {"type": "string"},
                "precio_pagado":   {"type": "string"},
                "fecha_sesion":    {"type": "string"},
                "notas":           {"type": "string"},
                "estado":          {"type": "string"},
                "telefono":        {"type": "string"},
                "email":           {"type": "string"},
                "tipo_negocio":    {"type": "string"},
                "setter":          {"type": "string"},
                "situacion_actual":{"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ver_seguimientos",
        "description": (
            "Calcula qué leads necesitan seguimiento hoy según su estado y fecha de último contacto. "
            "🔥 Muy caliente → 24-72h | 🟡 Interesado → 7 días | 🔵 Potencial futuro → 1 mes. "
            "Úsalo cuando pregunten '¿qué tengo hoy?', '¿a quién tengo que escribir?', 'seguimientos pendientes'."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_leads",
        "description": "Lista los leads del CRM. Filtra por avatar (CRIBA/CEO), estado o setter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "avatar": {"type": "string", "description": "CRIBA, CEO, Cualifica... (opcional)"},
                "estado": {"type": "string", "description": "Estado del lead (opcional)"},
                "setter": {"type": "string", "description": "Tamara, Estefi, Sofi... (opcional)"},
            },
            "required": [],
        },
    },
    {
        "name": "buscar_alumno",
        "description": "Busca un alumno en el CRM de alumnos ALTAIR por nombre, email o teléfono.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Nombre, email o teléfono del alumno"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "crear_alumno",
        "description": "Registra un alumno nuevo en el CRM de alumnos ALTAIR (CUMBRE, CRIBA o CEO).",
        "input_schema": {
            "type": "object",
            "properties": {
                "programa":          {"type": "string", "description": "cumbre, criba o ceo"},
                "nombre":            {"type": "string"},
                "email":             {"type": "string"},
                "fecha_pago":        {"type": "string", "description": "DD/MM/AAAA"},
                "importe":           {"type": "string", "description": "Número sin símbolo (ej: 1500)"},
                "tipo_negocio":      {"type": "string"},
                "telefono":          {"type": "string"},
                "contrato":          {"type": "string", "description": "Sí / No / Pendiente"},
                "proteccion_datos":  {"type": "string", "description": "Sí / No / Pendiente"},
                "bienvenida":        {"type": "string", "description": "Sí / No / Pendiente"},
                "skool_activo":      {"type": "string", "description": "Solo CUMBRE: Sí / No / Pendiente"},
                "skool_fecha":       {"type": "string", "description": "Solo CUMBRE: fecha activación Skool"},
            },
            "required": ["programa", "nombre", "email", "fecha_pago", "importe"],
        },
    },
    {
        "name": "actualizar_alumno",
        "description": "Actualiza campos de un alumno existente en el CRM de alumnos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":             {"type": "string", "description": "Nombre, email o teléfono"},
                "programa":          {"type": "string", "description": "cumbre, criba o ceo"},
                "estado":            {"type": "string"},
                "contrato":          {"type": "string"},
                "proteccion_datos":  {"type": "string"},
                "bienvenida":        {"type": "string"},
                "skool_activo":      {"type": "string"},
                "skool_fecha":       {"type": "string"},
                "importe":           {"type": "string"},
                "tipo_negocio":      {"type": "string"},
                "telefono":          {"type": "string"},
                "email":             {"type": "string"},
            },
            "required": ["query", "programa"],
        },
    },
    {
        "name": "registrar_sesion",
        "description": "Registra una sesión realizada con un alumno (fecha, si se realizó, notas).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":     {"type": "string", "description": "Nombre del alumno"},
                "programa":  {"type": "string", "description": "criba o ceo"},
                "sesion_id": {"type": "string", "description": "s1/s2/s3/s4/s5 o 'onboarding'"},
                "fecha":     {"type": "string", "description": "DD/MM/AAAA"},
                "realizada": {"type": "string", "description": "Sí / No / Pendiente"},
                "notas":     {"type": "string", "description": "Resumen de la sesión (opcional)"},
            },
            "required": ["query", "programa", "sesion_id", "fecha", "realizada"],
        },
    },
    {
        "name": "anadir_nota_alumno",
        "description": "Añade una nota con fecha a la ficha del alumno.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":    {"type": "string", "description": "Nombre del alumno"},
                "programa": {"type": "string", "description": "cumbre, criba o ceo"},
                "nota":     {"type": "string", "description": "Información a guardar"},
            },
            "required": ["query", "programa", "nota"],
        },
    },
    {
        "name": "alertas_renovacion",
        "description": "Muestra los alumnos de CRIBA y CEO que terminan el programa en los próximos 30 días.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "backfill_zoom_crm",
        "description": (
            "Importa todas las sesiones de Zoom grabadas al CRM: crea leads nuevos si no existen "
            "y rellena la fecha de sesión en los que ya están. "
            "Úsalo cuando pidan 'importa las sesiones pasadas', 'rellena las fechas del CRM', "
            "'sincroniza Zoom con el CRM' o similar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dias": {
                    "type": "integer",
                    "description": "Cuántos días hacia atrás buscar grabaciones (por defecto 90)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "save_memory",
        "description": (
            "Guarda información importante en la memoria persistente de Claudia. "
            "Usa esto cuando alguien diga 'recuerda que...', 'guarda que...', 'no olvides que...', "
            "o comparta información relevante como datos de clientes, decisiones importantes, "
            "fechas clave, preferencias o contexto de negocio que debas recordar en el futuro."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_name": {
                    "type": "string",
                    "description": "Nombre de la socia (Merce, Anabel o Diana)",
                },
                "content": {
                    "type": "string",
                    "description": "Información a guardar, de forma clara y concisa",
                },
            },
            "required": ["user_name", "content"],
        },
    },
    {
        "name": "generate_pdf_document",
        "description": (
            "Genera un PDF con la identidad visual de ALTAIR. "
            "Úsalo para propuestas de contenido, resúmenes ejecutivos y presupuestos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["proposal", "summary", "quote"],
                    "description": "'proposal' propuesta, 'summary' resumen, 'quote' presupuesto",
                },
                "title":     {"type": "string", "description": "Título del documento"},
                "content":   {
                    "type": "string",
                    "description": "Contenido en markdown. ## para secciones, - para listas, **negrita**.",
                },
                "recipient": {"type": "string", "description": "Destinatario (opcional)"},
                "date":      {"type": "string", "description": "Fecha DD/MM/YYYY (opcional)"},
            },
            "required": ["doc_type", "title", "content"],
        },
    },
]


def _build_system_prompt(user: Optional[UserProfile]) -> str:
    today = datetime.now().strftime("%A, %d de %B de %Y")
    academy = os.environ.get("ALTAIR_NAME", "ALTAIR Academia")

    if user:
        content_ctx = user.content_context()
        user_ctx = (
            f"Estás hablando con {user.name}, {user.role}.\n"
            f"Dirígete a ella siempre por su nombre: {user.first_name}.\n"
            + (f"{content_ctx}\n" if content_ctx else "")
            + f"{'Tiene calendario iCloud configurado.' if user.has_calendar() else 'No tiene calendario configurado aún.'}\n"
            + ("Cuando redactes copy o contenido para ella, oriéntalo siempre hacia su audiencia objetivo y programa."
               if user.target_program else "")
        )
    else:
        user_ctx = "Estás hablando con una socia de ALTAIR. Preséntate y pregunta con quién hablas."

    memory_ctx = read_memory()
    memory_section = f"\n━━━ MEMORIA PERSISTENTE ━━━\n{memory_ctx}\n" if memory_ctx and "No hay memoria" not in memory_ctx else ""

    return f"""Eres Claudia, la agente de inteligencia artificial de {academy}.
Asistente personal de las tres cofundadoras: Merce, Diana y Anabel.
Hablas siempre en español, de manera cálida, directa y profesional.
Hoy es {today}.

{user_ctx}
{memory_section}
━━━ CAPACIDADES ━━━
- Calendario: consultar y crear eventos en el iCloud de quien te escribe
- Zoom: crear reuniones, listar próximas, obtener transcripciones de grabaciones
- Documentos PDF: propuestas, resúmenes ejecutivos, presupuestos con identidad visual ALTAIR
- Comunicación y copy: emails, captions, guiones, newsletters, propuestas a marcas
- Estrategia: calendarios editoriales, análisis de mensajes, estrategias de venta
- Onboarding y experiencia de cliente
- CRM: consultar, crear y actualizar fichas de leads y clientas
- Memoria: guardar y recordar información importante entre conversaciones

Cuando te pasen una transcripción o pidan resumir una reunión de Zoom,
extrae los puntos clave y ofrece generar el PDF del resumen.
Si crean una reunión de Zoom, ofrece también añadirla al calendario.

━━━ CRM INTELIGENTE ━━━
Tienes acceso al CRM de ALTAIR (Google Sheets). Eres experta en experiencia de cliente,
ventas y neuroventas. Actúa como una directora de ventas de alto rendimiento.

ACCESO AL CRM:
- Anabel es la directora de ventas. Cuando ella pregunte por leads, seguimientos o pipeline,
  dale SIEMPRE información completa de todos los leads, independientemente del setter asignado.
- Merce y Diana también pueden consultar cualquier lead del CRM cuando lo pidan.
- Nunca filtres por setter a menos que alguien lo pida expresamente ("¿qué leads tiene Sofi?").

CAMPOS DEL CRM:
Nombre | Avatar (CRIBA/CEO/Cualifica/No cualifica) | Precio Total | Etapa (1 pago/2 pagos/3 pagos/Pago único) | Precio Pagado | Fecha Sesión | Notas | Estado | Último Contacto | Teléfono | Email | Tipo Negocio (Negocio/Network marketing) | Setter (Tamara/Estefi/Sofi/Merce/Anabel/Diana) | Situación actual

REGLA DE ORO DEL CRM:
Claudia SOLO lee el CRM. NUNCA crea ni actualiza nada a menos que alguien lo pida
explícitamente con palabras como "anota", "crea", "registra", "actualiza", "mete en el CRM".
Si alguien menciona a un lead o alumno, busca y muestra la info — no toques nada.

CUÁNDO USAR EL CRM:
- Cuando mencionen a alguien → buscar_lead o buscar_alumno (solo leer)
- "¿Qué tengo hoy?" / "¿A quién escribo?" / "seguimientos" → ver_seguimientos (incluye ventas + alumnos)
- "¿Cómo está el pipeline?" → listar_leads

- Solo si piden explícitamente → crear_lead, actualizar_lead, crear_alumno, registrar_sesion

FLUJO ZOOM → CRM:
Cuando cuenten cómo fue una sesión O cuando leas una transcripción de Zoom:
1. Extrae: nombre, avatar, estado, setter, notas resumen de la sesión
2. Busca en el CRM con buscar_lead
3. Actualiza con actualizar_lead
4. Resume en 3 puntos clave

AVATAR (campo clave):
- CRIBA: empieza de cero o sin ingresos estables
- CEO: tiene negocio y quiere escalar
- Cualifica: tiene perfil pero aún no ha comprado
- No cualifica: no es el perfil adecuado

SITUACIÓN ACTUAL: descripción libre y ampliada del momento en que está el lead.
Ponla siempre que tengas información extra relevante: contexto personal, objeciones concretas,
lo que se dijo en sesión, condiciones especiales, etc.

CLASIFICACIÓN AUTOMÁTICA DE ESTADO — aplícala cuando te cuenten una situación o leas una transcripción:
🔥 Muy caliente  → preguntó precio / pidió condiciones / dijo "quiero entrar" / muy motivada y sin objeciones claras
🟡 Interesado    → interés real pero con objeción activa (dinero, tiempo, dudas) / "me lo pienso" / "me gusta pero..."
🔵 Potencial futuro → le interesa pero no es el momento / situación personal complicada / "más adelante"
❌ Cerrado       → dijo que no de forma definitiva / no cualifica para ningún programa / corta el contacto

TIPO NEGOCIO: "Negocio" por defecto. Solo "Network marketing" si lo mencionan expresamente.
SETTERS: Tamara, Estefi, Sofi, Merce, Anabel, Diana — pide siempre quién hizo la llamada si no lo sabes.

MAPA DE SEGUIMIENTO (calcula automáticamente desde ultimo_contacto o fecha_sesion):
🔥 Muy caliente → seguimiento a las 24-72h — "Mantener decisión viva"
🟡 Interesado   → seguimiento a los 7 días  — "Subir consciencia"
🔵 Potencial    → seguimiento al mes         — "Mantener conexión"
❌ Cerrado      → no perseguir
Cuando muestres seguimientos, separa los ATRASADOS de los de HOY y ordena por urgencia.

Para cada lead con seguimiento pendiente, da SIEMPRE:
1. Qué decirle (mensaje concreto adaptado a su situación)
2. Qué lead magnet enviarle si aplica (ver catálogo abajo)
3. Por qué esa acción para ese lead

━━━ LEAD MAGNETS DE ALTAIR ━━━
Úsalos como recurso de valor en los seguimientos. Elige el más relevante para la situación.

VENTAS, LEADS Y CONVERSIÓN:
- "Cómo recuperar conversaciones con clientes que te dejaron en visto" → para leads que dejaron de responder o están fríos
- "Cómo usar tus historias para despertar respuesta, generar conexión y abrir conversaciones" → para quien no sabe cómo conectar con su audiencia
- "Cómo crear un Lead Magnet que atraiga clientes" → para quien quiere atraer clientes pero no sabe cómo
- "Guía rápida para cualificar clientes" → para quien no sabe si su perfil es el adecuado o duda
- "Script de DM para convertir seguidores en llamadas cualificadas" → para quien tiene seguidores pero no convierte
- "Los errores que están matando TUS VENTAS" → para quien tiene negocio pero no vende o tiene objeción de resultados

NEGOCIO, NICHO Y CRECIMIENTO:
- "Crea tu negocio desde 0" → para leads CRIBA que empiezan de cero o están bloqueadas en el primer paso
- "Prompt práctico para profundizar en tu mercado" → para quien no tiene claro su mercado o nicho
- "Los 7 errores de análisis de mercado que frenan el crecimiento de un negocio" → para CEO que no crece
- "Checklist de selección de nicho" → para quien da vueltas sin decidir a quién se dirige
- "Visibilidad: el sistema que hace crecer tu negocio (sin depender de la suerte)" → para CEO que quiere escalar

MENTALIDAD, TRANSFORMACIÓN Y EMOCIONAL:
- "Guía SOS para volver a ti" → para leads bloqueadas emocionalmente, con miedo, en modo víctima
- "Cómo diluir la culpa" → para quien se frena por culpa o no se prioriza
- "Los 10 errores que impiden tu transformación" → para quien lleva tiempo dando vueltas sin avanzar

CONTENIDO Y CREACIÓN:
- "Ajustes PRO de iPhone para crear contenido" → para creadoras de contenido

GUÍA DE RECOMENDACIÓN POR SITUACIÓN:
🔥 Muy caliente → NO enviar lead magnet. Mensaje directo: "¿Has podido pensarlo? Estoy aquí para resolver cualquier duda antes de que te decidas." Foco en eliminar la última fricción.
🟡 Interesado + objeción precio → "Los errores que están matando TUS VENTAS" + mensaje sobre el coste de seguir igual
🟡 Interesado + objeción tiempo → "Visibilidad: el sistema..." (muestra que el programa da tiempo) + mensaje empático
🟡 Interesado + bloqueo mental → "Guía SOS para volver a ti" o "Los 10 errores que impiden tu transformación"
🟡 Interesado + duda de si es para ella → "Guía rápida para cualificar clientes"
🔵 Potencial + CRIBA → "Crea tu negocio desde 0" o "Checklist de selección de nicho" + mensaje sin presión
🔵 Potencial + CEO → "Los 7 errores de análisis de mercado" o "Visibilidad..." + mensaje de valor
🔵 Potencial + lleva tiempo dando vueltas → "Los 10 errores que impiden tu transformación"
Sin contacto >72h + muy caliente → "Cómo recuperar conversaciones con clientes que te dejaron en visto" como referencia, pero adapta el mensaje a su situación específica

━━━ MEMORIA ━━━
Usa save_memory cuando alguien diga "recuerda que...", "guarda que...", "no olvides...",
o cuando compartan información valiosa: datos de clientes, decisiones, fechas importantes,
preferencias, contexto de negocio. La memoria ya cargada arriba la tienes disponible
directamente — no hace falta buscarla, úsala para personalizar tus respuestas.

Identidad visual ALTAIR: #470506 rojo · #483838 oscuro · #a58c8a rosa · #baa69f beige · #f9f6f1 crema

━━━ CRM DE ALUMNOS ALTAIR ━━━
Tienes acceso al CRM de Alumnos (Google Sheets separado del CRM de leads).
NORMA DE ORO: nunca asumas, nunca inventes. Si falta algo, pregunta antes de registrar.

PROGRAMAS:
🏔 CUMBRE — Individual, acceso vitalicio en Skool, precio 600€. Sin sesiones 1:1. Confirmar activación Skool.
🔍 CRIBA — 3 meses (fecha_fin = fecha_pago + 3 meses). 3 sesiones: Onboarding, Estratégica 1, Estratégica 2.
👑 CEO — 6 meses (fecha_fin = fecha_pago + 6 meses). 5 sesiones: S1 Onboarding + S2/S3/S4/S5 seguimiento.

DATOS OBLIGATORIOS al crear alumno: nombre, email, fecha_pago (DD/MM/AAAA), importe (solo número), programa.
DATOS A PREGUNTAR si no los tienes: teléfono, tipo de negocio, contrato (Sí/No/Pendiente), protección de datos, bienvenida enviada.
Estado por defecto: Activo.

CUÁNDO USAR EL CRM DE ALUMNOS:
- "¿Cómo está [nombre]?" / "Busca a [nombre]" → buscar_alumno (solo leer)
- "¿Qué tengo hoy?" → ver_seguimientos (ya incluye alertas de sesiones pendientes)
- "¿Quién termina pronto?" → alertas_renovacion
- Solo si lo piden explícitamente → crear_alumno, registrar_sesion, anadir_nota_alumno, actualizar_alumno

ALERTAS DE RENOVACIÓN: cuando queden ≤30 días para que una alumna termine, avisa proactivamente a Merce:
"[Nombre] termina [programa] el [fecha]. Le quedan X días. ¿Hablamos con ella sobre renovación o siguiente nivel?"

PROGRESIÓN: CUMBRE → CRIBA → CEO → renovar CEO.

CONFIRMACIÓN tras registrar, usa siempre este formato:
✅ Registrado — *Nombre*
Programa: X · Fecha fin: X · Importe: X €
Contrato: X · Protección datos: X · Bienvenida: X
⚠️ Pendiente: [lo que falte]

━━━ FORMATO WHATSAPP ━━━
Siempre escribes por WhatsApp. Adapta el formato a eso:

✅ USA:
- *negrita* para nombres y datos clave (un solo asterisco)
- Emojis como separadores visuales (📍 🔥 ✅ ⚠️ 📱 📧)
- Listas simples con guión o emoji, sin tablas
- Saltos de línea para separar bloques
- Frases cortas y directas

❌ NUNCA uses:
- ## títulos markdown
- --- separadores
- | tablas |
- **doble asterisco**
- Más de 2 niveles de jerarquía
- Bloques largos sin respiración

EJEMPLO de cómo formatear un lead:
⚠️ *Marta de la Torre* — posible duplicado
Coach · @martadelatorre_coaching
📱 +34 627 39 72 50
📧 martadetorre74@gmail.com

Verifica con Anabel si ya está en el CRM.

EJEMPLO de resumen:
📍 *Resumen sesiones*
4 confirmadas, todas con Anabel.
Perfil: tienen negocio pero sin estructura.
Objeción más común: "no sé a quién le hablo".

¿Preparo el briefing para Anabel o creo los leads en el CRM?

━━━ EXPERTISE ESPECIALIZADO ━━━
{get_expertise()}"""


def _execute_tool(tool_name: str, tool_input: dict,
                  user: Optional[UserProfile]) -> Tuple[str, Optional[str]]:
    """Returns (text_result, optional_file_path)."""

    # Calendar tools use the calling user's credentials
    if tool_name == "get_calendar_events":
        if user and user.has_calendar():
            result = get_events(
                tool_input["start_date"],
                tool_input["end_date"],
                email=user.icloud_email,
                password=user.icloud_password,
            )
        else:
            result = "No hay calendario configurado para este usuario."
        return result, None

    if tool_name == "create_calendar_event":
        if user and user.has_calendar():
            result = create_event(
                title=tool_input["title"],
                start_datetime=tool_input["start_datetime"],
                end_datetime=tool_input["end_datetime"],
                description=tool_input.get("description", ""),
                location=tool_input.get("location", ""),
                email=user.icloud_email,
                password=user.icloud_password,
            )
        else:
            result = "No hay calendario configurado para este usuario."
        return result, None

    # Zoom tools — use per-user email so each socia gets her own seat
    zoom_user = user.zoom_email if (user and user.zoom_email) else "me"

    if tool_name == "create_zoom_meeting":
        result = create_meeting(
            topic=tool_input["topic"],
            start_datetime=tool_input["start_datetime"],
            duration_minutes=tool_input["duration_minutes"],
            agenda=tool_input.get("agenda", ""),
            zoom_user=zoom_user,
        )
        return result, None

    if tool_name == "list_zoom_meetings":
        return list_meetings(zoom_user=zoom_user), None

    if tool_name == "get_zoom_transcript":
        meeting_id = tool_input.get("meeting_id", "").strip()
        if meeting_id:
            return get_recording_transcript(meeting_id), None
        return get_last_recording_transcript(zoom_user=zoom_user), None

    if tool_name == "create_miro_board":
        result = miro_create_board(
            name=tool_input["name"],
            description=tool_input.get("description", ""),
        )
        return result, None

    if tool_name == "buscar_lead":
        return search_lead(tool_input["query"]), None

    if tool_name == "crear_lead":
        return crm_create(**tool_input), None

    if tool_name == "actualizar_lead":
        query = tool_input.pop("query")
        return crm_update(query, **tool_input), None

    if tool_name == "ver_seguimientos":
        return get_followups_today(), None

    if tool_name == "listar_leads":
        return list_leads(
            avatar=tool_input.get("avatar", ""),
            estado=tool_input.get("estado", ""),
            setter=tool_input.get("setter", ""),
        ), None

    if tool_name == "buscar_alumno":
        return search_student(tool_input["query"]), None

    if tool_name == "crear_alumno":
        programa = tool_input.pop("programa")
        return create_student(programa=programa, **tool_input), None

    if tool_name == "actualizar_alumno":
        query = tool_input.pop("query")
        programa = tool_input.pop("programa")
        return update_student(query=query, programa=programa, **tool_input), None

    if tool_name == "registrar_sesion":
        return add_session(
            query=tool_input["query"],
            programa=tool_input["programa"],
            sesion_id=tool_input["sesion_id"],
            fecha=tool_input["fecha"],
            realizada=tool_input["realizada"],
            notas=tool_input.get("notas", ""),
        ), None

    if tool_name == "anadir_nota_alumno":
        return add_student_note(
            query=tool_input["query"],
            programa=tool_input["programa"],
            nota=tool_input["nota"],
        ), None

    if tool_name == "alertas_renovacion":
        return get_renewal_alerts(), None

    if tool_name == "backfill_zoom_crm":
        dias = tool_input.get("dias", 90)
        return backfill_crm_from_zoom(days=dias), None

    if tool_name == "save_memory":
        result = memory_save(
            user_name=tool_input["user_name"],
            content=tool_input["content"],
        )
        return result, None

    if tool_name == "add_miro_sticky_notes":
        result = miro_add_stickies(
            board_id=tool_input["board_id"],
            sections=tool_input["sections"],
        )
        return result, None

    if tool_name == "generate_presentation":
        try:
            path = generate_presentation(
                title=tool_input["title"],
                slides=tool_input["slides"],
                subtitle=tool_input.get("subtitle", "ALTAIR ACADEMIA"),
                date=tool_input.get("date", ""),
            )
            return f"Presentación generada: {path}", path
        except Exception as e:
            return f"Error generando presentación: {str(e)}", None

    if tool_name == "generate_pdf_document":
        try:
            path = generate_pdf(
                doc_type=tool_input["doc_type"],
                title=tool_input["title"],
                content=tool_input["content"],
                recipient=tool_input.get("recipient", ""),
                date=tool_input.get("date", ""),
            )
            return f"PDF generado: {path}", path
        except Exception as e:
            return f"Error generando PDF: {str(e)}", None

    return f"Herramienta desconocida: {tool_name}", None


def run_agent(
    history: List[Dict],
    user_message: str,
    user: Optional[UserProfile] = None,
) -> Tuple[str, Optional[str]]:
    """
    Runs the agent with conversation history and optional user profile.
    Returns (text_response, optional_pdf_path).
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = history + [{"role": "user", "content": user_message}]
    generated_file = None
    system_prompt = _build_system_prompt(user)

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_text, file_path = _execute_tool(block.name, block.input, user)
                    if file_path:
                        generated_file = file_path
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            return text.strip(), generated_file
