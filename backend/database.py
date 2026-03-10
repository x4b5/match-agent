import aiosqlite
import json
import os
import logging

import numpy as np
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

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_weights (
                dimensie TEXT PRIMARY KEY,
                huidig_gewicht REAL NOT NULL
            )
        """)

        # Seed met defaults als tabel leeg is
        cursor = await conn.execute("SELECT COUNT(*) FROM learning_weights")
        row = await cursor.fetchone()
        if row[0] == 0:
            await conn.executemany(
                "INSERT INTO learning_weights (dimensie, huidig_gewicht) VALUES (?, ?)",
                [("skills", 0.4), ("cultuur", 0.4), ("algemeen", 0.2)]
            )
        
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

        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN recruiter_rating INTEGER")
        except Exception:
            pass  # Kolom bestaat al

        try:
            await conn.execute("ALTER TABLE matches ADD COLUMN is_hire BOOLEAN DEFAULT 0")
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
async def bewaar_recruiter_rating(match_id: int, rating: int):
    """Sla een recruiter-rating (1-5) op voor een specifieke match."""
    conn = await _get_connection()
    try:
        await conn.execute(
            "UPDATE matches SET recruiter_rating = ? WHERE id = ?",
            (rating, match_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def tel_onverwerkte_ratings() -> int:
    """Tel matches met een rating maar waarvan feedback nog niet verwerkt is."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM matches WHERE recruiter_rating IS NOT NULL AND feedback_verwerkt = 0"
        )
        row = await cursor.fetchone()
        return row[0]
    finally:
        await conn.close()


async def haal_hoog_gewaardeerde_matches(min_rating: int = 4) -> list[dict]:
    """Haal matches op met een rating >= min_rating."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM matches WHERE recruiter_rating >= ? ORDER BY timestamp DESC",
            (min_rating,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def haal_learning_weights() -> dict[str, float]:
    """Haal de huidige learning weights op."""
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT dimensie, huidig_gewicht FROM learning_weights")
        rows = await cursor.fetchall()
        if not rows:
            return {"skills": 0.4, "cultuur": 0.4, "algemeen": 0.2}
        return {row["dimensie"]: row["huidig_gewicht"] for row in rows}
    finally:
        await conn.close()


async def update_learning_weights(weights: dict[str, float]):
    """Update alle learning weights."""
    conn = await _get_connection()
    try:
        for dimensie, gewicht in weights.items():
            await conn.execute(
                "INSERT OR REPLACE INTO learning_weights (dimensie, huidig_gewicht) VALUES (?, ?)",
                (dimensie, gewicht)
            )
        await conn.commit()
        logger.info(f"Learning weights bijgewerkt: {weights}")
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
    """Bereken de cosine similarity tussen twee vectoren via numpy."""
    a, b = np.asarray(vec1, dtype=np.float64), np.asarray(vec2, dtype=np.float64)
    if a.shape != b.shape or a.size == 0:
        return 0.0
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def _batch_cosine(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Bereken cosine similarity van een query vector tegen een matrix van vectoren in batch."""
    norms = np.linalg.norm(matrix, axis=1)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(matrix.shape[0])
    denom = norms * query_norm
    # Vermijd deling door nul
    denom = np.where(denom == 0, 1.0, denom)
    return matrix @ query / denom


