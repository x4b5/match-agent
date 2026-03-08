import pytest
from httpx import AsyncClient
import os

# ── Status Tests ──

class TestApiRoot:
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        assert "Matchflix" in response.json()["message"]

    async def test_ollama_status(self, client: AsyncClient):
        response = await client.get("/api/status/")
        assert response.status_code == 200
        assert "online" in response.json()


# ── Kandidaten CRUD Tests ──

class TestKandidatenAPI:
    async def test_list_kandidaten_leeg(self, client: AsyncClient):
        response = await client.get("/api/candidates/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_kandidaat(self, client: AsyncClient):
        response = await client.post("/api/candidates/", params={"name": "Test-Kandidaat"})
        assert response.status_code == 200
        assert response.json()["naam"] == "Test-Kandidaat"
        assert "id" in response.json()

    async def test_create_dubbele_kandidaat(self, client: AsyncClient):
        await client.post("/api/candidates/", params={"name": "Dubbel"})
        response = await client.post("/api/candidates/", params={"name": "Dubbel"})
        assert response.status_code == 400
        assert "bestaat al" in response.json()["detail"].lower()

    async def test_create_lege_naam(self, client: AsyncClient):
        response = await client.post("/api/candidates/", params={"name": "   "})
        assert response.status_code == 400
        assert "leeg" in response.json()["detail"].lower()

    async def test_delete_kandidaat(self, client: AsyncClient):
        # Maak eerst aan
        await client.post("/api/candidates/", params={"name": "te_verwijderen"})
        # Verwijder
        response = await client.delete("/api/candidates/te_verwijderen")
        assert response.status_code == 200
        # Omdat de map direct door create_item wordt gemaakt, moet dit "Verwijderd (DB+FS)" zijn
        # MAAR: create_item registreert het nog niet in de DB (dat doet de profielgeneratie pas)
        # Dus delete_item vindt het NIET in de DB, maar WEL op FS.
        # Wacht, base_router delete_item doet: haal_uuid_bij_naam.
        # Als het nog niet geprofileerd is, staat het niet in de documenten tabel.
        # Dus het verwijdert alleen van FS.
        assert "Verwijderd" in response.json()["message"]

    async def test_delete_niet_bestaande_kandidaat(self, client: AsyncClient):
        response = await client.delete("/api/candidates/Echt-Niet-Bestaand")
        # Als het nergens is, returnen we nu 200 "Verwijderd uit database (map bestond niet)"
        # omdat haal_uuid_bij_naam None geeft en os.path.exists False geeft.
        # Eigenlijk zou dit een 404 kunnen zijn, maar we houden het nu op 200 voor idempotentie.
        assert response.status_code == 200


# ── Werkgevers CRUD Tests ──

class TestWerkgeversAPI:
    async def test_list_werkgevers(self, client: AsyncClient):
        response = await client.get("/api/employers/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_werkgever(self, client: AsyncClient):
        response = await client.post("/api/employers/", params={"name": "Test-Job"})
        assert response.status_code == 200
        assert response.json()["naam"] == "Test-Job"

    async def test_create_lege_naam(self, client: AsyncClient):
        response = await client.post("/api/employers/", params={"name": " "})
        assert response.status_code == 400


# ── GDPR Tests ──

class TestGDPRAPI:
    async def test_vergeet_mij_niet_gevonden(self, client: AsyncClient):
        response = await client.post("/api/gdpr/vergeet-mij", json={
            "naam": "Onbekend",
            "doc_type": "kandidaat"
        })
        assert response.status_code == 404

    async def test_vergeet_mij_met_data(self, client: AsyncClient):
        # We moeten het eerst in de DB krijgen, maar create_item doet dat nog niet.
        # Gebruik de database helper direct om een nep-document te maken voor deze test
        from backend.database import bewaar_document
        await bewaar_document("test-uuid-123", "kandidaat", "AVG-Persoon", "", {}, [])
        
        response = await client.post("/api/gdpr/vergeet-mij", json={
            "naam": "AVG-Persoon",
            "doc_type": "kandidaat"
        })
        assert response.status_code == 200
        assert "AVG/GDPR" in response.json()["message"]


# ── Tasks API Tests ──

class TestTasksAPI:
    async def test_list_tasks(self, client: AsyncClient):
        response = await client.get("/api/tasks/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_task_niet_gevonden(self, client: AsyncClient):
        response = await client.get("/api/tasks/ongeldig-id")
        assert response.status_code == 404


# ── Match History Tests ──

class TestMatchHistoryAPI:
    async def test_match_history_leeg(self, client: AsyncClient):
        response = await client.get("/api/matching/history")
        assert response.status_code == 200
        assert response.json() == []
