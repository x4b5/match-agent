import aiosqlite
import json
import os
from datetime import datetime
from backend.config import ICLOUD_BASE

DB_PATH = os.path.join(ICLOUD_BASE, "matchflix.db")

async def init_db():
    """Initialiseer de database tabellen asynchroon."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("""
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                document_id TEXT PRIMARY KEY,
                doc_type TEXT,
                naam TEXT,
                vector_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexen voor sneller zoeken
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_kandidaat ON matches(kandidaat_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_vacature ON matches(vacature_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_embed_type ON embeddings(doc_type)")
        await conn.commit()

async def bewaar_match(kandidaat_naam, kandidaat_id, vacature_titel, vacature_id, percentage, modus, resultaat_dict):
    """Sla een match resultaat op in de database."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
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
        await conn.commit()

async def haal_laatste_matches(limit=50):
    """Haal de meest recente matches op."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM matches ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def haal_matches_voor_vacature(vacature_id):
    """Haal alle matches op voor een specifieke vacature UUID, gesorteerd op percentage."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT * FROM matches 
            WHERE vacature_id = ? 
            ORDER BY match_percentage DESC, timestamp DESC
        """, (vacature_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def haal_unieke_vacatures():
    """Haal lijst van unieke vacatures waarvoor gematcht is."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT DISTINCT vacature_titel FROM matches ORDER BY vacature_titel")
        rows = await cursor.fetchall()
        return [row["vacature_titel"] for row in rows]

async def bewaar_embedding(document_id, doc_type, naam, vector):
    """Sla een embedding vector (list van floats) op in de database."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            INSERT OR REPLACE INTO embeddings (document_id, doc_type, naam, vector_json)
            VALUES (?, ?, ?, ?)
        """, (document_id, doc_type, naam, json.dumps(vector)))
        await conn.commit()

async def haal_alle_embeddings(doc_type):
    """Haal alle embeddings op van een specifiek type (bijv. 'kandidaat')."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT document_id, naam, vector_json FROM embeddings WHERE doc_type = ?", (doc_type,))
        res = []
        rows = await cursor.fetchall()
        for row in rows:
            res.append({
                "document_id": row["document_id"],
                "naam": row["naam"],
                "vector": json.loads(row["vector_json"])
            })
        return res
