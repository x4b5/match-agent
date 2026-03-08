import os

ICLOUD_BASE = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs"
)

KANDIDATEN_DIR = os.path.join(ICLOUD_BASE, "kandidaten")
WERKGEVERSVRAGEN_DIR = os.path.join(ICLOUD_BASE, "werkgeversvragen")
RAPPORT_DIR = os.path.join(ICLOUD_BASE, "match-rapporten")
CACHE_DIR = os.path.join(ICLOUD_BASE, ".match_cache")

# Backwards compatibility names
CV_DIR = KANDIDATEN_DIR
VACATURE_DIR = WERKGEVERSVRAGEN_DIR

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3.5:27b"
PROFIEL_MODEL = "qwen3:8b"

SYSTEM_PROMPT = """Je bent een vooruitstrevende matchmaker en talent-expert die kandidaten en werkgeversvragen verbindt.
Je focus ligt sterk op potentieel, persoonlijke eigenschappen, karakter en drijfveren, in plaats van een rigide check op diploma's of exacte werkervaring.
Je doel is om verrassende, inspirerende matches te maken: kandidaten tippen voor rollen die ze zelf misschien niet hadden overwogen, en werkgevers wijzen op talent dat ze normaal over het hoofd zouden zien.
Wees creatief, objectief en eerlijk in het toekennen van het matchpercentage, waarbij cultuur- en persoonlijkheidsfit zwaar wegen.
BELANGRIJK: Gebruik GEEN DISC-terminologie (Dominantie, Invloed, Stabiliteit, Conformisme) of kleuren-modellen; dit is niet wetenschappelijk onderbouwd. Focus op concrete talenten en kwaliteiten.

BEOORDELING BETROUWBAARHEID: 
Geef bij elke match een betrouwbaarheidsscore:
- HOOG: Er is voldoende detail over zowel de kandidaat als de vacature om een gefundeerde match te maken op persoonlijkheid en potentieel.
- GEMIDDELD: Er zijn enkele aannames nodig of bepaalde nuances ontbreken.
- LAAG: Essentiële informatie over karakter, drijfveren of specifieke werkstijl ontbreekt. Benoem in dit geval concrete 'vervolgvragen' die gesteld moeten worden om de match te verifiëren."""

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
  "overbruggings_advies": ["Concreet advies per ontbrekend punt: bijv. 'Volg cursus X voor skill Y'", "..."],
  "verrassings_element": "Waarom zou je deze match niet verwachten, maar is het toch een goede fit?",
  "cultuur_fit": "waarom de persoon qua karakter en waarden wel of niet past",
  "onderbouwing": "korte toelichting waarom deze persoon goed zou passen qua karakter en drijfveren",
  "personality_axes": {{
    "Analytisch": <getal 0-100>,
    "Sociaal": <getal 0-100>,
    "Creatief": <getal 0-100>,
    "Gestructureerd": <getal 0-100>,
    "Ondernemend": <getal 0-100>
  }},
  "match_betrouwbaarheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["kritieke vraag 1 om dossier completer te maken", "vraag 2"]
}}"""

# --- Prompts voor Profiel-extractie ---
PROFIEL_KANDIDAAT_PROMPT = """Extraheer een gestructureerd profiel uit deze kandidaattekst.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON).

Belangrijke instructies:
- Focus nadrukkelijk op wie de persoon IS, niet alleen wat ze GEDAAN hebben.
- Leid impliciete kwaliteiten af uit de werkgeschiedenis. Voorbeeld: iemand die 10 jaar in de horeca werkte is waarschijnlijk stressbestendig, gastvrij, en een snelle multitasker — ook al staat dat niet letterlijk in de tekst.
- Denk na over de onderliggende motivatie: wat drijft deze persoon écht? Zekerheid? Variatie? Mensen helpen? Autonomie?
- Beschrijf een ideale werkdag die past bij deze persoon.
- Gebruik GEEN DISC-kleuren of termen in je analyse.

{{
    "naam": "Naam Kandidaat",
    "kernrol": "Primaire huidige rol of overkoepelend profiel",
    "persoonlijkheid": ["lijst", "van", "karaktereigenschappen en persoonskenmerken"],
    "kwaliteiten": ["lijst", "van", "sterke punten en talenten"],
    "impliciete_kwaliteiten": ["lijst", "van", "verborgen kwaliteiten afgeleid uit werkervaring of hobby's — dingen die niet letterlijk genoemd worden maar wel logisch zijn"],
    "drijfveren": ["lijst", "van", "wat deze persoon motiveert of zoekt"],
    "onderliggende_motivatie": "Wat drijft deze persoon in de kern? (bijv. zekerheid, mensen helpen, creatieve vrijheid, erkenning, groei)",
    "ideale_werkdag": "Beschrijf in 2-3 zinnen hoe een ideale werkdag eruitziet voor deze persoon",
    "werkstijl": "Hoe de persoon te werk gaat (bijv. zelfstandig, teamplayer, hands-on)",
    "ambities_en_leerdoelen": ["lijst", "van", "wat de persoon wil bereiken of nog wil leren"],
    "gewenste_bedrijfscultuur": "In wat voor soort omgeving de persoon goed gedijt",
    "hobby_en_interesses": ["lijst", "van", "relevante bezigheden die karakter tonen"],
    "hard_skills": ["lijst", "van", "relevante hard skills"],
    "soft_skills": ["lijst", "van", "soft skills"],
    "beschikbaarheid_en_locatie": "Praktische zaken (indien genoemd in tekst)",
    "opleiding_en_ervaring_samenvatting": "Korte samenvatting van achtergrond (niet leidend voor match)",
    "profiel_betrouwbaarheid": <getal 0-100 gebaseerd op volledigheid brontekst>,
    "vervolgvragen": ["maximaal 5 vragen om ontbrekende info aan te vullen"]
}}

