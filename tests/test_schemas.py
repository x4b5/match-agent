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
            zijn="Analytisch en creatief. Werkt graag zelfstandig maar communiceert helder in teamverband.",
            willen="Wil groeien in AI en machine learning. Zoekt een informele werkplek met ruimte voor experiment.",
            kunnen="Python, JavaScript, data-analyse. HBO ICT afgerond. Woont in Amsterdam, fulltime beschikbaar. Nog weinig ervaring met cloud-infra.",
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
                zijn="Test", willen="Test", kunnen="Test",
                dossier_compleetheid=150,  # Te hoog!
                vervolgvragen=[]
            )

    def test_dossier_compleetheid_negatief(self):
        """dossier_compleetheid < 0 moet falen."""
        with pytest.raises(ValidationError):
            KandidaatProfiel(
                naam="Test", kernrol="Test",
                zijn="Test", willen="Test", kunnen="Test",
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
            zijn="Alert, kalm onder druk, teamspeler. Past in een hecht team met directe communicatie.",
            willen="Kandidaat die veiligheid als kernwaarde ziet. Bedrijf biedt opleiding en doorgroeimogelijkheden.",
            kunnen="VCA-certificaat is een must, EHBO is mooi meegenomen. Hoofdtaak: objectbeveiliging incl. rondes en camerabewaking. Wisselende diensten.",
            dossier_compleetheid=80,
            vervolgvragen=[]
        )
        assert profiel.titel == "Objectbeveiliger"


class TestPersonalityAxes:
    def test_geldige_axes(self):
        axes = PersonalityAxes(
            Samenwerking="Werkt graag in teamverband, blijkt uit '10 jaar samenwerken'",
            Drive="Niet af te leiden uit dossier",
            Leervermogen="Hoog - pikt snel nieuwe dingen op",
            Zelfstandigheid="Redelijk",
            Veerkracht="Niet af te leiden uit dossier"
        )
        assert axes.Samenwerking == "Werkt graag in teamverband, blijkt uit '10 jaar samenwerken'"


class TestQuickScanMatchResult:
    def test_geldig_resultaat(self):
        result = QuickScanMatchResult(
            match_percentage=72,
            matchende_punten=["Communicatief", "Stressbestendig"],
            ontbrekende_punten=["Geen VCA"],
            succes_plan={"actie_kandidaat": ["A"], "actie_werkgever": ["B"]},
            personality_axes=PersonalityAxes(
                Samenwerking="Beschrijving A", Drive="Beschrijving B", Leervermogen="Beschrijving C",
                Zelfstandigheid="Beschrijving D", Veerkracht="Beschrijving E"
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
                personality_axes=PersonalityAxes(
                    Openheid="Beschrijving A", Conscientieusheid="Beschrijving B", Extraversie="Beschrijving C",
                    Vriendelijkheid="Beschrijving D", Neuroticisme="Beschrijving E"
                ),
                dossier_compleetheid="Zeer Hoog"  # Ongeldig!
            )

    def test_match_percentage_bereik(self):
        """match_percentage moet tussen 0 en 100 zijn."""
        with pytest.raises(ValidationError):
            QuickScanMatchResult(
                match_percentage=120,  # Te hoog!
                matchende_punten=[], ontbrekende_punten=[],
                personality_axes=PersonalityAxes(
                    Openheid="Beschrijving A", Conscientieusheid="Beschrijving B", Extraversie="Beschrijving C",
                    Vriendelijkheid="Beschrijving D", Neuroticisme="Beschrijving E"
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
            gespreksstarters=["Vertel over je ervaring met klanten"],
            risico_mitigatie="Begeleiding eerste 6 maanden",
            gedeelde_waarden=["Klanttevredenheid"],
            groeipotentieel="Kan doorgroeien naar teamleider",
            aandachtspunten=["Sectorkennis opbouwen"],
            boodschap_aan_kandidaat="Deze rol is perfect voor jou!",
            match_narratief="Een verrassende match die inspireert.",
            personality_axes=PersonalityAxes(
                Samenwerking="Beschrijving A", Drive="Beschrijving B", Leervermogen="Beschrijving C",
                Zelfstandigheid="Beschrijving D", Veerkracht="Beschrijving E"
            ),
            score_breakdown=ScoreBreakdown(
                persoonlijkheid_fit=85, cultuur_fit=78,
                vaardigheden_en_leervermogen=60, groei_potentieel=90,
                motivatie_alignment=80
            ),
            dossier_compleetheid="Hoog",
            vervolgvragen=["Wat trekt je aan in beveiliging?"]
        )
        assert result.match_percentage == 82
        assert result.score_breakdown.persoonlijkheid_fit == 85
