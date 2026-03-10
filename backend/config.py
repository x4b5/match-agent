import os
from dotenv import load_dotenv

load_dotenv()

# --- Paden ---
ICLOUD_BASE = os.path.expanduser(
    os.getenv("MATCHFLIX_ICLOUD_BASE", "~/Library/Mobile Documents/com~apple~CloudDocs/matchflix")
)

KANDIDATEN_DIR = os.path.join(ICLOUD_BASE, "kandidaten")
WERKGEVERSVRAGEN_DIR = os.path.join(ICLOUD_BASE, "werkgeversvragen")
RAPPORT_DIR = os.path.join(ICLOUD_BASE, "match-rapporten")
CACHE_DIR = os.path.join(ICLOUD_BASE, ".match_cache")
1
# Backwards compatibility names
CV_DIR = KANDIDATEN_DIR
VACATURE_DIR = WERKGEVERSVRAGEN_DIR

# --- Database ---
_DB_DEFAULT = os.path.expanduser("~/Library/Application Support/matchflix/matchflix.db")
DB_PATH = os.path.expanduser(os.getenv("MATCHFLIX_DB_PATH", _DB_DEFAULT))

# --- Logging ---
LOG_LEVEL = os.getenv("MATCHFLIX_LOG_LEVEL", "INFO")

