# PaperStrip — Agent Kompas

## Doel

Match kandidaten uit een kandidatenpool met werkgeversvragen, 100% lokaal via Ollama. De focus ligt op potentieel, persoonlijkheid, drijfveren en verrassende combinaties in plaats van een rigide check op diploma's en harde werkervaring. Geen data verlaat de machine.

## Kernbegrippen

- **Kandidaatprofiel**: een gestructureerd JSON-profiel dat de persoonlijkheid, kwaliteiten, drijfveren en skills van een kandidaat beschrijft.
- **Werkgeversvraag**: elke context van een werkgever (vacature, project, cultuurbehoefte) vertaald naar gezochte persoonlijkheid, teamcultuur en onmisbare talenten.
- **Matching**: het ontdekken van een out-of-the-box fit tussen kandidaten en werkgevers, die mensen inspireert om verder te kijken dan hun huidige zoekveld.

## Techstack

- **Taal**: Python 3
- **LLM**: Ollama (bijv. Qwen 3.5:27b en qwen3:8b) — lokaal
- **UI**: Streamlit (`app.py`)

## Repo map

```
paper_agent.py     # CLI Runner voor de matching engine
app.py             # Streamlit frontend (streamlit run app.py)
config.py          # Configuratie: paden, modellen, AI-prompts
profiel_agent.py   # Extractie van gestructureerde JSON profielen
requirements.txt   # Python dependencies
scripts/           # Utility scripts
```

## Werkregels

- **100% lokaal**: Alle verwerking draait lokaal via Ollama.
- **Focus op Potentieel**: We optimaliseren altijd voor persoonlijkheid en overdraagbare vaardigheden. We bouwen een talent-tool, geen ouderwetse vacaturebank.
- **Map-gebaseerde profielen**: Gegevens staan georganiseerd in individuele mappen (`kandidaten/naam/` en `werkgeversvragen/vraag/`) met ruwe bestanden en een afgeleide `*.json`.
- **Nederlands**: Code-comments en frontend in het Nederlands.

## Gebruik & UI

Start de web interface:

```bash
streamlit run app.py
```

Voor CLI matching:

```bash
python3 paper_agent.py
```

## Conventies

- Formatter: ruff (indien geïnstalleerd)
- Commits: korte, duidelijke messages in het Engels
