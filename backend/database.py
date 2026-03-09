import aiosqlite
import json
import os
import math
import logging
from datetime import datetime
from backend.config import ICLOUD_BASE, DB_PATH

logger = logging.getLogger("matchflix.db")


async def _get_connection() -> aiosqlite.Connection:
    """Maak een geconfigureerde database-connectie met WAL-modus en row_factory."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=5000")
    return conn


async def init_db():
    """Initialiseer de database tabellen asynchroon."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(ICLOUD_BASE, exist_ok=True)
    
    if "Mobile Documents" in DB_PATH:
        print("\033[93mWAARSCHUWING: Database pad bevat 'Mobile Documents'. Dit kan leiden tot corruptie in iCloud!\033[0m", flush=True)
        logger.warning("Database pad bevat 'Mobile Documents'. Dit kan leiden tot corruptie in iCloud!")
        
    conn = await _get_connection()
    try:
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
                model_versie TEXT,
                duur_ms INTEGER,
                resultaat_json TEXT,
                temperature REAL,
                feedback_tekst TEXT,
                feedback_verwerkt BOOLEAN DEFAULT 0
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                document_id TEXT PRIMARY KEY,
                doc_type TEXT,
                naam TEXT,
                vector_json TEXT,
                vector_skills_json TEXT,
                vector_cultuur_json TEXT,
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
                content_hash TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS taken (
                id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                type TEXT,
                naam TEXT,
                progress TEXT,
                progress_percent INTEGER DEFAULT 0,
                error TEXT,
                started_at REAL,
                updated_at REAL
            )
        """)
        
        # Indexen voor sneller zoeken
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_kandidaat ON matches(kandidaat_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_vacature ON matches(vacature_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_embed_type ON embeddings(doc_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON documenten(doc_type)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_naam ON documenten(naam, doc_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_taken_status ON taken(status)")
        
        # Migreer bestaande tabellen: voeg nieuwe kolommen toe als ze ontbreken
        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN model_versie TEXT")
        except Exception:
            pass  # Kolom bestaat al
        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN duur_ms INTEGER")
        except Exception:
            pass  # Kolom bestaat al
        
        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN temperature REAL")
        except Exception:
            pass  # Kolom bestaat al
        
        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN feedback_verwerkt BOOLEAN DEFAULT 0")
        except Exception:
            pass  # Kolom bestaat al
        
        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN feedback_tekst TEXT")
        except Exception:
            pass  # Kolom bestaat al
        
        try:
            await conn.execute("ALTER TABLE documenten ADD COLUMN content_hash TEXT")
        except Exception:
            pass  # Kolom bestaat al
            
        try:
            await conn.execute("ALTER TABLE embeddings ADD COLUMN vector_skills_json TEXT")
        except Exception:
            pass  # Kolom bestaat al

        try:
            await conn.execute("ALTER TABLE embeddings ADD COLUMN vector_cultuur_json TEXT")
        except Exception:
            pass  # Kolom bestaat al
        
        await conn.commit()
        logger.info(f"Database geïnitialiseerd: {DB_PATH} (WAL modus)")
    finally:
        await conn.close()


# ── Matches ──

async def bewaar_match(kandidaat_naam, kandidaat_id, vacature_titel, vacature_id, percentage, modus, resultaat_dict, model_versie=None, duur_ms=None, temperature=None):
    """Sla een match resultaat op in de database."""
    conn = await _get_connection()
    try:
        await conn.execute("""
            INSERT INTO matches (kandidaat_naam, kandidaat_id, vacature_titel, vacature_id, match_percentage, modus, model_versie, duur_ms, resultaat_json, temperature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kandidaat_naam, 
            kandidaat_id, 
            vacature_titel, 
            vacature_id, 
            percentage, 
            modus, 
            model_versie,
            duur_ms,
            json.dumps(resultaat_dict, ensure_ascii=False),
            temperature
        ))
        await conn.commit()
    finally:
        await conn.close()
async def bewaar_match_feedback(match_id: int, feedback: str):
    """Sla feedback op voor een specifieke match."""
    conn = await _get_connection()
    try:
        await conn.execute(
            "UPDATE matches SET feedback_tekst = ?, feedback_verwerkt = 0 WHERE id = ?",
            (feedback, match_id)
        )
        await conn.commit()
    finally:
        await conn.close()

