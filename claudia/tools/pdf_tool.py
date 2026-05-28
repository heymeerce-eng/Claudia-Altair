import os
import re
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

OUTPUT_DIR = Path(__file__).parent.parent.parent / "documentos"

CREAM      = (249, 246, 241)
DARK_BROWN = (72, 56, 56)
DARK_RED   = (71, 5, 6)
ROSE       = (165, 140, 138)
BEIGE      = (186, 166, 159)

W = 170  # usable width on A4


class AltairPDF(FPDF):
    def __init__(self, doc_type="proposal"):
        super().__init__()
        self.doc_type = doc_type
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=22)

    def header(self):
        pass

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-14)
            self.set_font("Helvetica", size=7)
            self.set_text_color(*ROSE)
            altair_name = os.environ.get("ALTAIR_NAME", "ALTAIR Academia")
            self.cell(0, 8, altair_name.upper(), align="C")

    def _bg(self):
        self.set_fill_color(*CREAM)
        self.rect(0, 0, 210, 297, "F")

    def _hline(self, y, x1=20, x2=190, color=DARK_RED, lw=0.4):
        self.set_draw_color(*color)
        self.set_line_width(lw)
        self.line(x1, y, x2, y)

    def cover(self, title, doc_type_label, recipient, date):
        self.add_page()
        self._bg()
        self._hline(22)

        self.set_y(75)
        self.set_font("Helvetica", size=9)
        self.set_text_color(*ROSE)
        self.cell(0, 8, doc_type_label.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*DARK_BROWN)
        self.set_x(20)
        self.multi_cell(W, 14, title, align="C")

        if recipient:
            self.ln(6)
            self._hline(self.get_y(), x1=70, x2=140, color=ROSE, lw=0.25)
            self.ln(8)
            self.set_font("Helvetica", size=11)
            self.set_text_color(*DARK_BROWN)
            self.cell(0, 8, f"Para: {recipient}", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_y(-30)
        self._hline(self.get_y())
        self.ln(3)

        altair_email = os.environ.get("ALTAIR_EMAIL", "")
        altair_name = os.environ.get("ALTAIR_NAME", "ALTAIR Academia")
        footer_text = f"{altair_name}  |  {date}"
        if altair_email:
            footer_text += f"  |  {altair_email}"

        self.set_font("Helvetica", size=8)
        self.set_text_color(*BEIGE)
        self.cell(0, 5, footer_text, align="C")

    def content_page(self, content_lines):
        """Renders parsed content lines onto pages."""
        self.add_page()
        self._bg()
        self.set_xy(20, 28)

        for item_type, text in content_lines:
            if self.get_y() > 265:
                self.add_page()
                self._bg()
                self.set_xy(20, 28)

            if item_type == "h2":
                self.ln(4)
                self.set_x(20)
                self.set_font("Helvetica", "B", 14)
                self.set_text_color(*DARK_RED)
                self.multi_cell(W, 8, text)
                self._hline(self.get_y() + 1, color=ROSE, lw=0.2)
                self.ln(5)

            elif item_type == "h3":
                self.ln(3)
                self.set_x(20)
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 7, text)
                self.ln(2)

            elif item_type == "bullet":
                self.set_x(25)
                self.set_font("Helvetica", size=11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W - 5, 6, f"- {text}")
                self.ln(1)

            elif item_type == "para":
                self.set_x(20)
                self.set_font("Helvetica", size=11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 6, text)
                self.ln(4)


def _parse_markdown(content: str) -> list:
    """Parses basic markdown into (type, text) tuples."""
    lines = []
    for line in content.split("\n"):
        line = line.rstrip()
        if line.startswith("## "):
            lines.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            lines.append(("h3", line[4:].strip()))
        elif re.match(r"^[-•*] ", line):
            lines.append(("bullet", line[2:].strip()))
        elif line.strip():
            lines.append(("para", line.strip()))
    return lines


DOC_TYPE_LABELS = {
    "proposal": "Propuesta",
    "summary": "Resumen ejecutivo",
    "quote": "Presupuesto",
}


def generate_pdf(doc_type: str, title: str, content: str,
                 recipient: str = "", date: str = "") -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not date:
        date = datetime.now().strftime("%d/%m/%Y")

    label = DOC_TYPE_LABELS.get(doc_type, "Documento")

    pdf = AltairPDF(doc_type=doc_type)

    # Cover page
    pdf.cover(title, label, recipient, date)

    # Content pages
    parsed = _parse_markdown(content)
    if parsed:
        pdf.content_page(parsed)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:40]
    filename = f"{doc_type}_{safe_title}_{timestamp}.pdf"
    output_path = OUTPUT_DIR / filename

    pdf.output(str(output_path))
    return str(output_path)
