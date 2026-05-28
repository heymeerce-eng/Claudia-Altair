"""
Generador de la propuesta ALTAIR para Claudia.
Ejecutar con: source .venv/bin/activate && python generate_proposal.py
"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from pathlib import Path
import re

# ── Paleta de colores ──────────────────────────────────────────────
RED    = (71,  5,   6)    # #470506
DARK   = (72,  56,  56)   # #483838
ROSE   = (165, 140, 138)  # #a58c8a
BEIGE  = (186, 166, 159)  # #baa69f
CREAM  = (249, 246, 241)  # #f9f6f1
WHITE  = (255, 255, 255)

# ── Rutas de fuentes ───────────────────────────────────────────────
FONTS = "/System/Library/Fonts/Supplemental"
ARIAL        = f"{FONTS}/Arial.ttf"
ARIAL_BOLD   = f"{FONTS}/Arial Bold.ttf"
ARIAL_ITALIC = f"{FONTS}/Arial Italic.ttf"
GEORGIA      = f"{FONTS}/Georgia.ttf"
GEORGIA_BOLD = f"{FONTS}/Georgia Bold.ttf"

OUTPUT = Path(__file__).parent / "documentos" / "propuesta_claudia_altair.pdf"
OUTPUT.parent.mkdir(exist_ok=True)


# ── Contenido de la propuesta ──────────────────────────────────────
SECTIONS = [
    {
        "heading": "El reto de hoy",
        "body": (
            "Gestionar una academia como ALTAIR implica una carga operativa enorme: "
            "responder mensajes, preparar materiales, coordinar calendarios, redactar propuestas, "
            "crear contenido para redes, resumir reuniones… tareas que consumen horas "
            "que podrían dedicarse a lo que realmente importa: crear, enseñar y crecer.\n\n"
            "La inteligencia artificial ha llegado a un punto en el que no es solo una herramienta "
            "de búsqueda o generación de texto. Hoy es posible tener un agente personal que "
            "entiende el contexto, recuerda conversaciones anteriores, conecta con tus herramientas "
            "y actúa en tu nombre — disponible las 24 horas, directamente desde WhatsApp."
        ),
    },
    {
        "heading": "Qué es Claudia",
        "body": (
            "Claudia es un agente de inteligencia artificial personalizado para ALTAIR. "
            "No es un chatbot genérico: está construida sobre el modelo Claude de Anthropic "
            "(el mismo nivel tecnológico que ChatGPT pero con mayor precisión en contexto largo) "
            "y configurada específicamente para vuestro flujo de trabajo.\n\n"
            "Funciona directamente desde WhatsApp. Le escribes como le escribirías a una "
            "asistente de confianza — y ella actúa."
        ),
    },
    {
        "heading": "Lo que Claudia hace por ALTAIR",
        "items": [
            ("Gestión de agenda",
             "Consulta, crea y modifica eventos en vuestro calendario. «¿Qué tenemos esta semana?», "
             "«Programa una reunión de socias el jueves a las 10» — lo hace directamente."),
            ("Propuestas y presupuestos en PDF",
             "A partir de una conversación o una transcripción, genera documentos profesionales "
             "con vuestra identidad visual: propuestas de colaboración, presupuestos de servicios, "
             "resúmenes ejecutivos."),
            ("Contenido y guiones",
             "Redacta guiones para Reels, captions para Instagram, newsletters, descripciones "
             "de cursos, emails a alumnas — con la voz de ALTAIR."),
            ("Estrategia de contenido",
             "Propone calendarios editoriales, analiza tendencias, sugiere formatos y temas "
             "alineados con vuestros objetivos y temporada."),
            ("Resúmenes de reuniones",
             "Pégale una transcripción o grabación y obtén un resumen ejecutivo estructurado "
             "con puntos clave, decisiones y próximos pasos — en PDF listo para compartir."),
            ("Recursos y materiales",
             "Genera temarios, fichas de cursos, materiales descargables, FAQs para alumnas "
             "o cualquier documento que necesitéis."),
        ],
    },
    {
        "heading": "Tiempo estimado ahorrado",
        "table": [
            ("Tarea", "Tiempo actual", "Con Claudia"),
            ("Redactar una propuesta",      "2–3 horas",   "10 minutos"),
            ("Preparar un presupuesto",     "45 minutos",  "5 minutos"),
            ("Resumir una reunión",         "30 minutos",  "2 minutos"),
            ("Crear un guion para Reel",    "1 hora",      "8 minutos"),
            ("Calendario editorial mensual","2–3 horas",   "20 minutos"),
            ("Responder/redactar emails",   "1 hora/día",  "15 min/día"),
        ],
        "footer": "Estimación conservadora basada en casos de uso reales con agentes de IA.",
    },
    {
        "heading": "Cómo funciona",
        "body": (
            "Claudia vive en vuestro servidor (o en la nube) y se conecta a WhatsApp "
            "a través de la API oficial de Twilio. No necesitáis instalar ninguna app nueva: "
            "simplemente le escribís a un número de WhatsApp.\n\n"
            "Tiene memoria de conversación, lo que significa que recuerda el contexto "
            "de mensajes anteriores dentro de cada sesión. Cada socia puede tener "
            "su propio hilo de conversación independiente.\n\n"
            "Los PDFs que genera utilizan vuestra identidad visual: paleta de colores, "
            "tipografía y datos de contacto. Cada documento sale listo para enviar."
        ),
    },
    {
        "heading": "Próximos pasos",
        "items": [
            ("1.  Activar el entorno",
             "Configuramos Claudia con las credenciales de ALTAIR (calendario, WhatsApp, identidad visual)."),
            ("2.  Sesión de onboarding",
             "Media hora para que las tres socias probéis Claudia en vivo con casos reales."),
            ("3.  Ajuste y personalización",
             "Durante las primeras dos semanas, refinamos las respuestas y añadimos "
             "flujos específicos para ALTAIR."),
            ("4.  En producción",
             "Claudia disponible 24/7 para las socias directamente desde WhatsApp."),
        ],
    },
]


# ── Clase PDF ──────────────────────────────────────────────────────
class ProposalPDF(FPDF):

    def __init__(self):
        super().__init__()
        self.add_font("Arial",        "", ARIAL)
        self.add_font("Arial",        "B", ARIAL_BOLD)
        self.add_font("Arial",        "I", ARIAL_ITALIC)
        self.add_font("Georgia",      "", GEORGIA)
        self.add_font("Georgia",      "B", GEORGIA_BOLD)
        self.set_auto_page_break(auto=True, margin=22)

    def _set_fill(self, rgb):
        self.set_fill_color(*rgb)

    def _set_text(self, rgb):
        self.set_text_color(*rgb)

    def _set_draw(self, rgb):
        self.set_draw_color(*rgb)

    # ── Header ──
    def header(self):
        if self.page_no() == 1:
            return
        # Small strip on subsequent pages
        self._set_fill(RED)
        self.rect(0, 0, 210, 10, "F")
        self._set_text(CREAM)
        self.set_font("Georgia", "", 8)
        self.set_xy(0, 1.5)
        self.cell(105, 7, "Merce Cardenal", align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_x(105)
        self.cell(95, 7, "Claudia para ALTAIR", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Accent line
        self._set_fill(ROSE)
        self.rect(0, 10, 210, 1, "F")
        self.set_y(16)

    def footer(self):
        self.set_y(-14)
        self._set_fill(DARK)
        self.rect(0, self.get_y(), 210, 20, "F")
        self._set_text(BEIGE)
        self.set_font("Arial", "", 7.5)
        self.set_x(16)
        self.cell(130, 8, "heymeerce@gmail.com", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(50, 8, f"Página {self.page_no()}", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Page 1 cover ──
    def cover(self):
        self.add_page()

        # Header band
        self._set_fill(RED)
        self.rect(0, 0, 210, 42, "F")
        self._set_fill(ROSE)
        self.rect(0, 42, 210, 1.5, "F")

        self._set_text(CREAM)
        self.set_font("Georgia", "", 24)
        self.set_xy(16, 10)
        self.cell(0, 10, "Merce Cardenal", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(16)
        self.set_font("Arial", "", 8)
        self._set_text((249, 230, 228))
        self.cell(0, 6, "CREADORA DE CONTENIDO  ·  ESTRATEGIA  ·  ALTAIR",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Title band
        self._set_fill(DARK)
        self.rect(0, 43.5, 210, 52, "F")
        self._set_text(BEIGE)
        self.set_font("Arial", "", 7.5)
        self.set_xy(16, 50)
        self.cell(0, 5, "PROPUESTA", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_text(CREAM)
        self.set_font("Georgia", "B", 22)
        self.set_xy(16, 56)
        self.multi_cell(178, 10, "Claudia: inteligencia\nartificial para ALTAIR",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Meta row
        self.set_y(97)
        self._set_fill(BEIGE)
        self.rect(0, 97, 210, 0.5, "F")
        self._set_text(ROSE)
        self.set_font("Arial", "", 7)
        self.set_xy(16, 100)
        self.cell(80, 5, "PARA", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_x(140)
        self.cell(54, 5, "FECHA", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_text(DARK)
        self.set_font("Arial", "B", 10)
        self.set_xy(16, 106)
        self.cell(80, 6, "Socias de ALTAIR Academia", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_x(140)
        self.cell(54, 6, "Mayo 2026", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_fill(BEIGE)
        self.rect(0, 113, 210, 0.5, "F")

        # Intro paragraph
        self._set_text(DARK)
        self.set_font("Arial", "", 10.5)
        self.set_xy(16, 120)
        intro = (
            "Esta propuesta presenta Claudia, un agente de inteligencia artificial personalizado "
            "para ALTAIR. Su objetivo es simple: liberar tiempo de las socias automatizando "
            "las tareas operativas y de comunicación que hoy consumen horas cada semana, "
            "para que podáis dedicaros a lo que realmente importa."
        )
        self.multi_cell(178, 6.5, intro)

    # ── Section heading ──
    def section_heading(self, text):
        self.ln(4)
        y = self.get_y()
        self._set_fill(RED)
        self.rect(16, y, 3, 7, "F")
        self._set_text(RED)
        self.set_font("Georgia", "B", 13)
        self.set_xy(22, y - 0.5)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._set_fill(BEIGE)
        self.rect(16, self.get_y(), 178, 0.4, "F")
        self.ln(4)

    # ── Body text ──
    def body(self, text):
        self._set_text(DARK)
        self.set_font("Arial", "", 10.2)
        self.set_x(16)
        self.multi_cell(178, 6.2, text)

    # ── Bullet items ──
    def bullet_items(self, items):
        for title, desc in items:
            y = self.get_y()
            # Bullet dot
            self._set_fill(ROSE)
            self.rect(16, y + 2.5, 2, 2, "F")
            # Title
            self._set_text(DARK)
            self.set_font("Arial", "B", 10.2)
            self.set_xy(21, y)
            self.multi_cell(173, 6, title)
            # Description
            self._set_text((90, 75, 75))
            self.set_font("Arial", "", 9.8)
            self.set_x(21)
            self.multi_cell(173, 5.8, desc)
            self.ln(2)

    # ── Time table ──
    def time_table(self, rows, footer_text):
        header = rows[0]
        data = rows[1:]
        col_w = [88, 45, 45]
        self.ln(2)

        # Table header
        self._set_fill(DARK)
        self._set_text(CREAM)
        self.set_font("Arial", "B", 9)
        self.set_x(16)
        for i, h in enumerate(header):
            self.cell(col_w[i], 8, h, border=0, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln(8)

        # Rows
        for idx, row in enumerate(data):
            self._set_fill(CREAM if idx % 2 == 0 else (242, 238, 234))
            self._set_text(DARK)
            self.set_font("Arial", "", 9.5)
            self.set_x(16)
            self.cell(col_w[0], 7.5, row[0], border=0, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.TOP)
            self._set_text(ROSE)
            self.set_font("Arial", "", 9.2)
            self.cell(col_w[1], 7.5, row[1], align="C", border=0, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.TOP)
            self._set_text(RED)
            self.set_font("Arial", "B", 9.5)
            self.cell(col_w[2], 7.5, row[2], align="C", border=0, fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Bottom border
        self._set_fill(RED)
        self.rect(16, self.get_y(), 178, 1, "F")
        self.ln(5)

        # Footer note
        self._set_text(ROSE)
        self.set_font("Arial", "I", 8.2)
        self.set_x(16)
        self.cell(178, 5, footer_text)
        self.ln(7)

    # ── Closing box ──
    def closing_box(self):
        self.ln(6)
        y = self.get_y()
        self._set_fill((245, 241, 237))
        self.rect(16, y, 178, 24, "F")
        self._set_fill(RED)
        self.rect(16, y, 3, 24, "F")
        self._set_text(DARK)
        self.set_font("Georgia", "B", 11)
        self.set_xy(22, y + 4)
        self.cell(0, 6, "¿Empezamos?", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(22)
        self._set_text((90, 75, 75))
        self.set_font("Arial", "", 9.5)
        self.cell(0, 5.5, "heymeerce@gmail.com  ·  Merce Cardenal")


# ── Build PDF ─────────────────────────────────────────────────────
def build():
    pdf = ProposalPDF()
    pdf.cover()
    pdf.add_page()

    for section in SECTIONS:
        pdf.section_heading(section["heading"])

        if "body" in section:
            pdf.body(section["body"])

        if "items" in section:
            pdf.bullet_items(section["items"])

        if "table" in section:
            pdf.time_table(section["table"], section.get("footer", ""))

        pdf.ln(2)

    pdf.closing_box()
    pdf.output(str(OUTPUT))
    print(f"PDF generado: {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
