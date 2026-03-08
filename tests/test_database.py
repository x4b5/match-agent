"""Tests voor database functies — cosine similarity, document CRUD, vector ranking."""
import pytest
import math
from backend.database import (
    bereken_cosine_similarity, init_db, bewaar_document, haal_document,
    haal_alle_documenten, bewaar_embedding, haal_alle_embeddings,
    haal_top_matches_vector, haal_top_vacatures_vector, bewaar_match,
    haal_laatste_matches, verwijder_alle_data
)


# ── Cosine Similarity Tests ──

class TestCosineSimilarity:
    def test_identieke_vectoren(self):
        """Identieke vectoren moeten similarity 1.0 geven."""
        vec = [1.0, 2.0, 3.0]
        assert bereken_cosine_similarity(vec, vec) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonale_vectoren(self):
        """Loodrechte vectoren moeten similarity 0.0 geven."""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        assert bereken_cosine_similarity(vec1, vec2) == pytest.approx(0.0, abs=1e-6)

    def test_tegengestelde_vectoren(self):
        """Tegengestelde vectoren moeten similarity -1.0 geven."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        assert bereken_cosine_similarity(vec1, vec2) == pytest.approx(-1.0, abs=1e-6)

    def test_lege_vectoren(self):
        """Lege vectoren moeten 0.0 geven."""
        assert bereken_cosine_similarity([], []) == 0.0

    def test_ongelijke_lengte(self):
        """Vectoren met ongelijke lengte moeten 0.0 geven."""
        assert bereken_cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_nul_vector(self):
        """Een nul-vector moet 0.0 geven (geen deling door nul)."""
        assert bereken_cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_bekende_similarity(self):
        """Test met bekende waarden: [1,2,3] en [4,5,6]."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [4.0, 5.0, 6.0]
        # cos = (4+10+18) / (sqrt(14) * sqrt(77)) = 32 / 32.833 ≈ 0.9746
        expected = 32 / (math.sqrt(14) * math.sqrt(77))
        assert bereken_cosine_similarity(vec1, vec2) == pytest.approx(expected, abs=1e-4)


# ── Document CRUD Tests ──

class TestDocumentCRUD:
    @pytest.fixture(autouse=True)
    async def setup_db(self, temp_data_dir):
        await init_db()

    async def test_bewaar_en_haal_document(self):
        profiel = {"naam": "Test Kandidaat", "kernrol": "Developer"}
        await bewaar_document("uuid-1", "kandidaat", "test_kandidaat", "ruwe tekst", profiel, [])
        
        doc = await haal_document("uuid-1")
        assert doc is not None
        assert doc["naam"] == "test_kandidaat"
        assert doc["profiel_dict"]["naam"] == "Test Kandidaat"

    async def test_haal_document_op_naam(self, temp_data_dir):
        await bewaar_document("id-456", "kandidaat", "Zoek-Mij", "Tekst", {"key": "val"}, [])
        doc = await haal_document("Zoek-Mij", "kandidaat")
        assert doc is not None
        assert doc["document_id"] == "id-456"

    async def test_haal_onbekend_document(self, temp_data_dir):
        doc = await haal_document("Bestaat-Niet", "kandidaat")
        assert doc is None

    async def test_haal_alle_documenten_per_type(self):
        await bewaar_document("u1", "kandidaat", "k1", "t1", {"naam": "K1"}, [])
        await bewaar_document("u2", "vacature", "v1", "t2", {"titel": "V1"}, [])
        await bewaar_document("u3", "kandidaat", "k2", "t3", {"naam": "K2"}, [])
        
        kandidaten = await haal_alle_documenten("kandidaat")
        vacatures = await haal_alle_documenten("vacature")
        
        assert len(kandidaten) == 2
        assert len(vacatures) == 1

    async def test_waarschuwingen_worden_opgeslagen(self):
        await bewaar_document("u4", "kandidaat", "k4", "tekst", {"naam": "K4"}, ["PII gevonden"])
        
        doc = await haal_document("u4")
        assert doc["waarschuwingen_list"] == ["PII gevonden"]


# ── Embedding & Vector Ranking Tests ──

