# MATCHFLIX — Agent Kompas

## Doel

Match kandidaten uit een kandidatenpool met werkgeversvragen, 100% lokaal via Ollama. De focus ligt op potentieel, persoonlijkheid, drijfveren en verrassende combinaties in plaats van een rigide check op diploma's en harde werkervaring. Geen data verlaat de machine.

## Kernbegrippen

- **Kandidaatprofiel**: een gestructureerd JSON-profiel dat de persoonlijkheid, kwaliteiten, drijfveren en skills van een kandidaat beschrijft.
- **Werkgeversvraag**: elke context van een werkgever (vacature, project, cultuurbehoefte) vertaald naar gezochte persoonlijkheid, teamcultuur en onmisbare talenten.
- **Matching**: het ontdekken van een out-of-the-box fit tussen kandidaten en werkgevers, die mensen inspireert om verder te kijken dan hun huidige zoekveld.

## Techstack

- **Taal**: Python 3 (backend), TypeScript (frontend)
- **LLM**: Ollama (bijv. Qwen 3.5:27b en qwen3:8b) — lokaal
- **Backend**: FastAPI (`backend/`)
- **Frontend**: SvelteKit (`frontend/`)

## Repo map

```
backend/           # FastAPI backend (uvicorn backend.main:app)
  main.py          # FastAPI app entry point
  config.py        # Configuratie: paden, modellen, AI-prompts
  database.py      # Database models en connectie
  services/        # Matching engine, profiel extractie
  api/             # API routes
frontend/          # SvelteKit frontend
  src/             # Svelte componenten en routes
requirements.txt   # Python dependencies
start.sh           # Start backend + frontend
```

## Werkregels

- **100% lokaal**: Alle verwerking draait lokaal via Ollama.
- **Focus op Potentieel**: We optimaliseren altijd voor persoonlijkheid en overdraagbare vaardigheden. We bouwen een talent-tool, geen ouderwetse vacaturebank.
- **Map-gebaseerde profielen**: Gegevens staan georganiseerd in individuele mappen (`kandidaten/naam/` en `werkgeversvragen/vraag/`) met ruwe bestanden en een afgeleide `*.json`.
- **Nederlands**: Code-comments en frontend in het Nederlands.

## Gebruik & UI

Start de web interface:

```bash
./start.sh
```

Dit start zowel de FastAPI backend (poort 8000) als de SvelteKit frontend.

## Conventies

- Formatter: ruff (indien geïnstalleerd)
- Commits: korte, duidelijke messages in het Engels