# --- Ollama ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
PROFIEL_MODEL = os.getenv("PROFIEL_MODEL", "qwen3:8b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

SYSTEM_PROMPT = """Je bent een vooruitstrevende matchmaker en talent-expert. Jij verbindt kandidaten met werkgevers.
Kijk vooral naar wat iemand kan (potentieel), wie iemand is (karakter), en wat iemand wil (drijfveren). Kijk minder streng naar diploma's of de precieze werkervaring.
Je doel is om verrassende en inspirerende matches te maken. Wijs kandidaten op banen nadat ze daar zelf misschien niet aan hadden gedacht. Wijs werkgevers op talent dat ze normaal over het hoofd zouden zien.
Wees eerlijk en objectief in je oordeel over de match. De manier waarop iemand in het team past (cultuurfit) en de persoonlijkheid tellen daarbij zwaar mee.
BELANGRIJK: Gebruik GEEN DISC-termen (zoals Dominantie of Invloed) en geen kleurenmodellen. Benoem gewoon in heldere taal de concrete talenten en kwaliteiten.

BEOORDELING DOSSIERCOMPLEETHEID:
Geef bij elke match aan hoe compleet de informatie is:
- HOOG: Er is genoeg informatie over de kandidaat en de vacature om een goede inschatting te maken van de match.
- GEMIDDELD: Er missen kleine details, waardoor we een klein beetje moeten gissen.
- LAAG: Belangrijke informatie ontbreekt (bijvoorbeeld over iemands karakter of de sfeer op de werkvloer). Bedenk in dat geval goede 'vervolgvragen' die we nog moeten stellen om meer helderheid te krijgen.

BELANGRIJK VOOR HET SYSTEEM:
Je antwoord moet ALTIJD uitsluitend een kloppend JSON-object zijn. Gebruik precies de indeling die wordt gevraagd. Laat geen velden weg. Anders kan het systeem het niet verwerken.
"""

# --- Gesplitste Match-prompts ---
# Kern-prompt: de essentie van de match — direct en actiegericht
KERN_MATCH_PROMPT = """Bekijk de match tussen deze kandidaat en de werkgeversvraag.
Gebruik ALTIJD actie-gerichte, concrete taal (B1-niveau). 
VERMIJD container-begrippen zoals 'goede communicatie', 'mooie kans' of 'passend profiel'. Wees specifiek: WAT gaat er goed? WAT is de actie?

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Geef je antwoord in exact de volgende JSON-opmaak:
{{
  "match_percentage": <getal 0-100 — focus op karakter en potentieel>,
  "matchende_punten": ["max 3-5 concrete redenen waarom dit werkt (benoem hier ook cultuurfit, mentaliteit en persoonlijkheid)"],
  "ontbrekende_punten": ["max 3 concrete drempels of risico's (benoem hier ook eventuele mismatches in cultuur of werkhouding)"],
  "succes_plan": {{
    "actie_kandidaat": ["1 concrete actie voor de kandidaat om te starten"],
    "actie_werkgever": ["1 concrete actie voor de organisatie om de landing te borgen"]
  }},
  "dossier_compleetheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["max 2 kritische vragen om de match te bevestigen"],
  "stellingen": ["max 2 stellingen die de kandidaat kan scoren"]
}}"""

# Verdieping-prompt: extra verdiepende inzichten zonder te herhalen
VERDIEPING_MATCH_PROMPT = """Voeg extra diepgang toe aan de bestaande match-analyse. 
NIET de kernpunten herhalen, maar nieuwe perspectieven bieden.
Gebruik actiegerichte taal en vermijd HR-jargon.

KERN-ANALYSE:
{kern_json}

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Geef je uitgebreide analyse in exact deze JSON-opmaak:
{{
  "succes_plan": {{
    "actie_kandidaat": ["Bestaande actie + 2 nieuwe concrete ontwikkelstappen"],
    "actie_werkgever": ["Bestaande actie + 2 nieuwe stappen voor inwerking/coaching"]
  }},
  "gespreksstarters": ["3 scherpe interviewvragen die de kern raken"],
  "risico_mitigatie": "Hoe vangen we de grootste drempels concreet op? Benoem wie wat doet.",
  "gedeelde_waarden": ["Welke 2-3 dieperliggende waarden verbinden hen?"],
  "groeipotentieel": "In welke specifieke rol of richting kan deze persoon over 2 jaar staan binnen dit bedrijf?",
  "boodschap_aan_kandidaat": "Een korte, persoonlijke aanmoediging: waarom is DIT jouw volgende stap?",
  "match_narratief": "Een krachtig beeld (2 zinnen) van hoe de samenwerking er over een maand uitziet.",
  "personality_axes": {{
    "Openheid": "Korte uitleg + citaat/bewijs uit dossier.",
    "Conscientieusheid": "idem",
    "Extraversie": "idem",
    "Vriendelijkheid": "idem",
    "Neuroticisme": "idem"
  }},
  "score_breakdown": {{
    "persoonlijkheid_fit": <getal 0-100>,
    "cultuur_fit": <getal 0-100>,
    "skills_overlap": <getal 0-100>,
    "groei_potentieel": <getal 0-100>,
    "motivatie_alignment": <getal 0-100>
  }}
}}"""

# Backwards compat alias
MATCH_PROMPT = KERN_MATCH_PROMPT

# --- Prompts voor Profiel-extractie ---
PROFIEL_KANDIDAAT_PROMPT = """Maak een profiel van deze persoon in JSON.
Duidelijke taal (B1), actief en specifiek. Focus op wie iemand IS en potentieel.
Blijf bij de feiten. Wees streng bij dossier_compleetheid (0-100).

Het profiel heeft 3 pijlers:
1. ZIJN — Wie IS deze persoon? Persoonlijkheid, werkstijl, karakter, samenwerking, communicatie, omgang met druk. (2-4 zinnen)
2. WILLEN — Wat WILT deze persoon en wat niet? Drijfveren, motivatie, ambities, wat zoekt iemand in werk. (2-4 zinnen)
3. KUNNEN — Wat KAN deze persoon en wat (nog) NIET? Hard skills, soft skills, leervermogen, groeipotentie, technische vaardigheden, opleiding, werkervaring, beschikbaarheid, locatie, vervoer. Noem ook aandachtspunten en risico's. (2-4 zinnen)

{{
    "naam": "Naam",
    "kernrol": "Huidige rol/profiel",
    "zijn": "Wie IS deze persoon? Persoonlijkheid, werkstijl, karakter, samenwerking, communicatie, omgang met druk.",
    "willen": "Wat WILT deze persoon en wat niet? Drijfveren, motivatie, ambities, wat zoekt iemand in werk.",
    "kunnen": "Wat KAN deze persoon en wat (nog) niet? Hard/soft skills, leervermogen, opleiding, ervaring, beschikbaarheid/locatie, én aandachtspunten.",
    "dossier_compleetheid": <getal 0-100>,
    "vervolgvragen": ["Max 5 vragen aan kandidaat"],
    "stellingen": ["5 stellingen voor 1-4 schaal"]
}}

TEKST:
{tekst}"""

PROFIEL_WERKGEVERSVRAAG_PROMPT = """Maak een profiel van deze werkgeversvraag in JSON.
Duidelijke taal (B1), actief en specifiek. Focus op TYPE PERSOON.
Blijf bij de feiten. Wees streng bij dossier_compleetheid (0-100).

Het profiel heeft 3 pijlers:
1. ZIJN — Wat voor PERSOON moet de kandidaat zijn? Persoonlijkheid, karakter, teamfit, cultuur, werksfeer, verborgen behoeften qua type persoon. (2-4 zinnen)
2. WILLEN — Wat moet de kandidaat WILLEN? Waarden, drijfveren, gewenste motivatie, wat biedt het bedrijf aan groei, begeleiding en ontwikkeling. (2-4 zinnen)
3. KUNNEN — Wat moet de kandidaat KUNNEN? Must-have en nice-to-have skills, taken, verantwoordelijkheden, belangrijkste taak, werktijden, praktische zaken, én aandachtspunten/risico's. (2-4 zinnen)

{{
    "titel": "Naam baan",
    "organisatie": "Bedrijfsnaam",
    "zijn": "Wat voor PERSOON moet de kandidaat zijn? Persoonlijkheid, karakter, teamfit, cultuur, werksfeer, verborgen behoeften.",
    "willen": "Wat moet de kandidaat WILLEN? Waarden, drijfveren, ambitie, ontwikkeling, wat biedt het bedrijf aan groei en begeleiding.",
    "kunnen": "Wat moet de kandidaat KUNNEN? Must-have en nice-to-have skills, taken, verantwoordelijkheden, werktijden, praktische zaken, én aandachtspunten.",
    "dossier_compleetheid": <getal 0-100>,
    "vervolgvragen": ["Max 5 vragen AAN WERKGEVER (bijv. 'Wat is het budget?')"],
    "stellingen": ["5 stellingen voor 1-4 schaal"]
}}

WERKGEVERSVRAAG:
{tekst}"""

EVALUEER_PROFIEL_PROMPT = """Je bent een expert in recruitment. Beoordeel de VOLLEDIGHEID van dit profiel.
Zijn er nog gaten in de informatie die ingevuld moeten worden om een perfecte match te maken?

Voor WERKGEVERSVRAGEN: Richt de vervolgvragen ALTIJD aan de WERKGEVER/RECRUITER (bijv. 'Wat is het budget?' of 'Hoe ziet het team eruit?' en NIET 'Kun jij dit?').
Voor KANDIDAATPROFIELEN: Richt de vervolgvragen aan de KANDIDAAT.
Bedenk maximaal 5 duidelijke vragen die we nog aan de gebruiker kunnen stellen. Zo krijgen we de informatie die we nog missen om een echt goede match te maken.
Zorg dat de vragen makkelijk te beantwoorden zijn.
Geef je antwoord in precies deze JSON-opmaak (geen extra tekst eromheen).

{{
    "volledigheid_score": <getal van 0 tot 100, waarbij 100 betekent dat alles erin staat>,
    "vervolgvragen": ["Duidelijke vraag aan de werkgever 1", "Vraag 2", "...(maximaal 5 vragen)"]
}}

PROFIEL:
{profiel_json}"""

VERRIJK_KANDIDAAT_PROMPT = """Je hebt al een profiel van een kandidaat gemaakt. Nu heb je nieuwe informatie gekregen via extra vragen.
Voeg deze nieuwe informatie en de oude informatie samen tot één nieuw en beter profiel.

Aanwijzingen:
- DE NIEUWE ANTWOORDEN ZIJN LEIDEND. Als een antwoord informatie geeft die in het bestaande profiel nog op "Onbekend" of "Niet genoemd" staat, mOET je dit veld nu bijwerken met de nieuwe informatie.
- Verwerk de nieuwe informatie soepel in het hele profiel. Maak er geen los stukje van onderaan, maar weef het erdoorheen.
- Gebruik ALTIJD begrijpelijke en duidelijke taal (B1-niveau). Spreek de gebruiker direct aan.
- Verhoog de score voor de dossiercompleetheid (dossier_compleetheid) aanzienlijk als de antwoorden belangrijke gaten vullen.
- Voeg nieuwe inzichten toe over iemands karakter (zijn), drijfveren (willen) en vaardigheden (kunnen) op basis van de antwoorden.
- Bedenk nieuwe vervolgvragen voor de kandidaat als er nog steeds belangrijke zaken ontbreken (maximaal 5).
- Bedenk 5 nieuwe prikkelende stellingen (stellingen) die de kandidaat kan beoordelen op een 4-punts schaal om extra informatie te verzamelen.
- Als het profiel nu helemaal compleet is, mogen de lijstjes met vervolgvragen en stellingen leeg blijven of een lege lijst zijn [].

BESTAAND PROFIEL:
{profiel_json}

NIEUWE ANTWOORDEN (vraag → antwoord):
{antwoorden_json}

OORSPRONKELIJKE TEKST (voor de zekerheid):
{ruwe_tekst}

Maak het volledige bijgewerkte profiel in precies dezelfde JSON-opmaak als het eerste profiel."""

VERRIJK_WERKGEVERSVRAAG_PROMPT = """Je hebt al een profiel gemaakt van een werkgeversvraag. Nu heb je nieuwe informatie gekregen via extra vragen.
Voeg deze nieuwe informatie en de oude informatie samen tot één nieuw en beter profiel.

Aanwijzingen:
- DE NIEUWE ANTWOORDEN ZIJN LEIDEND. Als een antwoord informatie geeft die in het bestaande profiel nog op "Onbekend" of "Niet genoemd" staat, MOET je dit veld nu bijwerken met de nieuwe informatie.
- Verwerk de nieuwe informatie soepel in het hele verhaal. Maak er geen los blokje van, maar weef het erdoorheen.
- Gebruik ALTIJD heldere, begrijpelijke taal (B1-niveau). Spreek de lezer direct aan.
- Verhoog de score voor de dossiercompleetheid (dossier_compleetheid) aanzienlijk als de antwoorden belangrijke gaten vullen.
- Voeg nieuwe inzichten toe over het gezochte karakter (zijn), de gewenste motivatie (willen) en benodigde vaardigheden (kunnen).
- Bedenk nieuwe vervolgvragen voor de werkgever/recruiter als er nog steeds belangrijke zaken ontbreken (maximaal 5). Stel deze vragen VRAAGSTELLEND aan de WERKGEVER (bijv. 'Wat zijn de exacte werktijden?' en NIET 'Wanneer kun jij werken?').
- Bedenk 5 nieuwe prikkelende stellingen (stellingen) die de werkgever kan beoordelen op een 4-punts schaal om extra informatie te verzamelen.
- Als het profiel nu helemaal compleet is, mogen de lijstjes met vervolgvragen en stellingen leeg blijven.

BESTAAND PROFIEL:
{profiel_json}

NIEUWE ANTWOORDEN (vraag → antwoord):
{antwoorden_json}

OORSPRONKELIJKE TEKST (voor de zekerheid):
{ruwe_tekst}

Maak het volledige bijgewerkte profiel in precies dezelfde JSON-opmaak als het eerste profiel."""

VERWERK_MATCH_FEEDBACK_PROMPT = """Je hebt onlangs een match beoordeeld. De recruiter heeft nu feedback gegeven op deze match.
Gebruik deze feedback om het profiel van de KANDIDAAT verder te verrijken en aan te scherpen.

KANDIDAATPROFIEL (HUIDIG):
{profiel_json}

MATCH RESULTAAT:
{match_json}

RECRUITER FEEDBACK:
{feedback_tekst}

FEEDBACK CATEGORIEËN (indien aanwezig):
De feedback kan voorafgegaan worden door [Categorieën: ...]. Dit geeft aan welk TYPE feedback het is:
- "Skills kloppen niet" → pas 'kunnen' aan
- "Verkeerd senioriteitsniveau" → pas 'kernrol' en 'kunnen' aan
- "Cultuur-mismatch" → pas 'zijn' aan
- "Betere match dan verwacht" → verhoog 'dossier_compleetheid', voeg positieve inzichten toe
- "Ontbrekende ervaring" → pas 'kunnen' aan
- "Motivatie verkeerd ingeschat" → pas 'willen' en 'zijn' aan

Aanwijzingen:
0. Gebruik ALTIJD heldere, begrijpelijke taal (B1-niveau). Geen wollig taalgebruik of HR-jargon.
1. Extraheer nieuwe feiten, vaardigheden of karaktereigenschappen uit de feedback.
2. Update relevante velden in het profiel: pas 'zijn', 'willen' en 'kunnen' aan waar nodig.
3. Als de feedback aangeeft dat iets NIET klopt, pas dit dan aan.
4. Verhoog de 'dossier_compleetheid' als de feedback waardevolle nieuwe informatie bevat.
5. Behoud alle bestaande informatie die niet door de feedback wordt tegengesproken.

Return het VOLLEDIG BIJGEWERKTE KANDIDAATPROFIEL in exact dezelfde JSON-opmaak als het origineel."""

VERWERK_WERKGEVER_FEEDBACK_PROMPT = """Je hebt onlangs een match beoordeeld. De recruiter heeft feedback gegeven op deze match.
Gebruik deze feedback om het profiel van de WERKGEVERSVRAAG verder te verrijken en aan te scherpen.

WERKGEVERSVRAAGPROFIEL (HUIDIG):
{profiel_json}

MATCH RESULTAAT:
{match_json}

RECRUITER FEEDBACK:
{feedback_tekst}

Aanwijzingen:
0. Gebruik ALTIJD heldere, begrijpelijke taal (B1-niveau). Geen wollig taalgebruik of HR-jargon.
1. Extraheer inzichten over teamcultuur, gezochte persoonlijkheid en verborgen behoeften uit de feedback.
2. Als de feedback aangeeft dat de werkgever eigenlijk iets anders zoekt (bijv. "meer hands-on", "juist geen leidinggevende"), pas dan 'zijn' en 'kunnen' aan.
3. Update 'kunnen' als de feedback nieuwe informatie geeft over gewenste skills of taken.
4. Verhoog de 'dossier_compleetheid' als de feedback waardevolle nieuwe informatie over de werkgeversvraag bevat.
5. Behoud alle bestaande informatie die niet door de feedback wordt tegengesproken.

Return het VOLLEDIG BIJGEWERKTE WERKGEVERSVRAAGPROFIEL in exact dezelfde JSON-opmaak als het origineel."""

REFLECTIE_PROMPT = """Analyseer de verzamelde feedback-teksten van een recruiter op matches.
Vat samen wat de recruiter belangrijk vindt en welk type kandidaat hoog of laag scoort.

FEEDBACK-TEKSTEN:
{feedback_teksten}

Geef je antwoord in exact deze JSON-opmaak:
{{
    "samenvatting": "Korte samenvatting van wat de recruiter waardeert en wat niet (2-4 zinnen, B1-niveau)",
    "sterke_voorkeur": ["Lijstje van eigenschappen of kwaliteiten die de recruiter duidelijk prefereert"],
    "vermijden": ["Lijstje van eigenschappen of kenmerken die de recruiter liever niet ziet"]
}}"""

# --- Match-modi ---
# Elke modus definieert welke stappen worden uitgevoerd:
#   stappen: ["kern"] = alleen kern-prompt, ["kern", "verdieping"] = kern + verdieping

QUICK_SCAN_MODEL = os.getenv("QUICK_SCAN_MODEL", "qwen3:4b")
STANDAARD_MODEL = os.getenv("STANDAARD_MODEL", "qwen3:8b")

MATCH_MODI = {
    "quick_scan": {
        "label": "Quick scan",
        "beschrijving": "Snel overzicht met alleen de kern-match (8 velden, snel model)",
        "num_predict": 2048,
        "num_ctx": 8192,
        "temperature": 0.1,
        "model_override": QUICK_SCAN_MODEL,
        "max_tekst_lengte": 1500,
        "think": False,
        "stappen": ["kern"],
        "prompt": KERN_MATCH_PROMPT,
    },
    "standaard": {
        "label": "Standaard",
        "beschrijving": "Kern-match + verdieping in twee stappen (betrouwbaarder dan alles tegelijk)",
        "num_predict": -1,
        "num_ctx": 8192,
        "temperature": 0.1,
        "model_override": STANDAARD_MODEL,
        "max_tekst_lengte": None,
        "think": False,
        "stappen": ["kern", "verdieping"],
        "prompt": KERN_MATCH_PROMPT,
    },
    "diepte_analyse": {
        "label": "Diepte-analyse",
        "beschrijving": "Kern-match + verdieping met thinking mode (27b model, diepere analyse)",
        "num_predict": -1,
        "num_ctx": 8192,
        "temperature": 0.1,
        "model_override": None,
        "max_tekst_lengte": None,
        "think": True,
        "stappen": ["kern", "verdieping"],
        "prompt": KERN_MATCH_PROMPT,
    },
}
