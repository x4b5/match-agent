"""Tests voor Pydantic schema validatie — edge cases en verplichte velden."""
import pytest
from pydantic import ValidationError
from backend.schemas import (
    KandidaatProfiel, WerkgeversvraagProfiel, QuickScanMatchResult,
    StandaardMatchResult, PersonalityAxes, ScoreBreakdown
)


class TestKandidaatProfiel:
    def test_minimaal_geldig_profiel(self):
        """Alle verplichte velden ingevuld — moet geldig zijn."""
        profiel = KandidaatProfiel(
            naam="Jan de Vries",
            kernrol="Software Developer",
            persoonlijkheid=["analytisch", "creatief"],
            kwaliteiten=["probleemoplossend"],
            impliciete_kwaliteiten=["doorzetter"],
            drijfveren=["leren"],
            onderliggende_motivatie="Groei",
            ideale_werkdag="Code schrijven",
            werkstijl="Zelfstandig",
            ambities_en_leerdoelen=["AI leren"],
            gewenste_bedrijfscultuur="Informeel",
            hobby_en_interesses=["schaken"],
            hard_skills=["Python"],
            soft_skills=["communicatie"],
            beschikbaarheid_en_locatie="Amsterdam",
            opleiding_en_ervaring_samenvatting="HBO ICT",
            dossier_compleetheid=75,
            vervolgvragen=["Wat is je ideale team?"]
        )
        assert profiel.naam == "Jan de Vries"
        assert profiel.dossier_compleetheid == 75

    def test_dossier_compleetheid_te_hoog(self):
        """dossier_compleetheid > 100 moet falen."""
        with pytest.raises(ValidationError):
            KandidaatProfiel(
                naam="Test", kernrol="Test",
                persoonlijkheid=[], kwaliteiten=[], impliciete_kwaliteiten=[],
                drijfveren=[], onderliggende_motivatie="", ideale_werkdag="",
                werkstijl="", ambities_en_leerdoelen=[], gewenste_bedrijfscultuur="",
                hobby_en_interesses=[], hard_skills=[], soft_skills=[],
                beschikbaarheid_en_locatie="", opleiding_en_ervaring_samenvatting="",
                dossier_compleetheid=150,  # Te hoog!
                vervolgvragen=[]
            )

    def test_dossier_compleetheid_negatief(self):
        """dossier_compleetheid < 0 moet falen."""
        with pytest.raises(ValidationError):
            KandidaatProfiel(
                naam="Test", kernrol="Test",
                persoonlijkheid=[], kwaliteiten=[], impliciete_kwaliteiten=[],
                drijfveren=[], onderliggende_motivatie="", ideale_werkdag="",
                werkstijl="", ambities_en_leerdoelen=[], gewenste_bedrijfscultuur="",
                hobby_en_interesses=[], hard_skills=[], soft_skills=[],
                beschikbaarheid_en_locatie="", opleiding_en_ervaring_samenvatting="",
                dossier_compleetheid=-10,  # Negatief!
                vervolgvragen=[]
            )

    def test_verplicht_veld_ontbreekt(self):
        """Ontbrekend verplicht veld moet falen."""
        with pytest.raises(ValidationError):
            KandidaatProfiel(naam="Test")  # Alle andere velden ontbreken


class TestWerkgeversvraagProfiel:
    def test_minimaal_geldig_profiel(self):
        profiel = WerkgeversvraagProfiel(
            titel="Objectbeveiliger",
            organisatie="Beveiliging BV",
            organisatiewaarden=["veiligheid"],
            gezochte_persoonlijkheid=["alert"],
            benodigde_kwaliteiten=["communicatief"],
            ideale_kandidaat_persona="Iemand die kalm blijft",
            verborgen_behoeften=["stressbestendigheid"],
            team_en_cultuur="Hecht team",
            ontwikkel_en_doorgroeimogelijkheden="Opleiding",
            begeleiding_en_inwerkperiode="8 weken",
            must_have_skills=["VCA"],
            nice_to_have_skills=["EHBO"],
            werktijden_en_omstandigheden="Wisselende diensten",
            belangrijkste_taak="Objectbeveiliging",
            dossier_compleetheid=80,
            vervolgvragen=[]
        )
        assert profiel.titel == "Objectbeveiliger"