async def haal_laatste_matches(limit=50):
    """Haal de meest recente matches op."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM matches ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def haal_matches_voor_vacature(vacature_id):
    """Haal alle matches op voor een specifieke vacature UUID, gesorteerd op percentage."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("""
            SELECT * FROM matches 
            WHERE vacature_id = ? 
            ORDER BY match_percentage DESC, timestamp DESC
        """, (vacature_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def haal_unieke_vacatures():
    """Haal lijst van unieke vacatures waarvoor gematcht is."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT DISTINCT vacature_titel FROM matches ORDER BY vacature_titel")
        rows = await cursor.fetchall()
        return [row["vacature_titel"] for row in rows]
    finally:
        await conn.close()


# ── Embeddings ──

async def bewaar_embedding(document_id, doc_type, naam, vector, vector_skills=None, vector_cultuur=None):
    """Sla embedding vectoren op (basis, plus optioneel skills en cultuur dimensies)."""
    conn = await _get_connection()
    try:
        await conn.execute("""
            INSERT OR REPLACE INTO embeddings (document_id, doc_type, naam, vector_json, vector_skills_json, vector_cultuur_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            document_id, 
            doc_type, 
            naam, 
            json.dumps(vector) if vector else None, 
            json.dumps(vector_skills) if vector_skills else None,
            json.dumps(vector_cultuur) if vector_cultuur else None
        ))
        await conn.commit()
    finally:
        await conn.close()

async def haal_alle_embeddings(doc_type):
    """Haal alle embeddings op van een specifiek type inclusief sub-dimensies."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT document_id, naam, vector_json, vector_skills_json, vector_cultuur_json FROM embeddings WHERE doc_type = ?", (doc_type,))
        res = []
        rows = await cursor.fetchall()
        for row in rows:
            res.append({
                "document_id": row["document_id"],
                "naam": row["naam"],
                "vector": json.loads(row["vector_json"]) if row["vector_json"] else None,
                "vector_skills": json.loads(row["vector_skills_json"]) if row["vector_skills_json"] else None,
                "vector_cultuur": json.loads(row["vector_cultuur_json"]) if row["vector_cultuur_json"] else None
            })
        return res
    finally:
        await conn.close()


# ── Vector Similarity ──

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

async def haal_top_matches_vector(
    vacature_vector: list[float] = None, 
    vacature_skills: list[float] = None, 
    vacature_cultuur: list[float] = None,
    limit: int = 5
) -> list[dict]:
    """Haal de top kandidaat matches op via multi-dimensional vector similarity."""
    kandidaten = await haal_alle_embeddings("kandidaat")
    
    scored_kandidaten = []
    for kandidaat in kandidaten:
        # Algemene score
        score_algemeen = 0.0
        if vacature_vector and kandidaat["vector"]:
            score_algemeen = bereken_cosine_similarity(vacature_vector, kandidaat["vector"])
            
        # Skills score
        score_skills = 0.0
        if vacature_skills and kandidaat["vector_skills"]:
            score_skills = bereken_cosine_similarity(vacature_skills, kandidaat["vector_skills"])
            
        # Cultuur score
        score_cultuur = 0.0
        if vacature_cultuur and kandidaat["vector_cultuur"]:
            score_cultuur = bereken_cosine_similarity(vacature_cultuur, kandidaat["vector_cultuur"])

        # Weeg de scores. Als we geen sub-dimensies hebben, gebruik we puur de algemene
        if vacature_skills and vacature_cultuur and kandidaat["vector_skills"] and kandidaat["vector_cultuur"]:
            # Combine score: 40% Skills, 40% Cultuur, 20% Algemeen (afhankelijk van wat relevant is)
            combined_score = (score_skills * 0.4) + (score_cultuur * 0.4) + (score_algemeen * 0.2)
        else:
            combined_score = score_algemeen

        scored_kandidaten.append({
            "document_id": kandidaat["document_id"],
            "naam": kandidaat["naam"],
            "score": combined_score,
            "percentage": max(0, min(100, int(combined_score * 100))),
            "sub_scores": {
                "algemeen": max(0, min(100, int(score_algemeen * 100))),
                "skills": max(0, min(100, int(score_skills * 100))),
                "cultuur": max(0, min(100, int(score_cultuur * 100)))
            }
        })
        
    scored_kandidaten.sort(key=lambda x: x["score"], reverse=True)
    return scored_kandidaten[:limit]

