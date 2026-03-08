# 🎯 MATCHFLIX

Een slimme, 100% lokale pre-selectie en match-tool aangedreven door Ollama (Qwen-modellen), FastAPI en SvelteKit.

## Visie

_MATCHFLIX_ is geen traditionele vacaturebank die CV's simpelweg naast een eisenlijstje legt. Deze applicatie is gebouwd om **potentieel, persoonlijkheid en drijfveren** te matchen aan bedrijfscultuur en gezochte kwaliteiten. Het doel is om _out-of-the-box_ associaties te maken en recruiters en werkgevers te inspireren met kandidaten die ze in eerste instantie misschien over het hoofd hadden gezien.

## Features

- **100% Lokaal & Privacy First**: Alle AI draait lokaal via [Ollama](https://ollama.ai). Er gaat geen data naar externe API's (dus 100% vertrouwelijk en veilig voor persoonsgegevens).
- **Gestructureerde LLM-Profielen**: Zet ruwe MS Word-, PDF- of TXT-documenten om naar gestructureerde JSON-profielen met focus op karakter, kwaliteiten en persoonlijkheid via AI.
- **Slimme Matching**: Combineert kandidaatprofielen met werkgeversvragen en geeft creatieve, verrassende en goed onderbouwde matches.
- **Web Interface**: SvelteKit frontend met streaming match-resultaten en meerdere match-modi.

## Installatie & Gebruik

### Vereisten

- Python 3.10 of hoger
- Node.js 18 of hoger
- [Ollama](https://ollama.com) lokaal geïnstalleerd. Zorg dat je een of meerdere LLM-modellen hebt gedownload (bijvoorbeeld `qwen3:8b` of `qwen3.5:27b` of varianten).

### Installatie

```bash
# 1. Clone de repository
# 2. Maak een virtual environment aan & activeer deze
python3 -m venv .venv
source .venv/bin/activate

# 3. Installeer Python afhankelijkheden
pip install -r requirements.txt

# 4. Installeer frontend afhankelijkheden
cd frontend && npm install && cd ..
```

### Start de app

```bash
./start.sh
```

Dit start de FastAPI backend (poort 8000) en de SvelteKit frontend.

## Configuratie

In `backend/config.py` kan je de locaties van de data aanpassen (bijv. een gedeelde map op iCloud of OneDrive). Hier vind je ook de uitgebreide AI-prompts die het inspirerende en 'out-of-the-box' matching-karakter bepalen.