class TestPersonalityAxes:
    def test_geldige_axes(self):
        axes = PersonalityAxes(
            Analytisch="Zeer sterk, blijkt uit '10 jaar data-analyse'", 
            Sociaal="Niet af te leiden uit dossier", 
            Creatief="Hoog - ontwerpt eigen oplossingen",
            Gestructureerd="Redelijk", 
            Ondernemend="Niet af te leiden uit dossier"
        )
        assert axes.Analytisch == "Zeer sterk, blijkt uit '10 jaar data-analyse'"


class TestQuickScanMatchResult:
    def test_geldig_resultaat(self):
        result = QuickScanMatchResult(
            match_percentage=72,
            matchende_punten=["Communicatief", "Stressbestendig"],
            ontbrekende_punten=["Geen VCA"],
            verrassings_element="Horeca-achtergrond geeft klantgerichtheid",
            onderbouwing="Past goed qua karakter",
            personality_axes=PersonalityAxes(
                Analytisch="Beschrijving A", Sociaal="Beschrijving B", Creatief="Beschrijving C",
                Gestructureerd="Beschrijving D", Ondernemend="Beschrijving E"
            ),
            dossier_compleetheid="Hoog"
        )
        assert result.match_percentage == 72

    def test_ongeldige_dossier_compleetheid(self):
        """dossier_compleetheid moet exact 'Laag', 'Gemiddeld', of 'Hoog' zijn."""
        with pytest.raises(ValidationError):
            QuickScanMatchResult(
                match_percentage=72,
                matchende_punten=[], ontbrekende_punten=[],
                verrassings_element="", onderbouwing="",
                personality_axes=PersonalityAxes(
                    Analytisch="Beschrijving A", Sociaal="Beschrijving B", Creatief="Beschrijving C",
                    Gestructureerd="Beschrijving D", Ondernemend="Beschrijving E"
                ),
                dossier_compleetheid="Zeer Hoog"  # Ongeldig!
            )

    def test_match_percentage_bereik(self):
        """match_percentage moet tussen 0 en 100 zijn."""
        with pytest.raises(ValidationError):
            QuickScanMatchResult(
                match_percentage=120,  # Te hoog!
                matchende_punten=[], ontbrekende_punten=[],
                verrassings_element="", onderbouwing="",
                personality_axes=PersonalityAxes(
                    Analytisch="Beschrijving A", Sociaal="Beschrijving B", Creatief="Beschrijving C",
                    Gestructureerd="Beschrijving D", Ondernemend="Beschrijving E"
                ),
                dossier_compleetheid="Hoog"
            )


class TestStandaardMatchResult:
    def test_geldig_volledig_resultaat(self):
        result = StandaardMatchResult(
            match_percentage=82,
            matchende_punten=["Teamspeler", "Communicatief"],
            ontbrekende_punten=["Geen ervaring in sector"],
            succes_plan={"actie_kandidaat": ["Inwerktraject van 3 maanden"], "actie_werkgever": ["Mentorprogramma opzetten"]},
            verrassings_element="Horeca-achtergrond",
            gespreksstarters=["Vertel over je ervaring met klanten"],
            risico_mitigatie="Begeleiding eerste 6 maanden",
            gedeelde_waarden=["Klanttevredenheid"],
            groeipotentieel="Kan doorgroeien naar teamleider",
            cultuur_fit="Past in informele cultuur",
            aandachtspunten=["Sectorkennis opbouwen"],
            boodschap_aan_kandidaat="Deze rol is perfect voor jou!",
            match_narratief="Een verrassende match die inspireert.",
            onderbouwing="Sterk karakter en overdraagbare skills",
            personality_axes=PersonalityAxes(
                Analytisch="Beschrijving A", Sociaal="Beschrijving B", Creatief="Beschrijving C",
                Gestructureerd="Beschrijving D", Ondernemend="Beschrijving E"
            ),
            score_breakdown=ScoreBreakdown(
                persoonlijkheid_fit=85, cultuur_fit=78,
                skills_overlap=60, groei_potentieel=90,
                motivatie_alignment=80
            ),
            dossier_compleetheid="Hoog",
            vervolgvragen=["Wat trekt je aan in beveiliging?"]
        )
        assert result.match_percentage == 82
        assert result.score_breakdown.persoonlijkheid_fit == 85
