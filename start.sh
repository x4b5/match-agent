#!/bin/bash

# Controleer of we in de juiste map staan
cd "$(dirname "$0")"

# Controleer of Ollama draait
if ! pgrep -x "ollama" > /dev/null
then
    echo "⚠️  Ollama lijkt niet te draaien. De AI-functionaliteit werkt mogelijk niet goed zonder de lokale Ollama server."
    echo "Start de Ollama app en probeer het opnieuw."
fi

echo "🚀 MATCHFLIX Backend & Frontend worden opgestart..."

# Start FastAPI server in the background
source .venv/bin/activate
export PYTHONPATH=.
uvicorn backend.main:app --host localhost --port 8000 &
BACKEND_PID=$!

# Wacht even en controleer of de backend nog draait
sleep 2
if ! ps -p $BACKEND_PID > /dev/null
then
    echo "❌ FOUT: De backend kon niet worden gestart. Controleer de logs hierboven."
    exit 1
fi

echo "✅ Backend gestart (PID: $BACKEND_PID)"

# Start SvelteKit development server in the foreground
cd frontend
npm run dev

