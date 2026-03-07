import os

ICLOUD_BASE = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs"
)

CV_DIR = os.path.join(ICLOUD_BASE, "cv's")
VACATURE_DIR = os.path.join(ICLOUD_BASE, "vacaturebank")
RAPPORT_DIR = os.path.join(ICLOUD_BASE, "match-rapporten")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3.5:27b"

SYSTEM_PROMPT = """Je bent een ervaren recruitment-expert die kandidaat-CV's analyseert en matcht met vacatures.
Je bent objectief, grondig en let op zowel harde skills (technisch, opleiding) als zachte skills (communicatie, leiderschap).
Geef altijd eerlijke matchpercentages - een 80%+ match betekent dat de kandidaat echt goed past."""

MATCH_PROMPT = """Analyseer de match tussen dit CV en deze vacature.

CV:
{cv_tekst}

VACATURE:
{vacature_tekst}

Geef je analyse in exact dit JSON-format (geen andere tekst, alleen JSON):
{{
  "match_percentage": <0-100>,
  "matchende_punten": ["punt1", "punt2"],
  "ontbrekende_punten": ["punt1", "punt2"],
  "onderbouwing": "korte toelichting"
}}"""