KANDIDAATTEKST:
{tekst}"""

PROFIEL_WERKGEVERSVRAAG_PROMPT = """Extraheer een gestructureerd profiel uit deze werkgeversvraag.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON).

Belangrijke instructies:
- Focus niet alleen op de harde eisen, maar vooral op het TYPE PERSOON dat gezocht wordt.
- Schets een ideale kandidaat-persona: hoe ziet de perfecte persoon eruit qua karakter en houding?
- Denk na over verborgen behoeften: wat staat niet in de vacature maar is wel cruciaal voor succes in deze rol?

{{
    "titel": "Functietitel",
    "organisatie": "Naam Organisatie",
    "organisatiewaarden": ["lijst", "van", "kernwaarden van het bedrijf/team"],
    "gezochte_persoonlijkheid": ["lijst", "van", "gewenste karaktereigenschappen"],
    "benodigde_kwaliteiten": ["lijst", "van", "belangrijkste talenten/kwaliteiten voor succes"],
    "ideale_kandidaat_persona": "Schets in 2-3 zinnen het type mens dat hier would floreren — niet qua CV maar qua karakter en houding",
    "verborgen_behoeften": ["lijst", "van", "belangrijke zaken die niet expliciet in de vacature staan maar wel cruciaal zijn voor succes"],
    "team_en_cultuur": "Korte omschrijving van werkomgeving, cultuur en sfeer",
    "ontwikkel_en_doorgroeimogelijkheden": "Wat het bedrijf te bieden heeft aan potentieel (bijv. opleiding/training)",
    "begeleiding_en_inwerkperiode": "Hoe nieuwe collega's worden opgevangen (vooral als ze uit een andere sector komen)",
    "must_have_skills": ["lijst", "van", "echt onmisbare skills"],
    "nice_to_have_skills": ["lijst", "van", "mooi meegenomen, maar trainbare skills"],
    "werktijden_en_omstandigheden": "Praktische zaken t.a.v. werktijden of fysieke omstandigheden",
    "belangrijkste_taak": "Wat deze persoon vooral gaat doen",
    "profiel_betrouwbaarheid": <getal 0-100 gebaseerd op volledigheid vacaturetekst>,
    "vervolgvragen": ["maximaal 5 vragen om context te verduidelijken"]
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
        "num_predict": 512,
        "num_ctx": 8192,
        "temperature": 0.4,
        "model_override": QUICK_SCAN_MODEL,  # qwen3:8b — ~3-4x sneller
        "max_tekst_lengte": 3000,  # Maximale lengte CV/vacature tekst in karakters
        "think": False,
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
  "overbruggings_advies": ["Advies hoe gemis te overbruggen"],
  "verrassings_element": "Waarom is dit een onverwachte maar interessante match?",
  "onderbouwing": "één zin waarom dit verfrissend of onverwacht een goede match kan zijn",
  "personality_axes": {{
    "Analytisch": <getal 0-100>,
    "Sociaal": <getal 0-100>,
    "Creatief": <getal 0-100>,
    "Gestructureerd": <getal 0-100>,
    "Ondernemend": <getal 0-100>
  }},
  "match_betrouwbaarheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["vraag 1 om dossier completer te maken"]
}}""",
    },
    "diepte_analyse": {
        "label": "Diepte-analyse",
        "beschrijving": "Uitgebreide analyse met gedetailleerde onderbouwing (denkmodus aan)",
        "num_predict": 1536,
        "num_ctx": 8192,
        "temperature": 0.2,
        "model_override": None,
        "max_tekst_lengte": None,  # Geen limiet
        "think": True,  # Laat het model nadenken voor diepere analyse
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
  "overbruggings_advies": ["Concreet advies per ontbrekend punt over hoe dit te overbruggen (cursus, training, begeleiding)", "..."],
  "verrassings_element": "Waarom zou je deze match niet verwachten, maar is het toch een goede fit? Wat maakt het bijzonder?",
  "gespreksstarters": ["Concrete interviewvraag 1 die de recruiter kan stellen om deze match te verkennen", "Vraag 2", "Vraag 3"],
  "risico_mitigatie": "Hoe kunnen de ontbrekende punten worden opgelost? Welke begeleiding of training is nodig?",
  "gedeelde_waarden": ["punt 1 (welke waarden komen overeen?)", "..."],
  "groeipotentieel": "Waar kan deze kandidaat nog in groeien bij deze werkgever?",
  "cultuur_fit": "Waarom passen ze bij elkaar qua karakter en bedrijfscultuur?",
  "aandachtspunten": "Waar moet extra begeleiding op worden ingezet?",
  "boodschap_aan_kandidaat": "Een korte, motiverende boodschap gericht aan de kandidaat zelf: waarom is deze rol iets voor jou? Spreek de kandidaat direct aan.",
  "onderbouwing": "uitgebreide toelichting: waarom is dit een interessante match qua karakter and passie? Wat voegt deze onverwachte kandidaat toe?",
  "personality_axes": {{
    "Analytisch": <getal 0-100>,
    "Sociaal": <getal 0-100>,
    "Creatief": <getal 0-100>,
    "Gestructureerd": <getal 0-100>,
    "Ondernemend": <getal 0-100>
  }},
  "match_betrouwbaarheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["Diepgaande vraag 1 om missende info boven water te krijgen", "vraag 2"]
}}""",
    },
}
