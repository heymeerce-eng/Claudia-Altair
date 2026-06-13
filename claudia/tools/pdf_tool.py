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
GRAY_LIGHT = (240, 237, 232)

W = 166  # usable width (margins 22mm each side)


class AltairPDF(FPDF):
    def __init__(self, doc_type="proposal"):
        super().__init__()
        self.doc_type = doc_type
        self.set_margins(22, 22, 22)
        self.set_auto_page_break(True, margin=25)

    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(*DARK_BROWN)
            self.rect(0, 0, 210, 8, "F")

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self._hline(self.get_y(), color=BEIGE, lw=0.2)
            self.set_y(-12)
            self.set_font("Helvetica", size=7)
            altair_name = os.environ.get("ALTAIR_NAME", "Altair Academy")
            self.set_text_color(*ROSE)
            self.cell(W - 15, 6, f"{altair_name} — Material exclusivo para alumnas", align="L")
            self.set_text_color(*BEIGE)
            self.cell(15, 6, f"Pág. {self.page_no() - 1}", align="R")

    def _bg(self):
        self.set_fill_color(*CREAM)
        self.rect(0, 0, 210, 297, "F")

    def _hline(self, y, x1=22, x2=188, color=DARK_RED, lw=0.4):
        self.set_draw_color(*color)
        self.set_line_width(lw)
        self.line(x1, y, x2, y)

    def cover(self, title, doc_type_label, recipient, date):
        self.add_page()

        # Full dark background
        self.set_fill_color(*DARK_BROWN)
        self.rect(0, 0, 210, 297, "F")

        # Top rule
        self._hline(20, color=BEIGE, lw=0.25)

        # Academy name
        self.set_y(24)
        altair_name = os.environ.get("ALTAIR_NAME", "Altair Academy")
        self.set_font("Helvetica", size=7.5)
        self.set_text_color(*BEIGE)
        self.cell(0, 5, altair_name.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        # Center section — doc type label
        self.set_y(92)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*ROSE)
        self.cell(0, 5, doc_type_label.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        # Short rule before title
        self.ln(5)
        self._hline(self.get_y(), x1=80, x2=130, color=ROSE, lw=0.2)
        self.ln(11)

        # Main title
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*CREAM)
        self.set_x(22)
        self.multi_cell(W, 13, title, align="C")

        # Short rule after title
        self.ln(8)
        self._hline(self.get_y(), x1=80, x2=130, color=ROSE, lw=0.2)

        # Recipient
        if recipient:
            self.ln(12)
            self.set_font("Helvetica", size=11)
            self.set_text_color(*BEIGE)
            self.cell(0, 7, f"Para: {recipient}", align="C", new_x="LMARGIN", new_y="NEXT")

        # Cover bottom footer
        self.set_y(-46)
        self._hline(self.get_y(), color=BEIGE, lw=0.25)
        self.ln(7)

        footer_main = f"{altair_name} — Material exclusivo para alumnas"
        self.set_font("Helvetica", size=8)
        self.set_text_color(*BEIGE)
        self.cell(0, 5, footer_main, align="C", new_x="LMARGIN", new_y="NEXT")

        details = []
        if date:
            details.append(date)
        altair_email = os.environ.get("ALTAIR_EMAIL", "")
        if altair_email:
            details.append(altair_email)
        if details:
            self.set_font("Helvetica", size=7)
            self.set_text_color(*ROSE)
            self.cell(0, 5, "  ·  ".join(details), align="C")

    def _callout_box(self, text):
        """Wine-colored box with cream italic text for key quotes/principles."""
        pad_x = 7
        pad_y = 5
        box_x = 22
        box_w = W
        line_h = 7

        self.set_font("Helvetica", "BI", 11)
        words = text.split()
        current = ""
        num_lines = 1
        for word in words:
            test = (current + " " + word).strip()
            if self.get_string_width(test) > (box_w - 2 * pad_x):
                num_lines += 1
                current = word
            else:
                current = test
        box_h = num_lines * line_h + 2 * pad_y + 2

        start_y = self.get_y() + 5
        if start_y + box_h > 265:
            self.add_page()
            self._bg()
            self.set_xy(22, 18)
            start_y = self.get_y() + 5

        self.set_fill_color(*DARK_RED)
        self.set_draw_color(*DARK_RED)
        self.rect(box_x, start_y, box_w, box_h, "F")

        self.set_xy(box_x + pad_x, start_y + pad_y)
        self.set_text_color(*CREAM)
        self.multi_cell(box_w - 2 * pad_x, line_h, text, align="C")

        self.set_y(start_y + box_h + 7)
        self.set_x(22)

    def content_page(self, content_lines):
        self.add_page()
        self._bg()
        self.set_xy(22, 18)

        for item_type, text in content_lines:
            if self.get_y() > 262:
                self.add_page()
                self._bg()
                self.set_xy(22, 18)

            if item_type == "h2":
                self.ln(7)
                self.set_x(22)
                self.set_font("Helvetica", "B", 15)
                self.set_text_color(*DARK_RED)
                self.multi_cell(W, 9, text)
                self._hline(self.get_y() + 1, color=ROSE, lw=0.2)
                self.ln(6)

            elif item_type == "h3":
                self.ln(4)
                self.set_x(22)
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 7, text)
                self.ln(3)

            elif item_type == "bullet":
                self.set_x(27)
                self.set_font("Helvetica", size=10.5)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W - 5, 6.5, f"— {text}")
                self.ln(1)

            elif item_type == "para":
                self.set_x(22)
                self.set_font("Helvetica", size=10.5)
                self.set_text_color(*DARK_BROWN)
                self.multi_cell(W, 6.5, text)
                self.ln(4)

            elif item_type == "callout":
                self._callout_box(text)


def _parse_markdown(content: str) -> list:
    lines = []
    for line in content.split("\n"):
        line = line.rstrip()
        if line.startswith("## "):
            lines.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            lines.append(("h3", line[4:].strip()))
        elif re.match(r"^[-•*] ", line):
            lines.append(("bullet", line[2:].strip()))
        elif line.startswith("> "):
            lines.append(("callout", line[2:].strip()))
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
    pdf.cover(title, label, recipient, date)

    parsed = _parse_markdown(content)
    if parsed:
        pdf.content_page(parsed)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:40]
    filename = f"{doc_type}_{safe_title}_{timestamp}.pdf"
    output_path = OUTPUT_DIR / filename

    pdf.output(str(output_path))
    return str(output_path)
