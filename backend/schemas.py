from pydantic import BaseModel, Field
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
    profiel_betrouwbaarheid: int = Field(ge=0, le=100, description="Hoe compleet is dit profiel?")
    vervolgvragen: List[str] = Field(max_items=5, description="Concrete vragen over essentiële info die mist")

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
    belangrijkste_taak: str = Field(description="Wat deze persoon vooral gaat doen")
    profiel_betrouwbaarheid: int = Field(ge=0, le=100, description="Hoe compleet is deze werkgeversvraag?")
    vervolgvragen: List[str] = Field(max_items=5, description="Concrete vragen over essentiële info die mist")

class EvalueerProfielResult(BaseModel):
    volledigheid_score: int = Field(ge=0, le=100, description="Volledigheid score")
    vervolgvragen: List[str] = Field(max_items=5, description="Concrete vragen over missende info")

class PersonalityAxes(BaseModel):
    Analytisch: int = Field(ge=0, le=100)
    Sociaal: int = Field(ge=0, le=100)
    Creatief: int = Field(ge=0, le=100)
    Gestructureerd: int = Field(ge=0, le=100)
    Ondernemend: int = Field(ge=0, le=100)

class ScoreBreakdown(BaseModel):
    persoonlijkheid_fit: int = Field(ge=0, le=100, description="Hoe goed passen de karaktereigenschappen?")
    cultuur_fit: int = Field(ge=0, le=100, description="Hoe goed past de bedrijfscultuur?")
    skills_overlap: int = Field(ge=0, le=100, description="In hoeverre zijn vereiste skills aanwezig?")
    groei_potentieel: int = Field(ge=0, le=100, description="Hoeveel groeipotentieel is er?")
    motivatie_alignment: int = Field(ge=0, le=100, description="Hoe goed sluiten drijfveren aan?")

class QuickScanMatchResult(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str]
    ontbrekende_punten: List[str]
    verrassings_element: str
    onderbouwing: str
    personality_axes: PersonalityAxes
    match_betrouwbaarheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")

class StandaardMatchResult(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    matchende_punten: List[str]
    ontbrekende_punten: List[str]
    overbruggings_advies: List[str]
    verrassings_element: str
    gespreksstarters: List[str]
    risico_mitigatie: str
    gedeelde_waarden: List[str]
    groeipotentieel: str
    cultuur_fit: str
    aandachtspunten: str
    boodschap_aan_kandidaat: str
    match_narratief: str = Field(description="Kort, inspirerend verhaal dat de match tot leven brengt")
    onderbouwing: str
    personality_axes: PersonalityAxes
    score_breakdown: ScoreBreakdown = Field(description="Transparante sub-scores per dimensie")
    match_betrouwbaarheid: str = Field(pattern="^(Laag|Gemiddeld|Hoog)$")
    vervolgvragen: List[str]
