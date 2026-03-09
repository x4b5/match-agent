import os

ICLOUD_BASE = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/matchflix"
)

KANDIDATEN_DIR = os.path.join(ICLOUD_BASE, "kandidaten")
WERKGEVERSVRAGEN_DIR = os.path.join(ICLOUD_BASE, "werkgeversvragen")
RAPPORT_DIR = os.path.join(ICLOUD_BASE, "match-rapporten")
CACHE_DIR = os.path.join(ICLOUD_BASE, ".match_cache")

# Backwards compatibility names
CV_DIR = KANDIDATEN_DIR
VACATURE_DIR = WERKGEVERSVRAGEN_DIR

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "qwen3.5:27b"
PROFIEL_MODEL = "qwen3:8b"
EMBEDDING_MODEL = "nomic-embed-text"

SYSTEM_PROMPT = """Je bent een vooruitstrevende matchmaker en talent-expert die kandidaten en werkgeversvragen verbindt.
Je focus ligt sterk op potentieel, persoonlijke eigenschappen, karakter en drijfveren, in plaats van een rigide check op diploma's of exacte werkervaring.
Je doel is om verrassende, inspirerende matches te maken: kandidaten tippen voor rollen die ze zelf misschien niet hadden overwogen, en werkgevers wijzen op talent dat ze normaal over het hoofd zouden zien.
Wees creatief, objectief en eerlijk in het toekennen van het matchpercentage, waarbij cultuur- en persoonlijkheidsfit zwaar wegen.
BELANGRIJK: Gebruik GEEN DISC-terminologie (Dominantie, Invloed, Stabiliteit, Conformisme) of kleuren-modellen; dit is niet wetenschappelijk onderbouwd. Focus op concrete talenten en kwaliteiten.

BEOORDELING DOSSIERCOMPLEETHEID: 
Geef bij elke match een score voor dossiercompleetheid:
- HOOG: Er is voldoende detail over zowel de kandidaat als de vacature om een gefundeerde match te maken op persoonlijkheid en potentieel.
- GEMIDDELD: Er zijn enkele aannames nodig of bepaalde nuances ontbreken.
- LAAG: Essentiële informatie over karakter, drijfveren of specifieke werkstijl ontbreekt. Benoem in dit geval concrete 'vervolgvragen' die gesteld moeten worden om het dossier completer te maken.

JSON-INTEGRITEIT:
Je output moet ALTIJD een volledig, valide en niet-geaborteerd JSON-object zijn dat exact voldoet aan het gevraagde schema. Sla GEEN velden over. Een onvolledig JSON-object is onbruikbaar.
"""

# --- Gesplitste Match-prompts ---
# Kern-prompt: 8 velden — betrouwbaar op elk quantisatieniveau
KERN_MATCH_PROMPT = """Analyseer de match tussen dit kandidaatprofiel en deze werkgeversvraag.
Focus op persoonlijkheid, potentieel en karakter — niet op exacte diploma's of functietitels.

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Antwoord in exact dit JSON-format (geen andere tekst, alleen JSON):
{{
  "match_percentage": <getal van 0 tot 100 — weeg persoonlijkheid en potentieel het zwaarst>,
  "matchende_punten": ["max 3 concrete, specifieke punten waarop kandidaat en vraag matchen"],
  "ontbrekende_punten": ["max 3 concrete punten die ontbreken of een risico vormen"],
  "verrassings_element": "Wat maakt deze match onverwacht interessant? Eén concrete observatie.",
  "onderbouwing": "Waarom past deze persoon qua karakter en drijfveren? 2-3 zinnen.",
  "cultuur_fit": "Past deze persoon bij de bedrijfscultuur en het team? Waarom wel/niet?",
  "dossier_compleetheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["max 3 kritieke vragen om de match beter te beoordelen"]
}}"""

