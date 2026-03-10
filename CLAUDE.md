# MATCHFLIX — Agent Kompas

## Doel

Match kandidaten uit een kandidatenpool met werkgeversvragen, 100% lokaal via Ollama. De focus ligt op potentieel, persoonlijkheid, drijfveren en verrassende combinaties in plaats van een rigide check op diploma's en harde werkervaring. Geen data verlaat de machine.

## Kernpijlers

- **Alles blijft op jouw computer**: De AI draait volledig lokaal. Er wordt geen data naar de cloud of externe diensten gestuurd — wat je invoert, blijft bij jou.
- **Automatische bescherming van persoonsgegevens**: Voordat tekst wordt geanalyseerd, worden gevoelige gegevens zoals e-mailadressen, IBAN-nummers en BSN-nummers automatisch onherkenbaar gemaakt. BSN-nummers worden zelfs wiskundig gecontroleerd op echtheid.
- **Potentie boven papier**: Matchflix kijkt verder dan diploma's en functietitels. Het draait om wie iemand is: karakter, drijfveren en of iemand past bij het team en de cultuur.
- **Heldere taal, geen jargon**: Alle communicatie is geschreven op B1-niveau — begrijpelijk voor iedereen, zonder vakjargon. Zo is het toegankelijk voor zowel recruiters als kandidaten.
- **Slim zoeken op betekenis**: Het systeem zoekt niet op losse woorden, maar begrijpt de betekenis achter profielen en vacatures. Daardoor vindt het ook matches die je met traditioneel zoeken zou missen — op drie vlakken: algemene fit, vaardigheden en cultuur.
- **Leert van jouw feedback**: Wanneer een recruiter feedback geeft op een match, wordt het kandidaatprofiel direct verrijkt. Het systeem leert mee en levert bij de volgende ronde betere matches.

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
