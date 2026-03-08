import aiosqlite
import json
import os
import math
from datetime import datetime
from backend.config import ICLOUD_BASE

DB_PATH = os.path.join(ICLOUD_BASE, "matchflix.db")

async def init_db():
    """Initialiseer de database tabellen asynchroon."""
    os.makedirs(ICLOUD_BASE, exist_ok=True)
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
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documenten (
                document_id TEXT PRIMARY KEY,
                doc_type TEXT,
                naam TEXT,
                ruwe_tekst TEXT,
                profiel_json TEXT,
                waarschuwingen TEXT,
                profiel_compleet BOOLEAN,
                verrijkings_antwoorden TEXT,
                versie INTEGER DEFAULT 1,
                vorige_profiel_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexen voor sneller zoeken
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_kandidaat ON matches(kandidaat_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_vacature ON matches(vacature_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_embed_type ON embeddings(doc_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON documenten(doc_type)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_naam ON documenten(naam, doc_type)")
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

def bereken_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Bereken de cosine similarity tussen twee vectoren."""
    if len(vec1) != len(vec2) or not vec1 or not vec2:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

async def haal_top_matches_vector(vacature_vector: list[float], limit: int = 5) -> list[dict]:
    """Haal de top kandidaat matches op puur gebaseerd op vector similarity."""
    kandidaten = await haal_alle_embeddings("kandidaat")
    
    scored_kandidaten = []
    for kandidaat in kandidaten:
        score = bereken_cosine_similarity(vacature_vector, kandidaat["vector"])
        scored_kandidaten.append({
            "document_id": kandidaat["document_id"],
            "naam": kandidaat["naam"],
            "score": score,
            # scale similarity score roughly to a 0-100 percentage
            "percentage": max(0, min(100, int(score * 100))) 
        })
        
    # Sort by score descending
    scored_kandidaten.sort(key=lambda x: x["score"], reverse=True)
    return scored_kandidaten[:limit]

async def haal_top_vacatures_vector(kandidaat_vector: list[float], limit: int = 5) -> list[dict]:
    """Reverse matching: haal de top vacatures op voor een gegeven kandidaat-vector."""
    vacatures = await haal_alle_embeddings("vacature")
    
    scored = []
    for vac in vacatures:
        score = bereken_cosine_similarity(kandidaat_vector, vac["vector"])
        scored.append({
            "document_id": vac["document_id"],
            "naam": vac["naam"],
            "score": score,
            "percentage": max(0, min(100, int(score * 100)))
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]

async def bewaar_document(document_id: str, doc_type: str, naam: str, ruwe_tekst: str, profiel_dict: dict, waarschuwingen: list):
    """Sla een geëxtraheerd profiel en ruwe tekst op in de database."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            INSERT OR REPLACE INTO documenten (document_id, doc_type, naam, ruwe_tekst, profiel_json, waarschuwingen, profiel_compleet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id, 
            doc_type, 
            naam, 
            ruwe_tekst, 
            json.dumps(profiel_dict, ensure_ascii=False) if profiel_dict else None,
            json.dumps(waarschuwingen, ensure_ascii=False) if waarschuwingen else None,
            True if profiel_dict else False
        ))
        await conn.commit()

async def haal_document(identifier: str) -> dict | None:
    """Haal een document op basis van UUID of Directory Naam."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        # Weak match on either UUID or the directory name (which is unique enough for now)
        cursor = await conn.execute("""
            SELECT * FROM documenten 
            WHERE document_id = ? OR naam = ?
            LIMIT 1
        """, (identifier, identifier))
        
        row = await cursor.fetchone()
        if not row:
            return None
            
        doc = dict(row)
        if doc.get("profiel_json"):
            doc["profiel_dict"] = json.loads(doc["profiel_json"])
        else:
            doc["profiel_dict"] = None
            
        if doc.get("waarschuwingen"):
            doc["waarschuwingen_list"] = json.loads(doc["waarschuwingen"])
        else:
            doc["waarschuwingen_list"] = []
            
        return doc

async def haal_alle_documenten(doc_type: str) -> list[dict]:
    """Haal alle documenten van een specifiek type op."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM documenten WHERE doc_type = ? ORDER BY timestamp DESC", (doc_type,))
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            doc = dict(row)
            if doc.get("profiel_json"):
                doc["profiel_dict"] = json.loads(doc["profiel_json"])
            else:
                doc["profiel_dict"] = None
            result.append(doc)
            
        return result

async def haal_cached_match(kandidaat_naam: str, vacature_naam: str, modus: str) -> dict | None:
    """Check of er al een match-resultaat bestaat voor deze combinatie.
    Geeft None terug als er geen cache is of als het profiel nieuwer is dan de match."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT m.*, d.timestamp as profiel_timestamp
            FROM matches m
            LEFT JOIN documenten d ON d.naam = m.kandidaat_naam
            WHERE m.kandidaat_naam = ? AND m.vacature_titel = ? AND m.modus = ?
            ORDER BY m.timestamp DESC
            LIMIT 1
        """, (kandidaat_naam, vacature_naam, modus))
        row = await cursor.fetchone()
        if not row:
            return None

        match = dict(row)
        # Invalideer cache als profiel nieuwer is dan de match
        if match.get("profiel_timestamp") and match.get("timestamp"):
            if match["profiel_timestamp"] > match["timestamp"]:
                return None

        if match.get("resultaat_json"):
            match["resultaat_dict"] = json.loads(match["resultaat_json"])
        return match


