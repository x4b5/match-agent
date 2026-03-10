from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional

class KandidaatProfiel(BaseModel):
    naam: str = Field(description="Naam van de kandidaat")
    kernrol: str = Field(description="Primaire huidige rol of overkoepelend profiel")
    persoonlijkheid: List[str] = Field(description="Lijst van karaktereigenschappen en persoonskenmerken")
    kwaliteiten: List[str] = Field(description="Lijst van sterke punten en talenten")
    impliciete_kwaliteiten: List[str] = Field(description="Verborgen kwaliteiten afgeleid uit werkervaring of hobby's")
    drijfveren: List[str] = Field(description="Wat deze persoon motiveert of zoekt")
    onderliggende_motivatie: str = Field(description="Wat drijft deze persoon in de kern?")
    ideale_werkdag: str = Field(description="Beschrijf in 2-3 zinnen hoe een ideale werkdag eruitziet")
    werkstijl: str = Field(description="Hoe de persoon te werk gaat (bijv. zelfstandig, teamplayer)")
    ambities_en_leerdoelen: List[str] = Field(description="Wat de persoon wil bereiken of nog wil leren")
    gewenste_bedrijfscultuur: str = Field(description="In wat voor soort omgeving de persoon goed gedijt")
    hobby_en_interesses: List[str] = Field(description="Relevante bezigheden die karakter tonen")
    hard_skills: List[str] = Field(description="Relevante hard skills")
    soft_skills: List[str] = Field(description="Soft skills")
    beschikbaarheid_en_locatie: str = Field(description="Praktische zaken (indien genoemd in tekst)")
    opleiding_en_ervaring_samenvatting: str = Field(description="Korte samenvatting van achtergrond")
    verrassende_functies: List[str] = Field(min_length=3, max_length=5, description="3-5 concrete functies/rollen waar deze persoon qua persoonlijkheid en talent goed bij zou passen, maar waar hij/zij zelf misschien niet aan denkt")
    dossier_compleetheid: int = Field(ge=0, le=100, validation_alias=AliasChoices("dossier_compleetheid", "profiel_betrouwbaarheid"), description="Hoe compleet is dit dossier?")
    aandachtspunten: List[str] = Field(default_factory=list, description="Aandachtspunten of kanttekeningen bij dit profiel")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over essentiële info die mist")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 stellingen met een 4-punts schaal die helpen gaten te vullen")
    cultuur_vragen: List[str] = Field(default_factory=list, max_length=3, description="3 prikkelende vragen over cultuur en persoonlijkheid")

class WerkgeversvraagProfiel(BaseModel):
    titel: str = Field(description="Functietitel")
    organisatie: str = Field(description="Naam Organisatie")
    organisatiewaarden: List[str] = Field(description="Kernwaarden van het bedrijf/team")
    gezochte_persoonlijkheid: List[str] = Field(description="Gewenste karaktereigenschappen")
    benodigde_kwaliteiten: List[str] = Field(description="Belangrijkste talenten/kwaliteiten voor succes")
    ideale_kandidaat_persona: str = Field(description="Schets het type mens dat hier zou floreren")
    verborgen_behoeften: List[str] = Field(description="Zaken niet expliciet in vacature maar cruciaal voor succes")
    team_en_cultuur: str = Field(description="Korte omschrijving van werkomgeving, cultuur en sfeer")
    ontwikkel_en_doorgroeimogelijkheden: str = Field(description="Wat het bedrijf te bieden heeft aan potentieel")
    begeleiding_en_inwerkperiode: str = Field(description="Hoe nieuwe collega's worden opgevangen")
    must_have_skills: List[str] = Field(description="Echt onmisbare skills")
    nice_to_have_skills: List[str] = Field(description="Mooi meegenomen, maar trainbare skills")
    werktijden_en_omstandigheden: str = Field(description="Praktische zaken t.a.v. werktijden of fysieke omstandigheden")
    taken: List[str] = Field(description="Opsomming van de belangrijkste taken en verantwoordelijkheden")
    belangrijkste_taak: str = Field(description="Wat deze persoon vooral gaat doen")
    dossier_compleetheid: int = Field(ge=0, le=100, validation_alias=AliasChoices("dossier_compleetheid", "profiel_betrouwbaarheid"), description="Hoe compleet is dit dossier?")
    aandachtspunten: List[str] = Field(default_factory=list, description="Aandachtspunten of kanttekeningen bij deze vraag")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over essentiële info die mist")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 prikkelende stellingen over de werkplek of het team")

