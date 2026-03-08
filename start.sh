#!/bin/bash

# Controleer of we in de juiste map staan
cd "$(dirname "$0")"

# Controleer of Ollama draait (optioneel, maar handig voor feedback)
if ! pgrep -x "ollama" > /dev/null
then
    echo "⚠️  Ollama lijkt niet te draaien. De AI-functionaliteit werkt mogelijk niet goed zonder de lokale Ollama server."
    echo "Start de Ollama app en probeer het opnieuw."
fi

echo "🚀 PaperStrip wordt opgestart..."

# Start streamlit direct vanuit de venv (geen handmatige activatie nodig)
./.venv/bin/streamlit run app.py
