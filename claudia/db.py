import sqlite3
import json
from pathlib import Path
from typing import List, Dict

DB_PATH = Path(__file__).parent.parent / "claudia.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_message(user_id: int, role: str, content):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, json.dumps(content) if isinstance(content, list) else content)
    )
    conn.commit()
    conn.close()


def get_history(user_id: int, limit: int = 20) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    messages = []
    for role, content in reversed(rows):
        try:
            messages.append({"role": role, "content": json.loads(content)})
        except (json.JSONDecodeError, TypeError):
            messages.append({"role": role, "content": content})
    return messages


def clear_history(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_document_record(user_id: int, filename: str, doc_type: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO documents (user_id, filename, doc_type) VALUES (?, ?, ?)",
        (user_id, filename, doc_type)
    )
    conn.commit()
    conn.close()
