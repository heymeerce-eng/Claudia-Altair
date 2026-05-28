"""
Herramienta de memoria persistente para Claudia.
Lee y escribe en memoria.md, organizado por socia.
"""
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path(__file__).parent.parent.parent / "memoria.md"


def read_memory() -> str:
    """Reads the full memory file."""
    if not MEMORY_FILE.exists():
        return "No hay memoria guardada aún."
    content = MEMORY_FILE.read_text(encoding="utf-8").strip()
    return content if content else "No hay memoria guardada aún."


def save_memory(user_name: str, content: str) -> str:
    """
    Appends a memory entry under the user's section.
    user_name: first name or full name (e.g. "Merce", "Anabel", "Diana")
    content: the information to remember
    """
    if not MEMORY_FILE.exists():
        return "Error: memoria.md no encontrado."

    text = MEMORY_FILE.read_text(encoding="utf-8")
    date_str = datetime.now().strftime("%d/%m/%Y")
    entry = f"- [{date_str}] {content}"

    # Find the user's section (partial match, case-insensitive)
    lines = text.split("\n")
    section_line = None
    for line in lines:
        if line.startswith("## ") and user_name.lower() in line.lower():
            section_line = line
            break

    if section_line:
        idx = text.find(section_line)
        # Find where the next section starts (or end of file)
        rest = text[idx + len(section_line):]
        next_section = rest.find("\n## ")
        if next_section == -1:
            new_text = text.rstrip() + f"\n{entry}\n"
        else:
            insert_at = idx + len(section_line) + next_section
            new_text = text[:insert_at] + f"\n{entry}" + text[insert_at:]
    else:
        # Create new section for this user
        new_text = text.rstrip() + f"\n\n## {user_name}\n{entry}\n"

    MEMORY_FILE.write_text(new_text, encoding="utf-8")
    return f"Guardado en memoria para {user_name}."
