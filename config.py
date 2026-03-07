import os

ICLOUD_BASE = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs"
)

KANDIDATEN_DIR = os.path.join(ICLOUD_BASE, "kandidaten")
WERKGEVERSVRAGEN_DIR = os.path.join(ICLOUD_BASE, "werkgeversvragen")
RAPPORT_DIR = os.path.join(ICLOUD_BASE, "match-rapporten")

# Backwards compatibility names
CV_DIR = KANDIDATEN_DIR
VACATURE_DIR = WERKGEVERSVRAGEN_DIR

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3.5:27b"
PROFIEL_MODEL = "qwen3:8b"

SYSTEM_PROMPT = """Je bent een vooruitstrevende matchmaker en talent-expert die kandidaten en werkgeversvragen verbindt.
Je focus ligt sterk op potentieel, persoonlijke eigenschappen, karakter en drijfveren, in plaats van een rigide check op diploma's of exacte werkervaring.
Je doel is om verrassende, inspirerende matches te maken: kandidaten tippen voor rollen die ze zelf misschien niet hadden overwogen, en werkgevers wijzen op talent dat ze normaal over het hoofd zouden zien.
Wees creatief, objectief en eerlijk in het toekennen van het matchpercentage, waarbij cultuur- en persoonlijkheidsfit zwaar wegen."""

MATCH_PROMPT = """Analyseer de match tussen dit kandidaatprofiel en deze werkgeversvraag met een focus op persoonlijkheid en potentieel.
Geef een match percentage van 0 tot 100 gebaseerd op karakter, drijfveren en potentieel.

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Geef je analyse in exact dit JSON-format (geen andere tekst, alleen JSON):
{{
  "match_percentage": <getal van 0 tot 100>,
  "matchende_punten": ["punt1", "punt2"],
  "ontbrekende_punten": ["punt1", "punt2"],
  "onderbouwing": "korte toelichting waarom deze persoon goed zou passen qua karakter en drijfveren"
}}"""

# --- Prompts voor Profiel-extractie ---
PROFIEL_KANDIDAAT_PROMPT = """Extraheer een gestructureerd profiel uit deze kandidaattekst.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON). Focus hierbij nadrukkelijk op wie de persoon is en wat hun kwaliteiten zijn, naast hun ervaring. Focus op potentieel.
{{
    "naam": "Naam Kandidaat",
    "kernrol": "Primaire huidige rol of overkoepelend profiel",
    "persoonlijkheid": ["lijst", "van", "karaktereigenschappen en persoonskenmerken"],
    "kwaliteiten": ["lijst", "van", "sterke punten en talenten"],
    "drijfveren": ["lijst", "van", "wat deze persoon motiveert of zoekt"],
    "hard_skills": ["lijst", "van", "relevante hard skills"],
    "soft_skills": ["lijst", "van", "soft skills"],
    "opleiding_en_ervaring_samenvatting": "Korte samenvatting van achtergrond (niet leidend voor match)"
}}

KANDIDAATTEKST:
{tekst}"""

PROFIEL_WERKGEVERSVRAAG_PROMPT = """Extraheer een gestructureerd profiel uit deze werkgeversvraag.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON). Focus niet alleen op de harde eisen, maar vooral op het type persoon dat gezocht wordt, de cultuur en de benodigde eigenschappen.
{{
    "titel": "Functietitel",
    "organisatie": "Naam Organisatie",
    "gezochte_persoonlijkheid": ["lijst", "van", "gewenste karaktereigenschappen"],
    "benodigde_kwaliteiten": ["lijst", "van", "belangrijkste talenten/kwaliteiten voor succes"],
    "team_en_cultuur": "Korte omschrijving van werkomgeving en cultuur",
    "must_have_skills": ["lijst", "van", "echt onmisbare skills"],
    "nice_to_have_skills": ["lijst", "van", "mooi meegenomen, maar trainbare skills"],
    "belangrijkste_taak": "Wat deze persoon vooral gaat doen"
}}

WERKGEVERSVRAAG:
{tekst}"""

# --- Match-modi ---

# Kleiner/sneller model voor quick scan. Zet op None om hetzelfde model te gebruiken.
QUICK_SCAN_MODEL = "qwen3:8b"

MATCH_MODI = {
    "quick_scan": {
        "label": "Quick scan",
        "beschrijving": "Snel overzicht met globale match (verkort input, sneller model)",
        "num_predict": 256,
        "num_ctx": 4096,
        "temperature": 0.4,
        "model_override": QUICK_SCAN_MODEL,  # qwen3:8b — ~3-4x sneller
        "max_tekst_lengte": 1500,  # Maximale lengte CV/vacature tekst in karakters
        "prompt": """Match dit kandidaatprofiel met dit werkgeversvraagprofiel. Focus zwaar op een verrassende match qua persoonskenmerken, kwaliteiten en potentieel.
Het match_percentage moet een getal tussen 0 en 100 zijn, gebaseerd op karakter en potentieel.

KANDIDAATPROFIEL (samengevat):
{cv_tekst}

WERKGEVERSVRAAGPROFIEL (samengevat):
{vacature_tekst}

JSON:
{{
  "match_percentage": <getal van 0 tot 100>,
  "matchende_punten": ["belangrijkste match qua persoonlijkheid/kwaliteit"],
  "ontbrekende_punten": ["belangrijkste gemis"],
  "onderbouwing": "één zin waarom dit verfrissend of onverwacht een goede match kan zijn"
}}""",
    },
    "diepte_analyse": {
        "label": "Diepte-analyse",
        "beschrijving": "Uitgebreide analyse met gedetailleerde onderbouwing",
        "num_predict": 1024,
        "num_ctx": 8192,
        "temperature": 0.2,
        "model_override": None,
        "max_tekst_lengte": None,  # Geen limiet
        "prompt": """Maak een grondige analyse van de match tussen dit kandidaatprofiel en dit werkgeversvraagprofiel.
Focus sterk op *out-of-the-box* denken: zoek de fit op basis van persoonlijkheid, drijfveren, zachte skills en overdraagbare kwaliteiten. Opleiding en exacte functietitels uit het verleden zijn ondergeschikt aan potentieel.
Laat zien waarom deze persoon in deze baan zou floreren, ook als het geen voor de hand liggende stap is. Inspireer de werkgever om breder te kijken.
Het match_percentage moet een getal tussen 0 en 100 zijn en weegt het zwaarst op personality en potentieel.

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Antwoord in exact dit JSON-format (geen andere tekst):
{{
  "match_percentage": <getal van 0 tot 100>,
  "matchende_punten": ["gedetailleerd punt 1 (bijv. gedeelde kernwaarde)", "punt 2 (overdraagbare skill)", "..."],
  "ontbrekende_punten": ["gedetailleerd punt 1 (bijv. kennis die nog opgedaan moet worden)", "..."],
  "onderbouwing": "uitgebreide toelichting: waarom is dit een interessante match qua karakter en passie? Wat voegt deze onverwachte kandidaat toe?"
}}""",
    },
}
