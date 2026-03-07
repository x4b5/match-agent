import os
import random
import subprocess
import sys

# Zorg dat python-docx beschikbaar is
try:
    import docx
    import pypdf
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "pypdf", "fpdf2"])
    import docx
    import pypdf
    from fpdf import FPDF

KANDIDATEN_DIR = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/kandidaten")

if not os.path.exists(KANDIDATEN_DIR):
    os.makedirs(KANDIDATEN_DIR)

kandidaten = [
    {
        "naam": "sjaak_polak",
        "doc_naam": "intakegesprek_sjaak.txt",
        "type": "txt",
        "inhoud": "INTAKE NOTITIES\nNaam: Sjaak Polak\nDatum: 10 maart 2026\nKandidaat is een senior projectmanager met 12 jaar ervaring in de bouw. IPMA-C gecertificeerd.\nHeeft grote infraprojecten (tot €50M) geleid. Kennis van UAV-GC contracten en werkt graag met Primavera.\nZoekt een nieuwe uitdaging als projectdirecteur of senior lead."
    },
    {
        "naam": "chloe_jansen",
        "doc_naam": "CV_Chloe_Jansen.docx",
        "type": "docx",
        "inhoud": "Curriculum Vitae Chloe Jansen\nProfiel: Enthousiaste online marketeer met focus op e-commerce en conversie-optimalisatie.\nErvaring:\n2022 - Heden: Marketing Specialist bij [Bedrijf X]. Verantwoordelijk voor Google Ads (ROAS 400%) en implementatie van GA4.\n2019 - 2022: Junior Marketeer bij [Bedrijf Y]. Beheerde Klaviyo e-mail campagnes en A/B testing.\nOpleiding:\nHBO Commerciële Economie, Hogeschool Utrecht (2019).\nSkills: Google Ads, Meta Ads, SEO, A/B Testing, Klaviyo."
    },
    {
        "naam": "bas_de_groot",
        "doc_naam": "verslag_bas.txt",
        "type": "txt",
        "inhoud": "Kort verslag test Bas de Groot\nResultaat persoonlijkheidstest: Analytisch sterk, introvert, detailgericht.\nBas heeft een HBO in Informatica. Hij heeft de afgelopen 3 jaar gewerkt als Data Analist. \nHij is enorm sterk in Python, Pandas, en SQL. Heeft veel dashboards gebouwd in Power BI.\nWeinig ervaring met direct klantcontact, maar zoekt wel een medior rol."
    },
    {
        "naam": "fatima_el_idrissi",
        "doc_naam": "sollicitatiebrief_fatima.pdf",
        "type": "pdf",
        "inhoud": "Beste HR,\nHierbij solliciteer ik op een functie als HR Manager. Ik heb ruim 6 jaar ervaring in het HR-vakbedrijf, waarvan de laatste 3 jaar als leidinggevende van een team van 4 HR-adviseurs.\nIk heb ruime kennis van het arbeidsrecht en verzuimmanagement, en werk dagelijks met AFAS.\nMijn opleiding Psychologie (WO) helpt me enorm in de dagelijkse praktijk.\nGroet, Fatima"
    },
    {
        "naam": "kevin_visser",
        "doc_naam": "ruwe_aantekeningen.txt",
        "type": "txt",
        "inhoud": "- Kevin V.\n- starter (1 jaar stage-ervaring)\n- MBO 4 Bouwkunde\n- tekent veel in AutoCAD en BIM.\n- wil doorgroeien naar werkvoorbereider / junior projectmanager.\n- enthousiaste jongen."
    },
    {
        "naam": "emily_chen",
        "doc_naam": "Emily_Chen_Resume.pdf",
        "type": "pdf",
        "inhoud": "EMILY CHEN | Data Scientist\nSkills: Python, Machine Learning (Scikit-Learn, TensorFlow), SQL, Tableau, dbt, Azure Cloud.\nExperience:\n- Data Scientist @ TechCorp (4 yrs): Developed predictive models, increased accuracy by 15%.\nEducation: MSc Econometrics, Erasmus University (2020).\nLanguages: English (Fluent), Dutch (B2)."
    },
    {
        "naam": "willem_de_vries",
        "doc_naam": "Wdv_profiel.txt",
        "type": "txt",
        "inhoud": "Willem de Vries, 55 jaar. Ervaren rot in de infrastructuur.\nOpleiding: MTS Civiele Techniek, daarna diverse interne curssusen.\nSkills: AutoCAD, bestekken schrijven, RAW-systematiek, UAV 2012.\nWerkervaring: 25 jaar als bestekschrijver / projectleider infra bij diverse gemeentes."
    },
    {
        "naam": "nina_smits",
        "doc_naam": "aanbevelingsbrief_nina.docx",
        "type": "docx",
        "inhoud": "Aanbeveling voor Nina Smits\nNina heeft 2 jaar bij ons gewerkt als HR Assistent. Ze is een kei in administratie en heeft onlangs haar HBO HRM behaald.\nZe is bekend met de basis van arbeidsrecht en Arbowetgeving. Ze zoekt nu een stap naar HR Adviseur."
    },
    {
        "naam": "tim_hendriks",
        "doc_naam": "transcript_video_pitch.txt",
        "type": "txt",
        "inhoud": "[00:01] Hoi, ik ben Tim en ik ben een gepassioneerde online marketeer.\n[00:05] Ik heb de afgelopen 5 jaar veel gedaan met SEO, SEMrush was mijn beste vriend.\n[00:10] Ook heb ik een webshop gerund in de plantenbranche, dus e-commerce kent geen geheimen voor me.\n[00:15] Ik zoek een rol als senior online marketeer."
    },
    {
        "naam": "anne_fleur_bos",
        "doc_naam": "AF_Bos_CV_2026.docx",
        "type": "docx",
        "inhoud": "Anne-Fleur Bos\nWO Master Finance.\nWerkervaring: 1 jaar traineeship bij een grote bank.\nGedaan: Data crunching, risicomodellen (Python). Niet super veel SQL, maar wel sterke Excel/VBA skills.\nAmbitie: Data Analist."
    }
]

for kandidaat in kandidaten:
    map_pad = os.path.join(KANDIDATEN_DIR, kandidaat["naam"])
    os.makedirs(map_pad, exist_ok=True)
    
    bestand_pad = os.path.join(map_pad, kandidaat["doc_naam"])
    
    if kandidaat["type"] == "txt":
        with open(bestand_pad, "w", encoding="utf-8") as f:
            f.write(kandidaat["inhoud"])
    elif kandidaat["type"] == "docx":
        doc = docx.Document()
        doc.add_paragraph(kandidaat["inhoud"])
        doc.save(bestand_pad)
    elif kandidaat["type"] == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=11)
        pdf.multi_cell(0, 10, kandidaat["inhoud"])
        pdf.output(bestand_pad)

print(f"Succesvol {len(kandidaten)} kandidaten gegenereerd in {KANDIDATEN_DIR}")