# Verdieping-prompt: ontvangt kern-resultaat als context, genereert extra inzichten
VERDIEPING_MATCH_PROMPT = """Je hebt zojuist een kern-analyse gemaakt van een match. Verdiep deze nu met extra inzichten.

KERN-ANALYSE:
{kern_json}

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Genereer de verdieping in exact dit JSON-format (geen andere tekst, alleen JSON):
{{
  "overbruggings_advies": ["Per ontbrekend punt: concreet advies hoe te overbruggen (cursus, training, begeleiding)"],
  "gespreksstarters": ["3 concrete interviewvragen die de recruiter kan stellen om deze match te verkennen"],
  "risico_mitigatie": "Hoe kunnen de risico's worden beperkt? Welke begeleiding is nodig?",
  "gedeelde_waarden": ["Welke waarden delen kandidaat en werkgever?"],
  "groeipotentieel": "Waar kan deze kandidaat groeien bij deze werkgever?",
  "boodschap_aan_kandidaat": "Korte, motiverende boodschap gericht aan de kandidaat: waarom is deze rol iets voor jou?",
  "match_narratief": "Een inspirerend verhaal van 3-4 zinnen dat deze match tot leven brengt.",
  "personality_axes": {{
    "Analytisch": "Kwalitatieve beschrijving mét citaat als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.",
    "Sociaal": "idem",
    "Creatief": "idem",
    "Gestructureerd": "idem",
    "Ondernemend": "idem"
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
PROFIEL_KANDIDAAT_PROMPT = """Extraheer een gestructureerd profiel uit deze kandidaattekst.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON).

Belangrijke instructies:
- Focus nadrukkelijk op wie de persoon IS, niet alleen wat ze GEDAAN hebben.
- Leid impliciete kwaliteiten af uit de werkgeschiedenis (bijv. horeca -> stressbestendig).
- KRITISCH: Blijf bij de feiten. Als informatie NIET in de tekst staat, vul dan "Niet genoemd" in of laat de lijst leeg. Hallucineer GEEN karaktereigenschappen of hobby's die niet logisch herleidbaar zijn.
- BEOORDELING DOSSIERCOMPLEETHEID: Wees EXTREEM streng!
    - 0-20: Zeer weinig info (alleen naam/snipet).
    - 20-40: Alleen korte intake-notities of 1-2 korte alinea's. Zonder CV is de score ALTIJD < 40%.
    - 40-70: Goed CV met werkervaring, maar weinig inzicht in drijfveren/karakter.
    - 70-90: Compleet dossier (CV + intake) met duidelijke persoonlijkheid en ambities.
    - 90-100: Zeer rijk dossier met expliciete details en eventuele Q&A verrijking.

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
    "dossier_compleetheid": <getal van 0 tot 100 — hoe compleet is dit dossier voor een goede match?>,
    "aandachtspunten": ["lijst van punten die extra aandacht verdienen of waar een kanttekening bij geplaatst kan worden"],
    "vervolgvragen": ["max 5 CONCRETE VRAGEN AAN DE KANDIDAAT over essentiële info die mist (bijv. drijfveren, werkstijl, beperkingen)"]
}}

BELANGRIJK: Zorg dat het veld "dossier_compleetheid" ALTIJD aanwezig is en een getal bevat. Stop pas nadat het JSON-object volledig is afgesloten met }}.

KANDIDAATTEKST:
{tekst}"""

PROFIEL_WERKGEVERSVRAAG_PROMPT = """Extraheer een gestructureerd profiel uit deze werkgeversvraag.
Zet de ruwe tekst om in exact dit JSON-format (geen andere tekst, alleen JSON).

Belangrijke instructies:
- Focus niet alleen op de harde eisen, maar vooral op het TYPE PERSOON dat gezocht wordt.
- Schets een ideale kandidaat-persona: hoe ziet de perfecte persoon eruit qua karakter en houding?
- KRITISCH: Blijf bij de feiten uit de vacaturetekst. Als informatie NIET in de tekst staat, vul dan "Niet genoemd" in. Hallucineer GEEN bedrijfscultuur die niet beschreven is.
- BEOORDELING DOSSIERCOMPLEETHEID: Wees EXTREEM streng!
    - 0-20: Zeer summiere vacature (bijv. alleen functietitel en locatie).
    - 20-40: Alleen korte notities of 1-2 korte alinea's. Zonder volledige vacaturetekst is de score ALTIJD < 40%.
    - 40-70: Harde eisen zijn duidelijk, maar cultuur, persona en groeimogelijkheden ontbreken.
    - 70-90: Goede vacaturetekst met info over taken, team en type persoon.
    - 90-100: Zeer gedetailleerde omschrijving inclusief visie, succesfactoren en inwerktraject.

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
    "dossier_compleetheid": <getal van 0 tot 100 — hoe compleet is dit dossier voor een goede match?>,
    "aandachtspunten": ["lijst van zaken die extra aandacht verdienen of waar een kanttekening bij geplaatst kan worden (reizen, ploegendienst, fysiek zwaar, etc.)"],
    "vervolgvragen": ["max 5 CONCRETE VRAGEN AAN DE WERKGEVER/RECRUITER over ontbrekende details van de rol of teamcultuur"]
}}