class TestVectorRanking:
    @pytest.fixture(autouse=True)
    async def setup_db(self, temp_data_dir):
        await init_db()

    async def test_bewaar_en_haal_embeddings(self):
        vector = [0.1, 0.2, 0.3]
        await bewaar_embedding("doc-1", "kandidaat", "test", vector)
        
        embeddings = await haal_alle_embeddings("kandidaat")
        assert len(embeddings) == 1
        assert embeddings[0]["vector"] == vector

    async def test_top_matches_sortering(self):
        """Top matches moeten gesorteerd zijn op similarity (hoog naar laag)."""
        # Vacature vector
        vac_vector = [1.0, 0.0, 0.0]
        
        # Kandidaat embeddings: k1 is het meest gelijkend, k3 het minst
        await bewaar_embedding("k1", "kandidaat", "kandidaat_1", [0.9, 0.1, 0.0])
        await bewaar_embedding("k2", "kandidaat", "kandidaat_2", [0.5, 0.5, 0.0])
        await bewaar_embedding("k3", "kandidaat", "kandidaat_3", [0.0, 0.0, 1.0])
        
        top = await haal_top_matches_vector(vac_vector, limit=3)
        
        assert len(top) == 3
        assert top[0]["naam"] == "kandidaat_1"  # Meest gelijkend
        assert top[2]["naam"] == "kandidaat_3"  # Minst gelijkend
        assert top[0]["score"] > top[1]["score"] > top[2]["score"]

    async def test_top_matches_limit(self):
        """Limit parameter moet het aantal resultaten beperken."""
        vac_vector = [1.0, 0.0]
        
        for i in range(10):
            await bewaar_embedding(f"k{i}", "kandidaat", f"kandidaat_{i}", [float(i)/10, 1.0 - float(i)/10])
        
        top = await haal_top_matches_vector(vac_vector, limit=3)
        assert len(top) == 3

    async def test_reverse_matching(self):
        """Reverse matching: welke vacatures passen bij een kandidaat?"""
        kand_vector = [1.0, 0.0, 0.0]
        
        await bewaar_embedding("v1", "vacature", "vac_1", [0.9, 0.1, 0.0])
        await bewaar_embedding("v2", "vacature", "vac_2", [0.0, 1.0, 0.0])
        
        top = await haal_top_vacatures_vector(kand_vector, limit=2)
        assert top[0]["naam"] == "vac_1"


# ── Match Opslag Tests ──

class TestMatchOpslag:
    @pytest.fixture(autouse=True)
    async def setup_db(self, temp_data_dir):
        await init_db()

    async def test_bewaar_en_haal_match(self):
        await bewaar_match("Jan", "uuid-jan", "Developer", "uuid-dev", 85, "standaard", {"test": True})
        
        matches = await haal_laatste_matches(10)
        assert len(matches) == 1
        assert matches[0]["match_percentage"] == 85
        assert matches[0]["kandidaat_naam"] == "Jan"

    async def test_match_met_model_versie(self):
        await bewaar_match("Piet", "uuid-piet", "Tester", "uuid-test", 70, "quick_scan", 
                          {"test": True}, model_versie="qwen3:8b", duur_ms=5200)
        
        matches = await haal_laatste_matches(10)
        assert matches[0]["model_versie"] == "qwen3:8b"
        assert matches[0]["duur_ms"] == 5200


# ── GDPR Verwijdering Tests ──

class TestGDPRVerwijdering:
    @pytest.fixture(autouse=True)
    async def setup_db(self, temp_data_dir):
        await init_db()

    async def test_verwijder_alle_data(self):
        # Maak data aan
        await bewaar_document("gdpr-1", "kandidaat", "gdpr_test", "tekst", {"naam": "GDPR"}, [])
        await bewaar_embedding("gdpr-1", "kandidaat", "gdpr_test", [0.1, 0.2])
        await bewaar_match("gdpr_test", "gdpr-1", "Vacature", "v1", 80, "standaard", {})
        
        # Verwijder alles
        rapport = await verwijder_alle_data("gdpr-1")
        
        assert rapport["documenten"] >= 1
        assert rapport["embeddings"] >= 1
        assert rapport["matches"] >= 1
        
        # Verifieer dat alles weg is
        doc = await haal_document("gdpr-1")
        assert doc is None
        
        embeddings = await haal_alle_embeddings("kandidaat")
        assert len(embeddings) == 0
