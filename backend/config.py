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
Noem altijd SPECIFIEK gedrag of een CONCRETE vaardigheid — geen algemeenheden.

BELANGRIJK VOOR HET SYSTEEM:
Je antwoord moet ALTIJD uitsluitend een kloppend JSON-object zijn. Gebruik precies de indeling die wordt gevraagd. Laat geen velden weg. Anders kan het systeem het niet verwerken.
"""

# --- Gesplitste Match-prompts ---
# Kern-prompt: de essentie van de match — direct en actiegericht
KERN_MATCH_PROMPT = """Bekijk de match tussen deze kandidaat en de werkgeversvraag.

Beoordeel de dossiercompleetheid:
- HOOG: Genoeg info voor goede inschatting.
- GEMIDDELD: Kleine details missen.
- LAAG: Belangrijke info ontbreekt — stel vervolgvragen.

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

# --- Anthropic (Claude) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# --- Prompts voor Profiel-extractie ---
_PERSPECTIEF_KANDIDAAT = """Vanuit de KANDIDAAT:
1. ZIJN — Wie IS deze persoon? Werkstijl, karakter, samenwerking, omgang met druk.
2. WILLEN — Wat WILT deze persoon? Drijfveren, ambities, wat zoekt iemand in werk.
3. KUNNEN — Wat KAN deze persoon en wat NIET? Skills, leervermogen, ervaring, beschikbaarheid, aandachtspunten."""

_PERSPECTIEF_WERKGEVER = """Vanuit de WERKGEVER (wat voor kandidaat zoeken we?):
1. ZIJN — Wat voor persoon moet het zijn? Karakter, teamfit, cultuur, verborgen behoeften.
2. WILLEN — Wat moet de kandidaat willen? Waarden, motivatie, wat biedt het bedrijf aan groei.
3. KUNNEN — Wat moet de kandidaat kunnen? Skills, taken, werktijden, aandachtspunten."""

_JSON_KANDIDAAT = """{{"naam": "...", "kernrol": "...", "zijn": "...", "willen": "...", "kunnen": "...", "dossier_compleetheid": 0, "vervolgvragen": ["..."], "stellingen": ["..."]}}"""
_JSON_WERKGEVER = """{{"titel": "...", "organisatie": "...", "zijn": "...", "willen": "...", "kunnen": "...", "dossier_compleetheid": 0, "vervolgvragen": ["..."], "stellingen": ["..."]}}"""

_PROFIEL_PROMPT = """Maak een profiel in JSON. Wees streng bij dossier_compleetheid (0-100).

3 pijlers (elk 2-4 zinnen):
{perspectief}

{json_template}

TEKST:
{tekst}"""

PROFIEL_KANDIDAAT_PROMPT = _PROFIEL_PROMPT.replace("{perspectief}", _PERSPECTIEF_KANDIDAAT).replace("{json_template}", _JSON_KANDIDAAT)
PROFIEL_WERKGEVERSVRAAG_PROMPT = _PROFIEL_PROMPT.replace("{perspectief}", _PERSPECTIEF_WERKGEVER).replace("{json_template}", _JSON_WERKGEVER)

EVALUEER_PROFIEL_PROMPT = """Beoordeel de VOLLEDIGHEID van dit profiel.
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

_VERRIJK_PROFIEL_PROMPT = """Voeg nieuwe antwoorden samen met het bestaande profiel.

Regels:
- Nieuwe antwoorden zijn LEIDEND boven "Onbekend" waarden.
- Weef door het hele profiel — geen los blokje.
- Verhoog dossier_compleetheid als gaten worden gevuld.
- Update zijn, willen en kunnen op basis van de antwoorden.
- Bedenk vervolgvragen AAN DE {doelgroep} als er info mist (max 5).
- Bedenk 5 stellingen (4-punts schaal). Leeg als profiel compleet is.

BESTAAND PROFIEL:
{profiel_json}

NIEUWE ANTWOORDEN:
{antwoorden_json}

OORSPRONKELIJKE TEKST:
{ruwe_tekst}

Return het volledige bijgewerkte profiel in dezelfde JSON-opmaak."""

VERRIJK_KANDIDAAT_PROMPT = _VERRIJK_PROFIEL_PROMPT.replace("{doelgroep}", "KANDIDAAT")
VERRIJK_WERKGEVERSVRAAG_PROMPT = _VERRIJK_PROFIEL_PROMPT.replace("{doelgroep}", "WERKGEVER")

_FEEDBACK_CATEGORIEEN_KANDIDAAT = """FEEDBACK CATEGORIEËN:
- "Skills kloppen niet" → pas 'kunnen' aan
- "Verkeerd senioriteitsniveau" → pas 'kernrol' en 'kunnen' aan
- "Cultuur-mismatch" → pas 'zijn' aan
- "Betere match dan verwacht" → verhoog 'dossier_compleetheid'
- "Ontbrekende ervaring" → pas 'kunnen' aan
- "Motivatie verkeerd ingeschat" → pas 'willen' en 'zijn' aan"""

_FEEDBACK_CATEGORIEEN_WERKGEVER = """FEEDBACK CATEGORIEËN:
- Werkgever zoekt ander type persoon → pas 'zijn' en 'kunnen' aan
- Andere skills gewenst → pas 'kunnen' aan"""

_VERWERK_FEEDBACK_PROMPT = """Verwerk recruiter-feedback in het {profiel_label}.

{profiel_type_upper}PROFIEL (HUIDIG):
{profiel_json}

MATCH RESULTAAT:
{match_json}

RECRUITER FEEDBACK:
{feedback_tekst}

{categorie_mapping}

Regels:
1. Extraheer nieuwe feiten uit de feedback.
2. Update zijn, willen en kunnen waar nodig.
3. Corrigeer wat niet klopt.
4. Verhoog dossier_compleetheid bij waardevolle info.
5. Behoud wat niet wordt tegengesproken.

Return het VOLLEDIGE bijgewerkte profiel in dezelfde JSON-opmaak."""

VERWERK_MATCH_FEEDBACK_PROMPT = _VERWERK_FEEDBACK_PROMPT.replace(
    "{profiel_label}", "kandidaatprofiel"
).replace("{profiel_type_upper}", "KANDIDAAT").replace(
    "{categorie_mapping}", _FEEDBACK_CATEGORIEEN_KANDIDAAT
)

VERWERK_WERKGEVER_FEEDBACK_PROMPT = _VERWERK_FEEDBACK_PROMPT.replace(
    "{profiel_label}", "werkgeversvraagprofiel"
).replace("{profiel_type_upper}", "WERKGEVERSVRAAG").replace(
    "{categorie_mapping}", _FEEDBACK_CATEGORIEEN_WERKGEVER
)

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