async def haal_top_vacatures_vector(
    kandidaat_vector: list[float] = None, 
    kandidaat_skills: list[float] = None,
    kandidaat_cultuur: list[float] = None,
    limit: int = 5
) -> list[dict]:
    """Reverse matching: multi-dimensional vacature discovery."""
    vacatures = await haal_alle_embeddings("vacature")
    
    scored = []
    for vac in vacatures:
        score_algemeen = 0.0
        if kandidaat_vector and vac["vector"]:
            score_algemeen = bereken_cosine_similarity(kandidaat_vector, vac["vector"])
            
        score_skills = 0.0
        if kandidaat_skills and vac["vector_skills"]:
            score_skills = bereken_cosine_similarity(kandidaat_skills, vac["vector_skills"])
            
        score_cultuur = 0.0
        if kandidaat_cultuur and vac["vector_cultuur"]:
            score_cultuur = bereken_cosine_similarity(kandidaat_cultuur, vac["vector_cultuur"])

        if kandidaat_skills and kandidaat_cultuur and vac["vector_skills"] and vac["vector_cultuur"]:
            combined_score = (score_skills * 0.4) + (score_cultuur * 0.4) + (score_algemeen * 0.2)
        else:
            combined_score = score_algemeen

        scored.append({
            "document_id": vac["document_id"],
            "naam": vac["naam"],
            "score": combined_score,
            "percentage": max(0, min(100, int(combined_score * 100))),
            "sub_scores": {
                "algemeen": max(0, min(100, int(score_algemeen * 100))),
                "skills": max(0, min(100, int(score_skills * 100))),
                "cultuur": max(0, min(100, int(score_cultuur * 100)))
            }
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


# ── Documenten ──

async def haal_uuid_bij_naam(naam: str, doc_type: str) -> str | None:
    """Haal de UUID op van een document op basis van naam en type."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT document_id FROM documenten WHERE naam = ? AND doc_type = ? LIMIT 1",
            (naam, doc_type)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    finally:
        await conn.close()

async def bewaar_document(document_id: str, doc_type: str, naam: str, ruwe_tekst: str, profiel_dict: dict, waarschuwingen: list, content_hash: str = None):
    """Sla een geëxtraheerd profiel en ruwe tekst op in de database."""
    conn = await _get_connection()
    try:
        await conn.execute("""
            INSERT OR REPLACE INTO documenten (document_id, doc_type, naam, ruwe_tekst, profiel_json, waarschuwingen, profiel_compleet, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id, 
            doc_type, 
            naam, 
            ruwe_tekst, 
            json.dumps(profiel_dict, ensure_ascii=False) if profiel_dict else None,
            json.dumps(waarschuwingen, ensure_ascii=False) if waarschuwingen else None,
            True if profiel_dict else False,
            content_hash
        ))
        await conn.commit()
    finally:
        await conn.close()

async def haal_document_bij_hash(content_hash: str, doc_type: str) -> dict | None:
    """Check of een document met deze hash al bestaat."""
    if not content_hash:
        return None
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM documenten WHERE content_hash = ? AND doc_type = ? LIMIT 1",
            (content_hash, doc_type)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()

async def haal_document(identifier: str, doc_type: str = None) -> dict | None:
    """Haal een document op bij naam of UUID. Optioneel filteren op type."""
    conn = await _get_connection()
    try:
        # Zoek eerst op UUID
        cursor = await conn.execute("SELECT * FROM documenten WHERE document_id = ? LIMIT 1", (identifier,))
        row = await cursor.fetchone()
        
        if not row:
            # Zoek op naam
            if doc_type:
                cursor = await conn.execute("SELECT * FROM documenten WHERE naam = ? AND doc_type = ? LIMIT 1", (identifier, doc_type))
            else:
                cursor = await conn.execute("SELECT * FROM documenten WHERE naam = ? LIMIT 1", (identifier,))
            row = await cursor.fetchone()
            
        if not row:
            return None
        doc = dict(row)
        doc["profiel_dict"] = json.loads(doc["profiel_json"]) if doc.get("profiel_json") else None
        doc["waarschuwingen_list"] = json.loads(doc["waarschuwingen"]) if doc.get("waarschuwingen") else []
        return doc
    finally:
        await conn.close()

async def haal_alle_documenten(doc_type: str) -> list[dict]:
    """Haal alle documenten van een specifiek type op."""
    conn = await _get_connection()
    try:
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
    finally:
        await conn.close()


# ── Match Cache ──

async def haal_cached_match(kandidaat_naam: str, vacature_naam: str, modus: str) -> dict | None:
    """Check of er al een match-resultaat bestaat voor deze combinatie."""
    conn = await _get_connection()
    try:
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
        if match.get("profiel_timestamp") and match.get("timestamp"):
            if match["profiel_timestamp"] > match["timestamp"]:
                return None

        if match.get("resultaat_json"):
            match["resultaat_dict"] = json.loads(match["resultaat_json"])
        return match
    finally:
        await conn.close()


# ── GDPR ──

async def verwijder_alle_data(document_id: str) -> dict:
    """
    GDPR 'Vergeet Mij' – verwijdert ALLE data voor een specifiek document UUID.
    Wist uit: documenten, embeddings, matches, en taken tabellen.
    Retourneert een rapport van wat verwijderd is.
    """
    rapport = {"documenten": 0, "embeddings": 0, "matches": 0}
    
    conn = await _get_connection()
    try:
        cursor = await conn.execute("DELETE FROM documenten WHERE document_id = ?", (document_id,))
        rapport["documenten"] = cursor.rowcount
        
        cursor = await conn.execute("DELETE FROM embeddings WHERE document_id = ?", (document_id,))
        rapport["embeddings"] = cursor.rowcount
        
        cursor = await conn.execute("DELETE FROM matches WHERE kandidaat_id = ? OR vacature_id = ?", (document_id, document_id))
        rapport["matches"] = cursor.rowcount
        
        await conn.commit()
    finally:
        await conn.close()
    
    return rapport


# ── Verrijking ──

async def bewaar_verrijking(document_id: str, antwoorden: dict):
    """Sla verrijkings-antwoorden op bij een bestaand document."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT verrijkings_antwoorden FROM documenten WHERE document_id = ?", (document_id,))
        row = await cursor.fetchone()
        
        bestaande = {}
        if row and row[0]:
            bestaande = json.loads(row[0])
        
        bestaande.update(antwoorden)
        
        await conn.execute(
            "UPDATE documenten SET verrijkings_antwoorden = ? WHERE document_id = ?",
            (json.dumps(bestaande, ensure_ascii=False), document_id)
        )
        await conn.commit()
    finally:
        await conn.close()

async def update_profiel_na_verrijking(document_id: str, nieuw_profiel: dict):
    """Update het profiel na verrijking. Bewaart de vorige versie voor delta tracking."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT profiel_json, versie FROM documenten WHERE document_id = ?", 
            (document_id,)
        )
        row = await cursor.fetchone()
        
        vorig_profiel = row[0] if row else None
        huidige_versie = row[1] if row and row[1] else 1
        
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
    finally:
        await conn.close()


