# Contributing

## Setup

```bash
# Clone de repo
git clone <repo-url>
cd match-agent

# Maak een virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Installeer Python dependencies
pip install -r requirements.txt

# Installeer frontend dependencies
cd frontend && npm install && cd ..

# Zorg dat Ollama draait
ollama serve
ollama pull qwen3.5:27b
```

## Development workflow

```bash
# Start backend + frontend
./start.sh

# Format code (optioneel, vereist ruff)
ruff format .

# Commit
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
