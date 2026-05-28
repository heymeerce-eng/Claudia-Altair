"""
Genera el PDF de presentación de Claudia para Anabel y Diana.
Ejecutar: source .venv/bin/activate && python generate_claudia_socias.py
"""

import os
from datetime import datetime
from fpdf import FPDF

CREAM      = (249, 246, 241)
DARK_BROWN = (72, 56, 56)
DARK_RED   = (71, 5, 6)
ROSE       = (165, 140, 138)
BEIGE      = (186, 166, 159)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "documentos")
W = 170  # usable width (A4 - margins)


class AltairPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-14)
            self.set_font("Helvetica", size=7)
            self.set_text_color(*ROSE)
            self.cell(0, 8, "ALTAIR ACADEMIA  |  CLAUDIA", align="C")

    def _bg(self, color):
        self.set_fill_color(*color)
        self.rect(0, 0, 210, 297, "F")

    def _hline(self, y, x1=20, x2=190, color=DARK_RED, lw=0.4):
        self.set_draw_color(*color)
        self.set_line_width(lw)
        self.line(x1, y, x2, y)

    # ── PORTADA ───────────────────────────────────────────────────────
    def cover(self, title, subtitle, tagline, date):
        self.add_page()
        self._bg(CREAM)
        self._hline(22)

        self.set_y(80)
        self.set_font("Helvetica", size=60)
        self.set_text_color(*DARK_BROWN)
        self.cell(0, 24, title, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", size=15)
        self.set_text_color(*ROSE)
        self.cell(0, 10, subtitle, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)
        self._hline(self.get_y(), x1=70, x2=140, color=ROSE, lw=0.25)
        self.ln(8)

        self.set_font("Helvetica", "I", 11)
        self.set_text_color(*DARK_BROWN)
        self.set_x(20)
        self.multi_cell(W, 7, tagline, align="C")

        self.set_y(-30)
        self._hline(self.get_y())
        self.ln(3)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*BEIGE)
        self.cell(0, 5, f"ALTAIR ACADEMIA  |  {date}", align="C")

    # ── PÁGINA DIVISORA ───────────────────────────────────────────────
    def divider(self, number, title):
        self.add_page()
        self._bg(BEIGE)
        self.set_y(110)
        self.set_font("Helvetica", size=11)
        self.set_text_color(*DARK_RED)
        self.cell(0, 8, number, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font("Helvetica", size=26)
        self.set_text_color(*DARK_BROWN)
        self.cell(0, 14, title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self._hline(self.get_y(), x1=80, x2=130, color=DARK_RED, lw=0.25)

    # ── PÁGINA DE CONTENIDO ───────────────────────────────────────────
    def content(self, page_title, blocks):
        """blocks: list of ("heading"|None, "body text") or just "text string"."""
        self.add_page()
        self._bg(CREAM)

        self.set_xy(20, 22)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*DARK_RED)
        self.cell(0, 10, page_title, new_x="LMARGIN", new_y="NEXT")
        self._hline(self.get_y() + 1, color=ROSE, lw=0.25)
        self.ln(7)

        for block in blocks:
            if isinstance(block, tuple):
                heading, body = block
                if heading:
                    self.set_x(20)
                    self.set_font("Helvetica", "B", 11)
                    self.set_text_color(*DARK_BROWN)
                    self.multi_cell(W, 6, heading)
                    self.ln(1)
                self.set_x(20)
                self.set_font("Helvetica", size=11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 6, body)
                self.ln(5)
            else:
                self.set_x(20)
                self.set_font("Helvetica", size=11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 6, block)
                self.ln(5)

    # ── PÁGINA DE BULLETS ─────────────────────────────────────────────
    def bullets(self, page_title, sections):
        """sections: dict {section_title: [bullet, bullet, ...]}"""
        self.add_page()
        self._bg(CREAM)

        self.set_xy(20, 22)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*DARK_RED)
        self.cell(0, 10, page_title, new_x="LMARGIN", new_y="NEXT")
        self._hline(self.get_y() + 1, color=ROSE, lw=0.25)
        self.ln(7)

        for section, items in sections.items():
            if section:
                self.set_x(20)
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 7, section)
                self.ln(1)
            for item in items:
                self.set_x(26)
                self.set_font("Helvetica", size=10)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W - 6, 5.5, f"- {item}")
                self.ln(1)
            self.ln(4)

    # ── PÁGINA PASO A PASO NUMERADO ───────────────────────────────────
    def steps(self, page_title, sections):
        """sections: dict {section_title: [(step_label, description), ...]}"""
        self.add_page()
        self._bg(CREAM)

        self.set_xy(20, 22)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*DARK_RED)
        self.cell(0, 10, page_title, new_x="LMARGIN", new_y="NEXT")
        self._hline(self.get_y() + 1, color=ROSE, lw=0.25)
        self.ln(7)

        for section, step_list in sections.items():
            if section:
                self.set_x(20)
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 7, section)
                self.ln(2)

            for label, desc in step_list:
                # Numbered box
                self.set_fill_color(*DARK_RED)
                self.set_xy(20, self.get_y())
                box_h = 6
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(249, 246, 241)
                self.cell(22, box_h, label, fill=True, align="C")
                # Description next to box
                self.set_font("Helvetica", size=10)
                self.set_text_color(*DARK_BROWN)
                x_after = self.get_x() + 3
                self.set_xy(x_after, self.get_y())
                self.multi_cell(W - 25, box_h, desc)
                self.ln(2)
            self.ln(5)


