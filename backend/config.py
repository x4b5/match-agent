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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:27b")
PROFIEL_MODEL = os.getenv("PROFIEL_MODEL", "qwen3:4b")
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
# Kern-prompt: 8 velden — betrouwbaar op elk quantisatieniveau
KERN_MATCH_PROMPT = """Bekijk hoe goed deze kandidaat en de werkgeversvraag bij elkaar passen.
Gebruik ALTIJD heldere, begrijpelijke taal (B1-niveau). Vermijd jargon en HR-termen.
Let vooral op persoonlijkheid, potentieel en karakter.

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Geef je antwoord in exact de volgende JSON-opmaak (schrijf geen extra test eromheen, alleen de JSON):
{{
  "match_percentage": <getal van 0 tot 100 — laat persoonlijkheid en talent hierin het zwaarst meewegen>,
  "matchende_punten": ["maximaal 3 hele duidelijke punten waarop de kandidaat en vacature goed samengaan"],
  "ontbrekende_punten": ["maximaal 3 punten die we eigenlijk missen of die een drempel/risico vormen"],
  "verrassings_element": "Wat maakt deze combinatie slim of onverwacht? Noem één leuk of pakkend punt.",
  "onderbouwing": "Leg in 2 of 3 zinnen uit waarom de drijfveren en karakters van beide partijen klikken.",
  "cultuur_fit": "Zal deze persoon passen bij de sfeer in dit bedrijf/team? Waarom wel of niet?",
  "dossier_compleetheid": "Laag|Gemiddeld|Hoog",
  "vervolgvragen": ["maximaal 3 belangrijke vragen die we nog moeten stellen om zekerder te zijn van deze match"],
  "stellingen": ["maximaal 3 prikkelende stellingen die de kandidaat kan beoordelen om de match te bevestigen of te verfijnen"]
}}"""

# Verdieping-prompt: ontvangt kern-resultaat als context, genereert extra inzichten
VERDIEPING_MATCH_PROMPT = """Je hebt onlangs een eerste scan gemaakt van een match. Voeg hier nu nog meer diepgang en inzichten aan toe.
Schrijf in ALTIJD begrijpelijke en duidelijke taal (B1-niveau). Spreek de lezer direct aan.

KERN-ANALYSE:
{kern_json}

KANDIDAATPROFIEL:
{cv_tekst}

WERKGEVERSVRAAGPROFIEL:
{vacature_tekst}

Geef je uitgebreide analyse in exact deze JSON-opmaak (alleen de JSON-code overnemen):
{{
  "overbruggings_advies": ["Geef voor élk ontbrekend punt een advies. Hoe vangen we dit op? (bijvoorbeeld met een cursus of meer begeleiding)"],
  "gespreksstarters": ["3 goede interviewvragen die de recruiter kan gebruiken in het eerste gesprek"],
  "risico_mitigatie": "Hoe houden we de risico's zo klein mogelijk? Wat voor soort inwerken/begeleiding is daarvoor handig?",
  "gedeelde_waarden": ["Welke normen en waarden vinden zowel het bedrijf als deze persoon belangrijk?"],
  "groeipotentieel": "Hoe en in welke richting zou deze persoon binnen dit bedrijf kunnen doorgroeien?",
  "boodschap_aan_kandidaat": "Een kort en aanmoedigend berichtje aan de kandidaat: waarom past deze vacature nou zó goed bij jou?",
  "match_narratief": "Een inspirerend en kort verhaaltje (3-4 zinnen) dat laat zien waarom deze combinatie een gouden zet kan zijn.",
  "personality_axes": {{
    "Analytisch": "Korte uitleg en geef een duidelijk voorbeeld uit de tekst. Niet zeker? Zeg dan: 'Niet af te leiden te maken uit het profiel'.",
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
PROFIEL_KANDIDAAT_PROMPT = """Maak een overzichtelijk profiel van deze persoon op basis van de tekst.
Zet de tekst om in precies deze JSON-opmaak (alleen de JSON-code, geen extra tekst eromheen).

Belangrijke aanwijzingen:
- Gebruik begrijpelijke en duidelijke taal (B1-niveau). Vermijd jargon en ingewikkelde woorden.
- Focus vooral op wie deze persoon IS, niet alleen op wat ze hebben gedaan.
- Kijk ook naar kwaliteiten die niet letterlijk worden genoemd, maar die je wel kunt afleiden (bijvoorbeeld: iemand die jarenlang in de horeca werkt, is waarschijnlijk stressbestendig).
- BELANGRIJK: Blijf bij de feiten. Als iets niet in de tekst staat, vul dan "Niet genoemd" in of laat het lijstje leeg. Verzin geen eigenschappen of hobby's die je niet kunt bewijzen.
- UITZONDERING: Bij het veld "verrassende_functies" mag je wél creatief zijn. Bedenk op basis van iemands karakter welke banen goed zouden passen, ook al heeft diegene daar niet de juiste papieren voor. Noem altijd minstens 3 suggesties.
- BEOORDELING DOSSIERCOMPLEETHEID: Wees heel streng!
    - 0-20: Bijna geen info (alleen een naam of een kort zinnetje).
    - 20-40: Alleen korte aantekeningen of een paar regels tekst. Zonder echt CV is de score altijd lager dan 40%.
    - 40-70: Er is een goed CV met werkervaring, maar we weten nog weinig over iemands karakter of wat diegene echt drijft.
    - 70-90: Het dossier is compleet (CV + verslag van een gesprek). We hebben een goed beeld van de persoon en de ambities.
    - 90-100: Een zeer uitgebreid dossier met veel details en extra antwoorden op vragen.