BELANGRIJK: Zorg dat het veld "dossier_compleetheid" ALTIJD aanwezig is en een getal bevat. Stop pas nadat het JSON-object volledig is afgesloten met }}.

WERKGEVERSVRAAG:
{tekst}"""

EVALUEER_PROFIEL_PROMPT = """Evalueer het volgende geëxtraheerde {type_profiel} op volledigheid en kwaliteit.
Formuleer maximaal 5 concrete vervolgvragen over essentiële informatie die mist om een goede match te kunnen maken.
Elke vraag moet direct te beantwoorden zijn door de gebruiker.
Zet je analyse om in exact dit JSON-format (geen andere tekst, alleen JSON).

{{
    "volledigheid_score": <getal van 0 tot 100, waarbij 100 perfect en compleet is>,
    "vervolgvragen": ["Concrete vraag 1 over missende info", "Vraag 2", "...(max 5)"]
}}

PROFIEL:
{profiel_json}"""

VERRIJK_KANDIDAAT_PROMPT = """Je hebt eerder een profiel gemaakt van een kandidaat. Nu heb je aanvullende informatie gekregen via een Q&A sessie.
Combineer het BESTAANDE PROFIEL met de NIEUWE ANTWOORDEN om een VERBETERD, RIJKER profiel te maken.

Instructies:
- Integreer de nieuwe informatie naadloos in het profiel — niet als apart blokje, maar verweven.
- Update de dossiercompleetheid omhoog als de antwoorden cruciale gaten vullen.
- Voeg nieuwe inzichten toe aan persoonlijkheid, drijfveren, impliciete kwaliteiten etc.
- Genereer NIEUWE vervolgvragen (AAN DE KANDIDAAT) als er NOG steeds belangrijke gaten zijn (max 5).
- Als het profiel nu compleet genoeg is, mag de lijst vervolgvragen leeg zijn.

BESTAAND PROFIEL:
{profiel_json}

NIEUWE ANTWOORDEN (vraag → antwoord):
{antwoorden_json}

ORIGINELE TEKST (ter referentie):
{ruwe_tekst}

Genereer het VOLLEDIGE bijgewerkte profiel in hetzelfde JSON-format als het origineel."""

VERRIJK_WERKGEVERSVRAAG_PROMPT = """Je hebt eerder een werkgeversvraag-profiel gemaakt. Nu heb je aanvullende informatie gekregen via een Q&A sessie.
Combineer het BESTAANDE PROFIEL met de NIEUWE ANTWOORDEN om een VERBETERD, RIJKER profiel te maken.

Instructies:
- Integreer de nieuwe informatie naadloos — niet als apart blokje, maar verweven.
- Update de dossiercompleetheid omhoog als de antwoorden cruciale gaten vullen.
- Voeg nieuwe inzichten toe aan gezochte persoonlijkheid, verborgen behoeften, etc.
- Genereer NIEUWE vervolgvragen (AAN DE WERKGEVER/RECRUITER) als er NOG steeds belangrijke gaten zijn (max 5).
- Als het profiel nu compleet genoeg is, mag de lijst vervolgvragen leeg zijn.

BESTAAND PROFIEL:
{profiel_json}

NIEUWE ANTWOORDEN (vraag → antwoord):
{antwoorden_json}

ORIGINELE TEKST (ter referentie):
{ruwe_tekst}

Genereer het VOLLEDIGE bijgewerkte profiel in hetzelfde JSON-format als het origineel."""


# --- Match-modi ---
# Elke modus definieert welke stappen worden uitgevoerd:
#   stappen: ["kern"] = alleen kern-prompt, ["kern", "verdieping"] = kern + verdieping

QUICK_SCAN_MODEL = "qwen3:4b"
STANDAARD_MODEL = "qwen3:8b"

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
        "temperature": 0.2,
        "model_override": None,
        "max_tekst_lengte": None,
        "think": True,
        "stappen": ["kern", "verdieping"],
        "prompt": KERN_MATCH_PROMPT,
    },
}