class EvalueerProfielResult(BaseModel):
    volledigheid_score: int = Field(ge=0, le=100, description="Volledigheid score")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over missende info")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 stellingen over missende info")

class PersonalityAxes(BaseModel):
    Analytisch: str = Field(description="Kwalitatieve beschrijving mét citaat uit CV als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Sociaal: str = Field(description="Kwalitatieve beschrijving mét citaat uit CV als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Creatief: str = Field(description="Kwalitatieve beschrijving mét citaat uit CV als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Gestructureerd: str = Field(description="Kwalitatieve beschrijving mét citaat uit CV als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Ondernemend: str = Field(description="Kwalitatieve beschrijving mét citaat uit CV als bewijs. Indien onbekend: 'Niet af te leiden uit dossier'.")

class ScoreBreakdown(BaseModel):
    persoonlijkheid_fit: int = Field(ge=0, le=100, description="Hoe goed passen de karaktereigenschappen?")
    cultuur_fit: int = Field(ge=0, le=100, description="Hoe goed past de bedrijfscultuur?")
    skills_overlap: int = Field(ge=0, le=100, description="In hoeverre zijn vereiste skills aanwezig?")
    groei_potentieel: int = Field(ge=0, le=100, description="Hoeveel groeipotentieel is er?")
    motivatie_alignment: int = Field(ge=0, le=100, description="Hoe goed sluiten drijfveren aan?")

class KernMatchResult(BaseModel):
    """Kern-match: de 8 belangrijkste velden — betrouwbaar op elk model."""
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str] = Field(max_length=5, description="Max 3-5 concrete matchpunten")
    ontbrekende_punten: List[str] = Field(max_length=5, description="Max 3-5 concrete ontbrekende punten")
    verrassings_element: str
    onderbouwing: str
    cultuur_fit: str
    dossier_compleetheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str] = Field(default_factory=list, max_length=5)
    stellingen: List[str] = Field(default_factory=list, max_length=5)

class SuccesPlan(BaseModel):
    """Tweezijdig actieplan: wat kan de kandidaat doen, en wat moet de werkgever bieden?"""
    actie_kandidaat: List[str]
    actie_werkgever: List[str]

class VerdiepingMatchResult(BaseModel):
    """Verdieping: extra velden die de kern-match verrijken."""
    succes_plan: SuccesPlan
    gespreksstarters: List[str]
    risico_mitigatie: str
    gedeelde_waarden: List[str]
    groeipotentieel: str
    boodschap_aan_kandidaat: str
    match_narratief: str = Field(description="Kort, inspirerend verhaal dat de match tot leven brengt")
    personality_axes: PersonalityAxes
    score_breakdown: ScoreBreakdown = Field(description="Transparante sub-scores per dimensie")

# QuickScan = kern-match + personality_axes + aandachtspunten (backwards compatible)
class QuickScanMatchResult(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str]
    ontbrekende_punten: List[str]
    verrassings_element: str
    onderbouwing: str
    cultuur_fit: str = Field(default="")
    personality_axes: PersonalityAxes = Field(default=None)
    aandachtspunten: List[str] = Field(default_factory=list)
    dossier_compleetheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str] = Field(default_factory=list)
    stellingen: List[str] = Field(default_factory=list)

# Standaard = samenvoeging van kern + verdieping (backwards compatible)
class StandaardMatchResult(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str]
    ontbrekende_punten: List[str]
    succes_plan: SuccesPlan = Field(default=None)
    verrassings_element: str
    gespreksstarters: List[str] = Field(default_factory=list)
    risico_mitigatie: str = Field(default="")
    gedeelde_waarden: List[str] = Field(default_factory=list)
    groeipotentieel: str = Field(default="")
    cultuur_fit: str
    aandachtspunten: List[str] = Field(default_factory=list)
    boodschap_aan_kandidaat: str = Field(default="")
    match_narratief: str = Field(default="", description="Kort, inspirerend verhaal dat de match tot leven brengt")
    onderbouwing: str
    personality_axes: PersonalityAxes = Field(default=None)
    score_breakdown: ScoreBreakdown = Field(default=None, description="Transparante sub-scores per dimensie")
    dossier_compleetheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str] = Field(default_factory=list)
