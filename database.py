import sqlite3
import json
import os
from datetime import datetime
from config import ICLOUD_BASE

DB_PATH = os.path.join(ICLOUD_BASE, "paperstrip.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialiseer de database tabellen."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                kandidaat_naam TEXT,
                kandidaat_id TEXT,
                vacature_titel TEXT,
                vacature_id TEXT,
                match_percentage INTEGER,
                modus TEXT,
                resultaat_json TEXT
            )
        """)
        # Indexen voor sneller zoeken
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kandidaat ON matches(kandidaat_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vacature ON matches(vacature_id)")
        conn.commit()

def bewaar_match(kandidaat_naam, kandidaat_id, vacature_titel, vacature_id, percentage, modus, resultaat_dict):
    """Sla een match resultaat op in de database."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO matches (kandidaat_naam, kandidaat_id, vacature_titel, vacature_id, match_percentage, modus, resultaat_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            kandidaat_naam, 
            kandidaat_id, 
            vacature_titel, 
            vacature_id, 
            percentage, 
            modus, 
            json.dumps(resultaat_dict, ensure_ascii=False)
        ))
        conn.commit()

def haal_laatste_matches(limit=50):
    """Haal de meest recente matches op."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM matches ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def haal_matches_voor_vacature(vacature_titel):
    """Haal alle matches op voor een specifieke vacature, gesorteerd op percentage."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM matches 
            WHERE vacature_titel = ? 
            ORDER BY match_percentage DESC, timestamp DESC
        """, (vacature_titel,))
        return [dict(row) for row in cursor.fetchall()]

def haal_unieke_vacatures():
    """Haal lijst van unieke vacatures waarvoor gematcht is."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT DISTINCT vacature_titel FROM matches ORDER BY vacature_titel")
        return [row["vacature_titel"] for row in cursor.fetchall()]

# Initialiseer bij import
if not os.path.exists(DB_PATH):
    init_db()
