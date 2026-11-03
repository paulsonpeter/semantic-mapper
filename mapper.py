"""Explicit phrase mappings backed by a local SQLite database."""
import csv
import io
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "semantic_mapper.db"
FIELDS = ["phrase", "concept", "detail"]
EXAMPLES = [
    ("sound from wheel", "WHEEL_NOISE", ""),
    ("rattling from tyre", "WHEEL_NOISE", "RATTLING"),
    ("whoosh from tyre", "WHEEL_NOISE", "WHOOSHING"),
    ("noise from wheel", "WHEEL_NOISE", ""),
    ("thud from wheel", "WHEEL_NOISE", "THUDDING"),
    ("engine shaking", "ENGINE_VIBRATION", "SHAKING"),
    ("motor vibrating", "ENGINE_VIBRATION", "VIBRATING"),
    ("gear shifting jerk", "TRANSMISSION_SHOCK", "JERKING"),
]


def normalize(phrase):
    text = unicodedata.normalize("NFKC", phrase).casefold()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return " ".join(text.split())


def label(value):
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value) or value == "UNMAPPED":
        raise ValueError("Use labels such as WHEEL_NOISE: letters, numbers and underscores; UNMAPPED is reserved.")
    return value


@contextmanager
def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(path=DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS concepts (name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS mappings (
            id INTEGER PRIMARY KEY,
            phrase TEXT NOT NULL,
            normalized TEXT NOT NULL UNIQUE,
            concept TEXT NOT NULL REFERENCES concepts(name),
            detail TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """)
        if not conn.execute("SELECT 1 FROM settings WHERE key='seeded'").fetchone():
            for phrase, concept, detail in EXAMPLES:
                conn.execute("INSERT OR IGNORE INTO concepts VALUES (?)", (concept,))
                conn.execute("INSERT OR IGNORE INTO mappings (phrase,normalized,concept,detail) VALUES (?,?,?,?)",
                             (phrase, normalize(phrase), concept, detail))
            conn.execute("INSERT INTO settings VALUES ('seeded','1')")


def concepts(path=DB_PATH):
    with connect(path) as conn:
        return [r[0] for r in conn.execute("SELECT name FROM concepts ORDER BY name")]


def add_concept(name, path=DB_PATH):
    with connect(path) as conn:
        conn.execute("INSERT INTO concepts VALUES (?)", (label(name),))


def delete_concept(name, path=DB_PATH):
    with connect(path) as conn:
        if conn.execute("SELECT 1 FROM mappings WHERE concept=?", (name,)).fetchone():
            raise ValueError("Remove or reassign this concept's mappings first.")
        conn.execute("DELETE FROM concepts WHERE name=?", (name,))


def mappings(path=DB_PATH):
    with connect(path) as conn:
        return [dict(r) for r in conn.execute("SELECT id,phrase,concept,detail FROM mappings ORDER BY concept,phrase")]


def save_mapping(phrase, concept, detail="", mapping_id=None, path=DB_PATH):
    if not normalize(phrase):
        raise ValueError("Enter a phrase containing more than spaces or punctuation.")
    concept = label(concept)
    detail = label(detail) if detail.strip() else ""
    with connect(path) as conn:
        values = (phrase.strip(), normalize(phrase), concept, detail)
        if mapping_id is None:
            conn.execute("INSERT INTO mappings (phrase,normalized,concept,detail) VALUES (?,?,?,?)", values)
        else:
            conn.execute("UPDATE mappings SET phrase=?,normalized=?,concept=?,detail=? WHERE id=?", (*values, mapping_id))


def delete_mapping(mapping_id, path=DB_PATH):
    with connect(path) as conn:
        conn.execute("DELETE FROM mappings WHERE id=?", (mapping_id,))


def match(phrases, path=DB_PATH):
    with connect(path) as conn:
        results = []
        for phrase in phrases:
            row = conn.execute("SELECT concept,detail FROM mappings WHERE normalized=?", (normalize(phrase),)).fetchone()
            results.append({"phrase": phrase, "concept": row[0] if row else "UNMAPPED",
                            "detail": row[1] if row else "", "status": "Matched" if row else "Unmapped"})
        return results


def export_csv(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def import_csv(content, path=DB_PATH):
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if reader.fieldnames != FIELDS:
        raise ValueError("CSV headers must be exactly: phrase,concept,detail")
    rows = []
    seen = set()
    for line, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Row {line}: expected three columns.")
        phrase = row["phrase"].strip()
        normalized = normalize(phrase)
        if not normalized:
            raise ValueError(f"Row {line}: phrase is empty.")
        if normalized in seen:
            raise ValueError(f"Row {line}: duplicate phrase after normalization.")
        seen.add(normalized)
        rows.append((phrase, normalized, label(row["concept"]), label(row["detail"]) if row["detail"].strip() else ""))
    # One transaction: any conflict rolls back the entire import.
    with connect(path) as conn:
        count = 0
        for phrase, normalized, concept, detail in rows:
            existing = conn.execute("SELECT concept,detail FROM mappings WHERE normalized=?", (normalized,)).fetchone()
            if existing:
                if tuple(existing) != (concept, detail):
                    raise ValueError(f"Conflicting mapping for '{phrase}'. Edit the existing mapping first.")
                continue
            conn.execute("INSERT OR IGNORE INTO concepts VALUES (?)", (concept,))
            conn.execute("INSERT INTO mappings (phrase,normalized,concept,detail) VALUES (?,?,?,?)",
                         (phrase, normalized, concept, detail))
            count += 1
    return count
