# MATCHFLIX — Agent Kompas

## Doel

Match kandidaten uit een kandidatenpool met werkgeversvragen, 100% lokaal via Ollama. De focus ligt op potentieel, persoonlijkheid, drijfveren en verrassende combinaties in plaats van een rigide check op diploma's en harde werkervaring. Geen data verlaat de machine.

## Sterke Punten

- **100% Lokaal & Privacy**: De volledige verwerking (Ollama) en opslag (SQLite/Lokale mappen) gebeurt direct op de machine van de gebruiker. Geen data verlaat de omgeving, wat zorgt voor maximale privacy en veiligheid.
- **AI-Gedreven Matchmaking**: Maakt gebruik van geavanceerde LLM's (zoals Qwen 3.5:27b) voor een multi-dimensionale analyse van matches op basis van persoonlijkheid, cultuur, skills, groei en motivatie. Bevat een 'diepte-analyse' met thinking-modellen.
- **Continu Lerend**: Een recursieve feedback-loop van recruiters verrijkt kandidaatprofielen en verbetert toekomstige matches direct op basis van menselijke inzichten.
- **Focus op Potentieel**: Prioriteert karakter, drijfveren en overdraagbare vaardigheden boven een rigide check op diploma's of functietitels. Het ontdekt verrassende combinaties die recruiters anders over het hoofd zouden zien.

## Kernbegrippen

- **Kandidaatprofiel**: Een AI-geëxtraheerd, gestructureerd profiel dat verder gaat dan een CV door ook persoonlijkheid, impliciete kwaliteiten en ambities vast te leggen.
- **Werkgeversvraag**: Contextuele vertaling van een vacature naar een 'persona' met specifieke teamcultuur-behoeften en gezochte karaktereigenschappen.
- **Dossiercompleetheid**: Een strenge AI-beoordeling van de beschikbare informatie, inclusief suggesties voor vervolgvragen om de match-betrouwbaarheid te verhogen.

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