# ── Taken (persistent task store) ──

async def maak_task_db(task_id: str, task_type: str, naam: str):
    """Sla een nieuwe taak op in de database."""
    import time
    conn = await _get_connection()
    try:
        await conn.execute("""
            INSERT OR REPLACE INTO taken (id, status, type, naam, progress, progress_percent, error, started_at, updated_at)
            VALUES (?, 'pending', ?, ?, NULL, 0, NULL, ?, ?)
        """, (task_id, task_type, naam, time.time(), time.time()))
        await conn.commit()
    finally:
        await conn.close()

async def update_task_db(task_id: str, **kwargs):
    """Update velden van een bestaande task in de database."""
    ALLOWED_COLUMNS = {"status", "progress", "progress_percent", "error"}
    for k in kwargs:
        if k not in ALLOWED_COLUMNS:
            raise ValueError(f"Ongeldige kolom in update_task_db: {k}")

    import time
    if not kwargs:
        return
    
    conn = await _get_connection()
    try:
        sets = []
        vals = []
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        sets.append("updated_at = ?")
        vals.append(time.time())
        vals.append(task_id)
        
        await conn.execute(f"UPDATE taken SET {', '.join(sets)} WHERE id = ?", vals)
        await conn.commit()
    finally:
        await conn.close()

async def haal_task_db(task_id: str) -> dict | None:
    """Haal een task op uit de database."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM taken WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()

async def haal_alle_taken_db() -> list[dict]:
    """Haal alle recente taken op (max 1 uur oud)."""
    import time
    conn = await _get_connection()
    try:
        cutoff = time.time() - 3600
        cursor = await conn.execute("SELECT * FROM taken WHERE started_at > ? ORDER BY started_at DESC", (cutoff,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def cleanup_taken_db():
    """Verwijder taken ouder dan 1 uur."""
    import time
    conn = await _get_connection()
    try:
        cutoff = time.time() - 3600
        await conn.execute("DELETE FROM taken WHERE started_at < ?", (cutoff,))
        await conn.commit()
    finally:
        await conn.close()
