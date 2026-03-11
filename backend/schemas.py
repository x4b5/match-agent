from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


class KandidaatProfiel(BaseModel):
    naam: str = Field(description="Naam van de kandidaat")
    kernrol: str = Field(description="Primaire huidige rol of overkoepelend profiel")
    zijn: str = Field(description="Wie IS deze persoon? Werkstijl, persoonlijkheid, karakter, samenwerking, communicatie, omgang met druk")
    willen: str = Field(description="Wat WILT deze persoon? Drijfveren, motivatie, ambities, wat zoekt iemand in werk")
    kunnen: str = Field(description="Wat KAN deze persoon? Hard/soft skills, leervermogen, opleiding, ervaring, beschikbaarheid/locatie, én wat iemand nog NIET kan.")
    kernwoorden: List[str] = Field(max_length=5, description="5 korte, krachtige trefwoorden die dit profiel het beste samenvatten")
    dossier_compleetheid: int = Field(ge=0, le=100, validation_alias=AliasChoices("dossier_compleetheid", "profiel_betrouwbaarheid"), description="Hoe compleet is dit dossier?")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over essentiële info die mist")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 stellingen met een 4-punts schaal die helpen gaten te vullen")
    last_generated: Optional[str] = Field(default=None, description="ISO datum van laatste generatie")

class WerkgeversvraagProfiel(BaseModel):
    titel: str = Field(description="Functietitel")
    organisatie: str = Field(description="Naam Organisatie")
    zijn: str = Field(description="Wat voor PERSOON moet de kandidaat zijn? Persoonlijkheid, karakter, teamfit, cultuur, werksfeer, verborgen behoeften.")
    willen: str = Field(description="Wat moet de kandidaat WILLEN? Waarden, drijfveren, ambitie, ontwikkeling, wat biedt het bedrijf aan groei en begeleiding.")
    kunnen: str = Field(description="Wat moet de kandidaat KUNNEN? Must-have en nice-to-have skills, taken, verantwoordelijkheden, werktijden, praktische zaken, én aandachtspunten.")
    kernwoorden: List[str] = Field(max_length=5, description="5 korte, krachtige trefwoorden die dit profiel het beste samenvatten")
    dossier_compleetheid: int = Field(ge=0, le=100, validation_alias=AliasChoices("dossier_compleetheid", "profiel_betrouwbaarheid"), description="Hoe compleet is dit dossier?")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over essentiële info die mist")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 stellingen met een 4-punts schaal die helpen gaten te vullen")
    last_generated: Optional[str] = Field(default=None, description="ISO datum van laatste generatie")

class EvalueerProfielResult(BaseModel):
    volledigheid_score: int = Field(ge=0, le=100, description="Volledigheid score")
    vervolgvragen: List[str] = Field(max_length=5, description="Concrete vragen over missende info")
    stellingen: List[str] = Field(default_factory=list, max_length=5, description="5 stellingen over missende info")

class PersonalityAxes(BaseModel):
    Samenwerking: str = Field(description="Hoe werkt deze persoon samen? Bewijs uit dossier. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Drive: str = Field(description="Wat drijft deze persoon? Bewijs uit dossier. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Leervermogen: str = Field(description="Hoe snel pikt deze persoon nieuwe dingen op? Bewijs uit dossier. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Zelfstandigheid: str = Field(description="Hoe goed werkt deze persoon op eigen kracht? Bewijs uit dossier. Indien onbekend: 'Niet af te leiden uit dossier'.")
    Veerkracht: str = Field(description="Hoe gaat deze persoon om met tegenslag? Bewijs uit dossier. Indien onbekend: 'Niet af te leiden uit dossier'.")

class ScoreBreakdown(BaseModel):
    persoonlijkheid_fit: int = Field(ge=0, le=100, description="Hoe goed passen de karaktereigenschappen?")
    cultuur_fit: int = Field(ge=0, le=100, description="Hoe goed past de bedrijfscultuur?")
    vaardigheden_en_leervermogen: int = Field(ge=0, le=100, description="In hoeverre zijn vaardigheden aanwezig of aanleerbaar?")
    groei_potentieel: int = Field(ge=0, le=100, description="Hoeveel groeipotentieel is er?")
    motivatie_alignment: int = Field(ge=0, le=100, description="Hoe goed sluiten drijfveren aan?")

class SuccesPlan(BaseModel):
    """Tweezijdig actieplan: wat kan de kandidaat doen, en wat moet de werkgever bieden?"""
    actie_kandidaat: List[str]
    actie_werkgever: List[str]

class KernMatchResult(BaseModel):
    """Kern-match: de 8 belangrijkste velden — betrouwbaar op elk model."""
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str] = Field(max_length=5, description="Max 3-5 concrete matchpunten")
    ontbrekende_punten: List[str] = Field(max_length=5, description="Max 3-5 concrete ontbrekende punten")
    succes_plan: SuccesPlan
    dossier_compleetheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str] = Field(default_factory=list, max_length=5)
    stellingen: List[str] = Field(default_factory=list, max_length=5)

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
    succes_plan: SuccesPlan = Field(default=None)
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
    gespreksstarters: List[str] = Field(default_factory=list)
    risico_mitigatie: str = Field(default="")
    gedeelde_waarden: List[str] = Field(default_factory=list)
    groeipotentieel: str = Field(default="")
    aandachtspunten: List[str] = Field(default_factory=list)
    boodschap_aan_kandidaat: str = Field(default="")
    match_narratief: str = Field(default="", description="Kort, inspirerend verhaal dat de match tot leven brengt")
    personality_axes: PersonalityAxes = Field(default=None)
    score_breakdown: ScoreBreakdown = Field(default=None, description="Transparante sub-scores per dimensie")
    dossier_compleetheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str] = Field(default_factory=list)