def generate():
    pdf = AltairPDF()
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(20, 20, 20)

    today = datetime.now().strftime("%d de mayo de 2026")

    # ── PORTADA ───────────────────────────────────────────────────────
    pdf.cover(
        "CLAUDIA",
        "Vuestra asistente personal de inteligencia artificial",
        "Una propuesta para que las tres trabajemos menos horas\ny consigamos mas sin agotarnos.",
        today,
    )

    # ── 01 · QUE ES ───────────────────────────────────────────────────
    pdf.divider("01", "Que es Claudia")
    pdf.content(
        "Claudia en una frase",
        [
            (None,
             "Claudia es una inteligencia artificial entrenada especificamente para ALTAIR. "
             "No es ChatGPT ni un asistente generico. Conoce vuestros programas, vuestras audiencias, "
             "vuestra forma de comunicar y habla con voz de ALTAIR."),
            ("Como se usa",
             "Directamente desde WhatsApp. Sin instalar nada nuevo, sin aprender ningun software. "
             "Le escribis igual que le escribiriaisua amiga. Ella gestiona el resto."),
            ("Por que la hemos creado",
             "Las tres dedicais tiempo a tareas que se pueden automatizar: revisar el calendario, "
             "crear reuniones de Zoom, redactar propuestas, resumir grabaciones, escribir captions... "
             "Claudia hace todo eso en segundos para que vosotras os enfoqueis en lo que solo vosotras podeis hacer."),
            ("La logica ALTAIR aplicada a nosotras mismas",
             "Ventas predecibles y crecer sin quemarse. Claudia es la herramienta que nos permite "
             "practicar lo que ensenamos."),
        ],
    )

    # ── 02 · QUE HACE ─────────────────────────────────────────────────
    pdf.divider("02", "Lo que Claudia hace hoy")
    pdf.bullets(
        "Capacidades actuales",
        {
            "Calendario iCloud": [
                '"Que tengo esta semana?" -> respuesta inmediata desde WhatsApp',
                '"Crea una reunion el jueves a las 10h" -> lo anade directamente a tu iCloud',
                "Funciona de forma individual para cada una (cada socia ve su propio calendario)",
            ],
            "Zoom": [
                '"Crea una reunion de Zoom para manana a las 12h" -> genera el enlace listo para compartir',
                '"Resume la ultima reunion grabada" -> extrae y sintetiza la transcripcion automaticamente',
                '"Lista mis proximas reuniones" -> vista rapida de agenda sin abrir Zoom',
            ],
            "Documentos PDF con identidad ALTAIR": [
                "Propuestas comerciales para marcas y colaboraciones",
                "Presupuestos y cotizaciones formateadas",
                "Resumenes ejecutivos de reuniones",
                "Todo con vuestros colores (#470506, #a58c8a, #f9f6f1) y tipografia",
            ],
            "Presentaciones PowerPoint": [
                "Pitch decks de programas CRIBA y CEO",
                "Presentaciones de estrategia interna",
                "Exportables a Keynote o Google Slides, con identidad ALTAIR",
            ],
            "Tableros Miro": [
                "Customer journeys de alumnas",
                "Calendarios editoriales visuales por semanas",
                "Mapas de estrategia y sesiones de brainstorming",
            ],
            "Contenido y copy especializado": [
                "Captions de Instagram adaptados a tu audiencia especifica (Merce -> CRIBA, Anabel y Diana -> CEO)",
                "Emails de venta con framework PASTOR (orientados al programa correcto)",
                "Guiones de Reels y stories",
                "Secuencias de seguimiento post-venta (sin presion, estilo ALTAIR)",
                "Newsletters y comunicaciones a alumnas",
                "Manejo de objeciones en DMs con voz propia de cada una",
            ],
        },
    )

    # ── 03 · TIEMPO ───────────────────────────────────────────────────
    pdf.divider("03", "El tiempo que Claudia os devuelve")
    pdf.content(
        "Comparativa real",
        [
            ("Redactar una propuesta comercial",
             "Sin Claudia: 2 horas de borrador, revision y formateo.\n"
             "Con Claudia: 5 minutos. Lista en PDF con identidad ALTAIR para enviar."),
            ("Resumir una reunion de Zoom grabada",
             "Sin Claudia: 30 minutos de escuchar la grabacion y tomar notas.\n"
             "Con Claudia: 30 segundos. Os devuelve los puntos clave y os pregunta si quereis el PDF del resumen."),
            ("Crear un calendario editorial mensual",
             "Sin Claudia: 1-2 horas entre ideas, estructura y formato.\n"
             "Con Claudia: 2 minutos. Incluyendo el tablero Miro visual si lo quereis."),
            ("Redactar un email de venta",
             "Sin Claudia: 45-60 minutos con el framework correcto.\n"
             "Con Claudia: 3 minutos, adaptado a vuestro programa y audiencia."),
            ("Consultar disponibilidad en el calendario",
             "Sin Claudia: abrir la app, navegar por semanas, volver a WhatsApp.\n"
             "Con Claudia: preguntais desde WhatsApp y la respuesta llega al instante."),
            ("Una caption para Instagram",
             "Sin Claudia: 20-30 minutos pensando el hook, el cuerpo y el CTA.\n"
             "Con Claudia: 2 minutos con la estructura correcta y el tono de vuestra audiencia."),
        ],
    )

    # ── 04 · PASO A PASO ──────────────────────────────────────────────
    pdf.divider("04", "Como tenerla: paso a paso")
    pdf.steps(
        "Para Anabel y Diana (la forma mas sencilla)",
        {
            "Solo necesitais tres pasos:": [
                ("PASO 1", "Merce anade vuestro numero de WhatsApp a la configuracion de Claudia (lo hace ella, vosotras no tocais nada)"),
                ("PASO 2", "Guardais el numero de Claudia en vuestros contactos de movil"),
                ("PASO 3", "Le escribis un mensaje y empezais a usarla"),
            ],
            "Si quereis arrancar Claudia tambien en vuestro propio ordenador (opcional):": [
                ("PASO 1", "Instalar Python: ir a python.org -> Download -> ejecutar el instalador (como instalar cualquier app)"),
                ("PASO 2", "Pedirle la carpeta del proyecto a Merce (por AirDrop o Google Drive)"),
                ("PASO 3", "Abrir el archivo .env y rellenar vuestras credenciales de iCloud y WhatsApp"),
                ("PASO 4", 'Abrir Terminal y escribir: python run.py - Claudia arranca y os da una URL para conectar WhatsApp'),
            ],
        },
    )

    # ── 05 · FUTURO ───────────────────────────────────────────────────
    pdf.divider("05", "Lo que Claudia podra hacer")
    pdf.bullets(
        "Proximas integraciones",
        {
            "Automatizaciones de negocio": [
                "Gestionar el onboarding de nuevas alumnas automaticamente",
                "Recordatorios de seguimiento a leads que no han respondido",
                "Responder preguntas frecuentes en DMs con vuestra propia voz",
            ],
            "Integraciones de herramientas": [
                "Notion y Google Drive: acceder a documentos y notas desde WhatsApp",
                "Google Slides: presentaciones en la nube directamente",
                "Metricas de contenido: alcance, guardados y conversiones de cada post",
            ],
            "Contenido avanzado": [
                "Generar borradores a partir de notas de voz en WhatsApp",
                "Crear secuencias completas de email de bienvenida para nuevas alumnas",
                "Diseno del customer journey de cada programa en Miro",
            ],
            "CUMBRE (cuando lanceis el programa)": [
                "Claudia ya conoce el programa. Puede crear todo el material de venta, onboarding y seguimiento desde el primer dia.",
            ],
        },
    )

    # ── 06 · INVERSION ────────────────────────────────────────────────
    pdf.divider("06", "La inversion y los siguientes pasos")
    pdf.content(
        "Que necesitamos para empezar",
        [
            ("Cuanto cuesta",
             "Claudia ya esta construida y funcionando. No hay coste de desarrollo.\n\n"
             "Coste de uso: aproximadamente 20-40 euros al mes para las tres (API de Claude con uso normal). "
             "Eso es menos de 15 euros por socia al mes."),
            ("Que necesita cada una de vosotras",
             "- Vuestro numero de WhatsApp (Merce lo anade a la config)\n"
             "- Las credenciales de iCloud para el calendario (se generan en appleid.apple.com -> Seguridad -> Contrasenas de aplicaciones)\n"
             "- Nada mas"),
            ("Los siguientes pasos",
             "1. Merce comparte la configuracion con Anabel y Diana\n"
             "2. Cada una anade sus credenciales en 10 minutos\n"
             "3. Las tres empezamos a usarla esta semana\n"
             "4. En 30 dias decidimos que nuevas integraciones queremos"),
            ("Una ultima cosa",
             "Claudia conoce vuestros programas, vuestras audiencias y vuestra forma de comunicar. "
             "Cuanto mas la useis, mejores resultados os dara.\n\n"
             "Es vuestra asistente, no una herramienta generica."),
        ],
    )

    # ── GUARDAR ───────────────────────────────────────────────────────
    os.makedirs(DOCS_DIR, exist_ok=True)
    path = os.path.join(DOCS_DIR, "claudia_para_las_socias.pdf")
    pdf.output(path)
    print(f"PDF generado: {path}")
    return path


if __name__ == "__main__":
    generate()
