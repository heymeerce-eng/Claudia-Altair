import os
import requests

MIRO_BASE = "https://api.miro.com/v2"


def _headers() -> dict:
    token = os.environ.get("MIRO_API_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_board(name: str, description: str = "") -> str:
    """Creates a Miro board and returns its ID and view URL."""
    resp = requests.post(
        f"{MIRO_BASE}/boards",
        headers=_headers(),
        json={"name": name, "description": description},
    )
    if resp.status_code not in (200, 201):
        return f"Error creando tablero: {resp.status_code} — {resp.text}"
    data = resp.json()
    board_id = data.get("id", "")
    view_link = data.get("viewLink", "")
    return f"Tablero creado.\nID: {board_id}\nURL: {view_link}"


def add_sticky_notes(board_id: str, sections: dict) -> str:
    """
    Creates sticky notes organized in vertical columns, one per section.
    sections: {"Nombre sección": ["texto 1", "texto 2", ...], ...}
    """
    SECTION_WIDTH = 700
    STICKY_SIZE = 200
    PADDING = 60
    FRAME_PADDING_TOP = 180

    x_offset = 0
    created = 0
    errors = []

    for section_title, items in sections.items():
        frame_height = FRAME_PADDING_TOP + len(items) * (STICKY_SIZE + PADDING) + PADDING
        frame_payload = {
            "data": {"title": section_title, "type": "freeform"},
            "geometry": {"height": frame_height, "width": SECTION_WIDTH},
            "position": {"x": x_offset, "y": 0, "origin": "center"},
        }
        requests.post(
            f"{MIRO_BASE}/boards/{board_id}/frames",
            headers=_headers(),
            json=frame_payload,
        )

        y_pos = -(frame_height // 2) + FRAME_PADDING_TOP
        for item in items:
            sticky_payload = {
                "data": {"content": item, "shape": "square"},
                "style": {"fillColor": "light_yellow"},
                "geometry": {"width": STICKY_SIZE},
                "position": {"x": x_offset, "y": y_pos, "origin": "center"},
            }
            r = requests.post(
                f"{MIRO_BASE}/boards/{board_id}/sticky_notes",
                headers=_headers(),
                json=sticky_payload,
            )
            if r.status_code in (200, 201):
                created += 1
            else:
                errors.append(f"'{item[:25]}': {r.status_code}")
            y_pos += STICKY_SIZE + PADDING

        x_offset += SECTION_WIDTH + PADDING

    result = f"Tablero actualizado: {created} post-its creados en {len(sections)} secciones."
    if errors:
        result += f"\nErrores: {'; '.join(errors[:3])}"
    return result
