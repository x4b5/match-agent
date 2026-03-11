import pytest
import os
import tempfile
import aiosqlite

# Override ICLOUD_BASE to use temp directory during tests
@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch, tmp_path):
    """Gebruik een tijdelijke directory voor alle tests."""
    kandidaten = str(tmp_path / "kandidaten")
    werkgevers = str(tmp_path / "werkgeversvragen")
    
    monkeypatch.setattr("backend.config.ICLOUD_BASE", str(tmp_path))
    monkeypatch.setattr("backend.config.KANDIDATEN_DIR", kandidaten)
    monkeypatch.setattr("backend.config.WERKGEVERSVRAGEN_DIR", werkgevers)
    monkeypatch.setattr("backend.config.RAPPORT_DIR", str(tmp_path / "rapporten"))
    monkeypatch.setattr("backend.database.DB_PATH", str(tmp_path / "test.db"))
    
    os.makedirs(kandidaten, exist_ok=True)
    os.makedirs(werkgevers, exist_ok=True)
    return tmp_path

@pytest.fixture
async def client():
    """Asynchrone test client voor FastAPI."""
    from backend.main import app
    from httpx import AsyncClient, ASGITransport
    from backend.database import init_db
    
    # Zorg dat de DB geïnitialiseerd is voor de API tests
    await init_db()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