async def haal_top_matches_vector(
    vacature_vector: list[float] = None,
    vacature_skills: list[float] = None,
    vacature_cultuur: list[float] = None,
    limit: int = 5,
    gewichten: dict[str, float] = None
) -> list[dict]:
    """Haal de top kandidaat matches op via multi-dimensional vector similarity (numpy batch)."""
    kandidaten = await haal_alle_embeddings("kandidaat")
    if not kandidaten:
        return []

    # Filter kandidaten met een geldige vector
    valid = [k for k in kandidaten if k["vector"]]
    if not valid:
        return []

    # Bouw matrices en bereken batch scores
    scores_algemeen = np.zeros(len(valid))
    scores_skills = np.zeros(len(valid))
    scores_cultuur = np.zeros(len(valid))

    if vacature_vector:
        q = np.asarray(vacature_vector, dtype=np.float64)
        mat = np.array([k["vector"] for k in valid], dtype=np.float64)
        scores_algemeen = _batch_cosine(mat, q)

    if vacature_skills:
        q_s = np.asarray(vacature_skills, dtype=np.float64)
        # Alleen kandidaten met skills vector; de rest houdt score 0
        indices = [i for i, k in enumerate(valid) if k["vector_skills"]]
        if indices:
            mat_s = np.array([valid[i]["vector_skills"] for i in indices], dtype=np.float64)
            batch_scores = _batch_cosine(mat_s, q_s)
            for j, idx in enumerate(indices):
                scores_skills[idx] = batch_scores[j]

    if vacature_cultuur:
        q_c = np.asarray(vacature_cultuur, dtype=np.float64)
        indices = [i for i, k in enumerate(valid) if k["vector_cultuur"]]
        if indices:
            mat_c = np.array([valid[i]["vector_cultuur"] for i in indices], dtype=np.float64)
            batch_scores = _batch_cosine(mat_c, q_c)
            for j, idx in enumerate(indices):
                scores_cultuur[idx] = batch_scores[j]

    # Gewogen combinatie (dynamisch via learning weights)
    w = gewichten or {}
    w_skills = w.get("skills", 0.4)
    w_cultuur = w.get("cultuur", 0.4)
    w_algemeen = w.get("algemeen", 0.2)

    has_sub = np.array([
        bool(vacature_skills and vacature_cultuur and k["vector_skills"] and k["vector_cultuur"])
        for k in valid
    ])
    combined = np.where(
        has_sub,
        scores_skills * w_skills + scores_cultuur * w_cultuur + scores_algemeen * w_algemeen,
        scores_algemeen,
    )

    # Top-N via argpartition (sneller dan full sort bij grote sets)
    if len(combined) > limit:
        top_idx = np.argpartition(combined, -limit)[-limit:]
        top_idx = top_idx[np.argsort(combined[top_idx])[::-1]]
    else:
        top_idx = np.argsort(combined)[::-1]

    return [
        {
            "document_id": valid[i]["document_id"],
            "naam": valid[i]["naam"],
            "score": float(combined[i]),
            "percentage": max(0, min(100, int(combined[i] * 100))),
            "sub_scores": {
                "algemeen": max(0, min(100, int(scores_algemeen[i] * 100))),
                "skills": max(0, min(100, int(scores_skills[i] * 100))),
                "cultuur": max(0, min(100, int(scores_cultuur[i] * 100))),
            },
        }
        for i in top_idx
    ]

async def haal_top_vacatures_vector(
    kandidaat_vector: list[float] = None,
    kandidaat_skills: list[float] = None,
    kandidaat_cultuur: list[float] = None,
    limit: int = 5,
    gewichten: dict[str, float] = None
) -> list[dict]:
    """Reverse matching: multi-dimensional vacature discovery (numpy batch)."""
    vacatures = await haal_alle_embeddings("vacature")
    if not vacatures:
        return []

    valid = [v for v in vacatures if v["vector"]]
    if not valid:
        return []

    scores_algemeen = np.zeros(len(valid))
    scores_skills = np.zeros(len(valid))
    scores_cultuur = np.zeros(len(valid))

    if kandidaat_vector:
        q = np.asarray(kandidaat_vector, dtype=np.float64)
        mat = np.array([v["vector"] for v in valid], dtype=np.float64)
        scores_algemeen = _batch_cosine(mat, q)

    if kandidaat_skills:
        q_s = np.asarray(kandidaat_skills, dtype=np.float64)
        indices = [i for i, v in enumerate(valid) if v["vector_skills"]]
        if indices:
            mat_s = np.array([valid[i]["vector_skills"] for i in indices], dtype=np.float64)
            batch_scores = _batch_cosine(mat_s, q_s)
            for j, idx in enumerate(indices):
                scores_skills[idx] = batch_scores[j]

    if kandidaat_cultuur:
        q_c = np.asarray(kandidaat_cultuur, dtype=np.float64)
        indices = [i for i, v in enumerate(valid) if v["vector_cultuur"]]
        if indices:
            mat_c = np.array([valid[i]["vector_cultuur"] for i in indices], dtype=np.float64)
            batch_scores = _batch_cosine(mat_c, q_c)
            for j, idx in enumerate(indices):
                scores_cultuur[idx] = batch_scores[j]

    # Gewogen combinatie (dynamisch via learning weights)
    w = gewichten or {}
    w_skills = w.get("skills", 0.4)
    w_cultuur = w.get("cultuur", 0.4)
    w_algemeen = w.get("algemeen", 0.2)

    has_sub = np.array([
        bool(kandidaat_skills and kandidaat_cultuur and v["vector_skills"] and v["vector_cultuur"])
        for v in valid
    ])
    combined = np.where(
        has_sub,
        scores_skills * w_skills + scores_cultuur * w_cultuur + scores_algemeen * w_algemeen,
        scores_algemeen,
    )

    if len(combined) > limit:
        top_idx = np.argpartition(combined, -limit)[-limit:]
        top_idx = top_idx[np.argsort(combined[top_idx])[::-1]]
    else:
        top_idx = np.argsort(combined)[::-1]

    return [
        {
            "document_id": valid[i]["document_id"],
            "naam": valid[i]["naam"],
            "score": float(combined[i]),
            "percentage": max(0, min(100, int(combined[i] * 100))),
            "sub_scores": {
                "algemeen": max(0, min(100, int(scores_algemeen[i] * 100))),
                "skills": max(0, min(100, int(scores_skills[i] * 100))),
                "cultuur": max(0, min(100, int(scores_cultuur[i] * 100))),
            },
        }
        for i in top_idx
    ]


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
