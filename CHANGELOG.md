# Changelog

## [0.2.0] — 2025-03-08

### Added
- SvelteKit web interface met streaming match-resultaten
- FastAPI backend met API routes
- SQLite database voor kandidaten, werkgeversvragen en matches
- Meerdere match-modi (quick, standaard, diepgaand)
- Start-script voor backend + frontend (`start.sh`)

### Changed
- Architectuur: van Streamlit monoliet naar FastAPI + SvelteKit
- Profiel extractie verplaatst naar backend services

### Removed
- Streamlit frontend (`app.py`)
- CLI interface (`paper_agent.py`)

## [0.1.0] — 2025-03-07

### Added
- CV-matching via Ollama (Qwen 3.5:27b)
- CLI interface met `--cv` filter
- JSON match-resultaten (percentage, matchende/ontbrekende punten, onderbouwing)
- Tekstrapport generatie per kandidaat
- iCloud-integratie voor CV's, vacatures en rapporten
- Configureerbare prompts en modelsettings
