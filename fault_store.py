"""Local storage for user-approved aircraft fault terms."""
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "approved_aircraft_faults.db"


def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS approved_faults (
            id INTEGER PRIMARY KEY,
            paragraph TEXT NOT NULL,
            normalized_term TEXT NOT NULL,
            model TEXT NOT NULL,
            approved_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            UNIQUE(paragraph, normalized_term)
        )""")


def approve(paragraph, term, model):
    if not all(isinstance(value, str) and value.strip() for value in (paragraph, term, model)):
        raise ValueError("A paragraph, fault term and model are required before saving.")
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO approved_faults (paragraph, normalized_term, model) VALUES (?, ?, ?)",
            (paragraph.strip(), term.strip(), model.strip()))
        return cursor.rowcount == 1


def records():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM approved_faults ORDER BY id DESC")]