{{
    "naam": "Naam van de persoon",
    "kernrol": "Wat is iemands huidige baan of het belangrijkste profiel?",
    "persoonlijkheid": ["Lijstje met karaktereigenschappen"],
    "kwaliteiten": ["Lijstje met sterke punten en talenten"],
    "impliciete_kwaliteiten": ["Lijstje met verborgen talenten die je kunt afleiden uit ervaring of hobby's"],
    "drijfveren": ["Lijstje met wat deze persoon belangrijk vindt in werk"],
    "onderliggende_motivatie": "Wat drijft deze persoon in de kern? (Denk aan: zekerheid, anderen helpen, vrijheid, groei, enz.)",
    "ideale_werkdag": "Beschrijf in 2 of 3 zinnen hoe een perfecte dag op het werk eruitziet voor deze persoon.",
    "werkstijl": "Hoe gaat deze persoon te werk? (Bijvoorbeeld: werkt graag alleen, is een echte teamplayer, of stroopt graag de mouwen op.)",
    "ambities_en_leerdoelen": ["Lijstje van wat de persoon nog wil bereiken of leren"],
    "gewenste_bedrijfscultuur": "In wat voor soort werkomgeving voelt deze persoon zich het prettigst?",
    "hobby_en_interesses": ["Lijstje van relevante hobby's die iets zeggen over iemands karakter"],
    "hard_skills": ["Lijstje met technische vaardigheden en diploma's"],
    "soft_skills": ["Lijstje met sociale en persoonlijke vaardigheden"],
    "beschikbaarheid_en_locatie": "Praktische zaken zoals woonplaats of uren (indien genoemd)",
    "opleiding_en_ervaring_samenvatting": "Korte samenvatting van de achtergrond",
    "verrassende_functies": ["3 tot 5 banen die goed passen bij iemands karakter en talent, maar waar de persoon zelf misschien niet direct aan denkt. Wees creatief!"],
    "dossier_compleetheid": <getal van 0 tot 100 — hoe compleet is dit dossier om een goede match te maken?>,
    "aandachtspunten": ["Lijstje van zaken waar we extra op moeten letten of die een risico kunnen zijn"],
    "vervolgvragen": ["Maximaal 5 DUIDELIJKE VRAGEN AAN DE KANDIDAAT over belangrijke informatie die nog ontbreekt (bijvoorbeeld over werkstijl of wat iemand écht motiveert)"],
    "stellingen": ["Bedenk 5 prikkelende stellingen die de kandidaat kan beoordelen op een schaal van 1 tot 4 (bijv. 'Ik werk het liefst in een gestructureerde omgeving'). Gebruik stellingen om informatie te verkrijgen die nog niet in het profiel staat."],
    "cultuur_vragen": ["3 KORTE, SIMPELE, verhalende vragen over cultuur en persoonlijkheid. Schrijf op B1-niveau (begrijpelijk voor iedereen). Vermijd moeilijke woorden of formele taal. Denk aan: 'Wanneer baalde je echt van een fout, maar leerde je er toch van?' of 'Heb je wel eens iets geks gedaan om een klant blij te maken?'. Schrijf zoals je tegen een vriend praat."]
}}

BELANGRIJK: Zorg dat het veld "dossier_compleetheid" altijd een getal is. Stop direct nadat je het JSON-object hebt afgesloten met }}.

KANDIDAATTEKST:
{tekst}"""

PROFIEL_WERKGEVERSVRAAG_PROMPT = """Maak een overzichtelijk profiel van deze werkgeversvraag of vacature.
Zet de tekst om in precies deze JSON-opmaak (alleen de JSON-code, geen extra tekst eromheen).

Belangrijke aanwijzingen:
- Gebruik begrijpelijke en duidelijke taal (B1-niveau). Vermijd jargon en ingewikkelde woorden.
- Schrijf actief en direct.
- Focus niet alleen op de harde eisen, maar vooral op het TYPE PERSOON dat wordt gezocht.
- BELANGRIJK: Blijf bij de feiten uit de tekst. Als iets niet in de tekst staat, vul dan "Niet genoemd" in. Ga geen bedrijfscultuur verzinnen die niet in de tekst staat.
- BEOORDELING DOSSIERCOMPLEETHEID: Wees heel streng!
    - 0-20: Zeer korte tekst (bijvoorbeeld alleen de naam van de baan en de plaats).
    - 20-40: Alleen korte aantekeningen of een paar zinnetjes. Zonder volledige tekst is de score altijd lager dan 40%.
    - 40-70: De eisen zijn duidelijk, maar we weten nog niks over de sfeer, het team of de doorgroeimogelijkheden.
    - 70-90: Een goede tekst met informatie over de taken, het team en het type persoon dat gezocht wordt.
    - 90-100: Een zeer uitgebreid verhaal met details over de visie van het bedrijf en hoe iemand wordt ingewerkt.

