# Match Agent — Agent Kompas

## Doel
Match kandidaat-CV's met vacatures, 100% lokaal via Ollama. Geen data verlaat de machine.

## Techstack
- **Taal**: Python 3
- **LLM**: Ollama (Qwen 3.5:27b) — lokaal
- **Dependencies**: requests (zie `requirements.txt`)

## Repo map
```
match_agent.py     # Hoofdscript: CLI, Ollama-calls, rapportgeneratie
config.py          # Configuratie: paden, model, prompts
requirements.txt   # Python dependencies
scripts/           # Utility scripts (log-hours, etc.)
.githooks/         # Git hooks (pre-commit, post-commit)
```

## Werkregels
- **100% lokaal**: Alle verwerking draait lokaal via Ollama. Geen PII naar externe servers.
- **iCloud-mappen als bron**: CV's, vacatures en rapporten staan in iCloud Drive (zie `config.py`).
- **Nederlands**: Code-comments en output in het Nederlands.
- **JSON-output**: Ollama geeft gestructureerde JSON-matchresultaten.

## Gebruik
```bash
# Alle CV's matchen met alle vacatures
python3 match_agent.py

# Specifiek CV matchen
python3 match_agent.py --cv cv_sarah_de_vries.txt
```

## Conventies
- Formatter: ruff (indien geïnstalleerd)
- Geen type-checking enforced, maar type hints waar nuttig
- Commits: korte, duidelijke messages in het Engels