async def verwijder_alle_data(document_id: str) -> dict:
    """
    GDPR 'Vergeet Mij' – verwijdert ALLE data voor een specifiek document UUID.
    Wist uit: documenten, embeddings, en matches tabellen.
    Retourneert een rapport van wat verwijderd is.
    """
    rapport = {"documenten": 0, "embeddings": 0, "matches": 0}
    
    async with aiosqlite.connect(DB_PATH) as conn:
        # Verwijder uit documenten
        cursor = await conn.execute("DELETE FROM documenten WHERE document_id = ?", (document_id,))
        rapport["documenten"] = cursor.rowcount
        
        # Verwijder embedding
        cursor = await conn.execute("DELETE FROM embeddings WHERE document_id = ?", (document_id,))
        rapport["embeddings"] = cursor.rowcount
        
        # Verwijder uit matches (zowel als kandidaat als als vacature)
        cursor = await conn.execute("DELETE FROM matches WHERE kandidaat_id = ? OR vacature_id = ?", (document_id, document_id))
        rapport["matches"] = cursor.rowcount
        
        await conn.commit()
    
    return rapport

async def bewaar_verrijking(document_id: str, antwoorden: dict):
    """Sla verrijkings-antwoorden op bij een bestaand document."""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Haal bestaande antwoorden op
        cursor = await conn.execute("SELECT verrijkings_antwoorden FROM documenten WHERE document_id = ?", (document_id,))
        row = await cursor.fetchone()
        
        bestaande = {}
        if row and row[0]:
            bestaande = json.loads(row[0])
        
        # Merge nieuwe antwoorden
        bestaande.update(antwoorden)
        
        await conn.execute(
            "UPDATE documenten SET verrijkings_antwoorden = ? WHERE document_id = ?",
            (json.dumps(bestaande, ensure_ascii=False), document_id)
        )
        await conn.commit()

async def update_profiel_na_verrijking(document_id: str, nieuw_profiel: dict):
    """Update het profiel na verrijking. Bewaart de vorige versie voor delta tracking."""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Haal huidige staat op
        cursor = await conn.execute(
            "SELECT profiel_json, versie FROM documenten WHERE document_id = ?", 
            (document_id,)
        )
        row = await cursor.fetchone()
        
        vorig_profiel = row[0] if row else None
        huidige_versie = row[1] if row and row[1] else 1
        
        # Update met nieuw profiel, sla vorige versie op
        await conn.execute("""
            UPDATE documenten 
            SET profiel_json = ?, 
                vorige_profiel_json = ?,
                versie = ?,
                profiel_compleet = 1,
                timestamp = CURRENT_TIMESTAMP
            WHERE document_id = ?
        """, (
            json.dumps(nieuw_profiel, ensure_ascii=False),
            vorig_profiel,
            huidige_versie + 1,
            document_id
        ))
        await conn.commit()
        
        return {"versie": huidige_versie + 1, "vorige_versie": huidige_versie}

