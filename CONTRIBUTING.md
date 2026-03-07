# Contributing

## Setup

```bash
# Clone de repo
git clone <repo-url>
cd match-agent

# Maak een virtual environment
python3 -m venv venv
source venv/bin/activate

# Installeer dependencies
pip install -r requirements.txt

# Kopieer environment variabelen
cp .env.example .env

# Zorg dat Ollama draait
ollama serve
ollama pull qwen3.5:27b
```

## Development workflow

```bash
# Start je werkdag (registreert starttijd)
bash start-day.sh

# Draai het script
python3 match_agent.py --cv cv_sarah_de_vries.txt

# Format code (optioneel, vereist ruff)
ruff format .

# Commit (post-commit hook logt automatisch uren)
git add -A
git commit -m "beschrijving van wijziging"
```

## Git hooks

De repo gebruikt custom git hooks in `.githooks/`. Deze worden automatisch actief via:
```bash
git config core.hooksPath .githooks
```

- **pre-commit**: Draait `ruff format --check` (als ruff beschikbaar is)
- **post-commit**: Logt uren in `LOGBOOK.md`