{{
    "titel": "Naam van de baan",
    "organisatie": "Naam van het bedrijf",
    "organisatiewaarden": ["Lijstje van belangrijkste waarden van het bedrijf/team"],
    "gezochte_persoonlijkheid": ["Lijstje van gewenste karaktereigenschappen"],
    "benodigde_kwaliteiten": ["Lijstje van belangrijkste talenten om succesvol te zijn in deze baan"],
    "ideale_kandidaat_persona": "Beschrijf in 2 of 3 zinnen het type persoon dat hier echt gelukkig zou worden — niet op basis van het CV, maar qua karakter and instelling.",
    "verborgen_behoeften": ["Lijstje van belangrijke zaken die niet letterlijk in de tekst staan, maar die wel cruciaal zijn voor succes"],
    "team_en_cultuur": "Korte beschrijving van de werkomgeving, de sfeer and het team",
    "ontwikkel_en_doorgroeimogelijkheden": "Wat biedt het bedrijf aan groei? (Bijvoorbeeld trainingen of cursussen)",
    "begeleiding_en_inwerkperiode": "Hoe wordt iemand opgevangen and ingewerkt? (Zeker belangrijk voor mensen uit een andere sector)",
    "must_have_skills": ["Lijstje van vaardigheden die echt onmisbaar zijn"],
    "nice_to_have_skills": ["Lijstje van vaardigheden die mooi meegenomen zijn, maar die je ook nog kunt leren"],
    "taken": ["Lijstje van de belangrijkste taken and verantwoordelijkheden"],
    "werktijden_en_omstandigheden": "Praktische zaken over uren, tijden of de werkplek",
    "belangrijkste_taak": "Wat is de allerbelangrijkste taak in deze baan?",
    "dossier_compleetheid": <getal van 0 tot 100 — hoe compleet is de informatie om een goede match te maken?>,
    "aandachtspunten": ["Lijstje van zaken waar we extra op moeten letten (bijvoorbeeld reistijd, ploegendienst of fysiek zwaar werk)"],
    "vervolgvragen": ["Maximaal 5 DUIDELIJKE VRAGEN AAN DE WERKGEVER over belangrijke details die nog ontbreken over de baan of het team"],
    "stellingen": ["Bedenk 5 prikkelende stellingen over de werkplek of het team (bijv. 'In dit team wordt veel samengewerkt in plaats van individueel gewerkt'). Gebruik stellingen om de cultuur en behoeften scherper te krijgen."]
}}

BELANGRIJK: Zorg dat het veld "dossier_compleetheid" altijd een getal is. Stop direct nadat je het JSON-object hebt afgesloten met }}.

WERKGEVERSVRAAG:
{tekst}"""

EVALUEER_PROFIEL_PROMPT = """Beoordeel hoe compleet en goed het volgende profiel is ({type_profiel}).
Bedenk maximaal 5 duidelijke vragen die we nog aan de gebruiker kunnen stellen. Zo krijgen we de informatie die we nog missen om een echt goede match te maken.
Zorg dat de vragen makkelijk te beantwoorden zijn.
Geef je antwoord in precies deze JSON-opmaak (geen extra tekst eromheen).

{{
    "volledigheid_score": <getal van 0 tot 100, waarbij 100 betekent dat alles erin staat>,
    "vervolgvragen": ["Duidelijke vraag 1 over wat er ontbreekt", "Vraag 2", "...(maximaal 5 vragen)"],
    "stellingen": ["5 prikkelende stellingen die gaten in de informatie vullen (bijv. 'Ik vind het geen probleem om onder tijdsdruk te werken')"]
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
- Voeg nieuwe inzichten toe over iemands karakter, talenten en drijfveren op basis van de antwoorden.
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
- Voeg nieuwe inzichten toe over het gezochte karakter, de werksfeer en behoeften.
- Bedenk nieuwe vervolgvragen voor de werkgever als er nog steeds belangrijke zaken ontbreken (maximaal 5).
- Bedenk 5 nieuwe prikkelende stellingen over de werkplek of het team om de cultuur scherper te krijgen.
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

Aanwijzingen:
0. Gebruik ALTIJD heldere, begrijpelijke taal (B1-niveau). Geen wollig taalgebruik of HR-jargon.
1. Extraheer nieuwe feiten, vaardigheden of karaktereigenschappen uit de feedback.
2. Update relevante velden in het profiel (zoals 'persoonlijkheid', 'kwaliteiten', 'hard_skills', 'soft_skills').
3. Als de feedback aangeeft dat iets NIET klopt, pas dit dan aan.
4. Verhoog de 'dossier_compleetheid' als de feedback waardevolle nieuwe informatie bevat.
5. Behoud alle bestaande informatie die niet door de feedback wordt tegengesproken.

Return het VOLLEDIG BIJGEWERKTE KANDIDAATPROFIEL in exact dezelfde JSON-opmaak als het origineel."""

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
