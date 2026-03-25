"""
SQLite database initialization and access for MediOrbit.

Creates the three core tables on first run and seeds them with Tamil Nadu hospital data.
All query helpers return plain Python dicts so callers can construct Pydantic models
from them without coupling this module to any schema import cycle.
"""

import csv
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "hospitals.db"
CSV_PATH = Path(__file__).parent.parent / "data" / "hospitals.csv"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables and seed data if they do not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        _create_tables(conn)
        _seed_if_empty(conn)
        conn.commit()
    finally:
        conn.close()


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            city            TEXT,
            state           TEXT DEFAULT 'Tamil Nadu',
            specialties     TEXT DEFAULT '[]',
            procedures      TEXT DEFAULT '[]',
            min_price       INTEGER DEFAULT 0,
            max_price       INTEGER DEFAULT 0,
            ai_score        REAL DEFAULT 0.0,
            insurance       TEXT DEFAULT '[]',
            accreditations  TEXT DEFAULT '[]',
            phone           TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            image_url       TEXT DEFAULT '',
            lat             REAL DEFAULT 0.0,
            lng             REAL DEFAULT 0.0,
            success_rate    REAL DEFAULT 0.0,
            timeline_days   INTEGER DEFAULT 0,
            doctor_count    INTEGER DEFAULT 0,
            review_count    INTEGER DEFAULT 0,
            avg_rating      REAL DEFAULT 0.0,
            doctors         TEXT DEFAULT '[]',
            reviews         TEXT DEFAULT '[]',
            cost_breakdown  TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT CHECK(role IN ('user', 'assistant')),
            content     TEXT,
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);

        CREATE TABLE IF NOT EXISTS extractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            diagnosis       TEXT DEFAULT '[]',
            procedure       TEXT DEFAULT '[]',
            medications     TEXT DEFAULT '[]',
            patient_age     INTEGER,
            patient_gender  TEXT,
            raw_text        TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_ext_session ON extractions(session_id);
    """)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Seed hospitals from CSV file if table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0]
    if count > 0:
        return
    
    # Try to read from CSV if it exists
    if CSV_PATH.exists():
        _seed_from_csv(conn)
    else:
        # Fallback: seed with empty table (hospitals can be added manually)
        print(f"Warning: CSV file not found at {CSV_PATH}. Hospital table seeded but empty.")


def _seed_from_csv(conn: sqlite3.Connection) -> None:
    """Read hospitals from CSV and populate the database."""
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse comma-separated fields into lists
                specialties = [s.strip() for s in row.get('specialties', '').split(',') if s.strip()]
                procedures = [p.strip() for p in row.get('procedures', '').split(',') if p.strip()]
                insurance = [i.strip() for i in row.get('insurance_schemes', '').split(',') if i.strip()]
                
                # Convert price fields to integers
                try:
                    min_price = int(row.get('min_price', 0))
                    max_price = int(row.get('max_price', 0))
                except (ValueError, TypeError):
                    min_price, max_price = 0, 0
                
                # Convert success rate to float
                try:
                    success_rate = float(row.get('success_rate', 0))
                except (ValueError, TypeError):
                    success_rate = 0.0
                
                # Convert coordinates
                try:
                    lat = float(row.get('lat', 0.0))
                    lng = float(row.get('lng', 0.0))
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0
                
                # Insert hospital record
                conn.execute("""
                    INSERT OR IGNORE INTO hospitals
                        (id, name, city, state, specialties, procedures, min_price, max_price,
                         ai_score, insurance, accreditations, phone, email,
                         lat, lng, success_rate, doctor_count)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    row.get('id'),
                    row.get('name'),
                    row.get('city'),
                    row.get('state', 'Tamil Nadu'),
                    json.dumps(specialties),
                    json.dumps(procedures),
                    min_price,
                    max_price,
                    85.0,  # Default AI score
                    json.dumps(insurance),
                    json.dumps([row.get('nabh_accredited', 'No')]) if row.get('nabh_accredited') == 'Yes' else json.dumps([]),
                    row.get('phone', ''),
                    row.get('email', ''),
                    lat,
                    lng,
                    success_rate,
                    10,  # Default doctor count
                ))
        conn.commit()
        hospital_count = conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0]
        print(f"Successfully seeded {hospital_count} hospitals from CSV")
    except Exception as e:
        print(f"Error seeding hospitals from CSV: {e}")
        raise


def get_available_cities() -> list[str]:
    """Query and return all distinct cities from hospitals table."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT city FROM hospitals WHERE city IS NOT NULL ORDER BY city"
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def query_hospitals_by_specialty(specialty: str) -> list[dict]:
    """Query hospitals that offer a specific specialty or procedure."""
    conn = get_connection()
    try:
        # Search in both specialties and procedures JSON fields
        rows = conn.execute("""
            SELECT * FROM hospitals 
            WHERE specialties LIKE ? OR procedures LIKE ?
            ORDER BY success_rate DESC, avg_rating DESC
        """, (f'%{specialty}%', f'%{specialty}%')).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()



def row_to_dict(row: sqlite3.Row) -> dict:
    """
    Convert a sqlite3.Row to a plain dict, parsing any JSON string columns.

    Args:
        row: A sqlite3.Row returned by a query.

    Returns:
        A dict with JSON columns already parsed into Python objects.
    """
    d = dict(row)
    json_cols = {"specialties", "procedures", "insurance", "accreditations",
                 "doctors", "reviews", "cost_breakdown"}
    for col in json_cols:
        if col in d and isinstance(d[col], str):
            try:
                d[col] = json.loads(d[col])
            except (json.JSONDecodeError, TypeError):
                d[col] = []
    return d


def save_conversation_turn(session_id: str, role: str, content: str) -> None:
    """
    Persist one conversation turn to the conversations table.

    Args:
        session_id: Unique identifier for the chat session.
        role: Either 'user' or 'assistant'.
        content: The message text.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()
    finally:
        conn.close()


def get_conversation_history(session_id: str, limit: int = 20) -> list[dict]:
    """
    Retrieve the most recent conversation turns for a session.

    Args:
        session_id: The chat session identifier.
        limit: Maximum number of messages to return (most recent first).

    Returns:
        List of dicts with keys: role, content (in chronological order).
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT role, content FROM conversations
               WHERE session_id = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


def save_extraction(session_id: str, extraction: dict) -> None:
    """
    Persist a prescription extraction result to the extractions table.

    Args:
        session_id: The chat session identifier.
        extraction: Dict matching ExtractionResult fields.
    """
    conn = get_connection()
    try:
        patient = extraction.get("patient", {})
        conn.execute(
            """INSERT INTO extractions
               (session_id, diagnosis, procedure, medications, patient_age, patient_gender, raw_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                json.dumps(extraction.get("diagnosis", [])),
                json.dumps(extraction.get("procedure", [])),
                json.dumps(extraction.get("medications", [])),
                patient.get("age") if isinstance(patient, dict) else None,
                patient.get("gender") if isinstance(patient, dict) else None,
                extraction.get("raw_text", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_extraction(session_id: str) -> dict | None:
    """
    Return the most recent prescription extraction for a session, or None.

    Args:
        session_id: The chat session identifier.

    Returns:
        Dict with diagnosis, procedure, medications, patient_age, patient_gender or None.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM extractions WHERE session_id = ?
               ORDER BY id DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for col in ("diagnosis", "procedure", "medications"):
            if isinstance(d.get(col), str):
                try:
                    d[col] = json.loads(d[col])
                except (json.JSONDecodeError, TypeError):
                    d[col] = []
        return d
    finally:
        conn.close()
