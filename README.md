# 🎯 PaperStrip

Een slimme, 100% lokale pre-selectie en match-tool aangedreven door Ollama (Qwen-modellen) en Python/Streamlit.

## Visie

De _PaperStrip_ is geen traditionele vacaturebank die CV's simpelweg naast een eisenlijstje legt. Deze applicatie is gebouwd om **potentieel, persoonlijkheid en drijfveren** te matchen aan bedrijfscultuur en gezochte kwaliteiten. Het doel is om _out-of-the-box_ associaties te maken en recruiters en werkgevers te inspireren met kandidaten die ze in eerste instantie misschien over het hoofd hadden gezien.

## Features

- **100% Lokaal & Privacy First**: Alle AI draait lokaal via [Ollama](https://ollama.ai). Er gaat geen data naar externe API's (dus 100% vertrouwelijk en veilig voor persoonsgegevens).
- **Gestructureerde LLM-Profielen**: Zet ruwe MS Word-, PDF- of TXT-documenten om naar gestructureerde JSON-profielen met focus op karakter, kwaliteiten en persoonlijkheid via AI.
- **Slimme Matching**: Combineert kandidaatprofielen met werkgeversvragen en geeft creatieve, verrassende en goed onderbouwde matches.
- **Streamlit Dashboard**: Gebruiksvriendelijke interface voor het beheren van documenten (dossiers), genereren van profielen en starten van het (parallelle) matchproces.

## Installatie & Gebruik

### Vereisten

- Python 3.10 of hoger
- [Ollama](https://ollama.com) lokaal geïnstalleerd. Zorg dat je een of meerdere LLM-modellen hebt gedownload (bijvoorbeeld `qwen3:8b` of `qwen3.5:27b` of varianten).

### Installatie

```bash
# 1. Clone de repository
# 2. Maak een virtual environment aan & activeer deze
python3 -m venv venv
source venv/bin/activate  # Of venv\Scripts\activate op Windows

# 3. Installeer afhankelijkheden
pip install -r requirements.txt
```

### Start de app (Interface)

De Streamlit frontend is de eenvoudigste manier om PaperStrip te bedienen.

```bash
streamlit run app.py
```

## Configuratie (`config.py`)

In `config.py` kan je de locaties van de data aanpassen (bijv. een gedeelde map op iCloud of OneDrive). Hier vind je ook de uitgebreide AI-prompts die het inspirerende en 'out-of-the-box' matching-karakter bepalen.
