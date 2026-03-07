#!/usr/bin/env python3
"""Match-agent: matcht kandidaat-CV's met vacatures via Ollama (Qwen 3.5)."""

import argparse
import json
import os
import re
import sys

import requests

from config import (
    CV_DIR,
    MATCH_PROMPT,
    OLLAMA_MODEL,
    OLLAMA_URL,
    RAPPORT_DIR,
    SYSTEM_PROMPT,
    VACATURE_DIR,
)


def lees_bestanden(directory: str, filter_bestand: str | None = None) -> dict[str, str]:
    """Lees alle .txt bestanden uit een map. Retourneert {bestandsnaam: inhoud}."""
    bestanden = {}
    for f in sorted(os.listdir(directory)):
        if not f.endswith(".txt"):
            continue
        if filter_bestand and f != filter_bestand:
            continue
        pad = os.path.join(directory, f)
        with open(pad, encoding="utf-8") as fh:
            bestanden[f] = fh.read()
    return bestanden


def extract_naam_uit_cv(tekst: str) -> str:
    """Haal de kandidaatnaam uit een CV-tekst."""
    for regel in tekst.splitlines():
        if regel.lower().startswith("naam:"):
            return regel.split(":", 1)[1].strip()
    return "Onbekend"


def extract_vacature_titel(tekst: str) -> str:
    """Haal de vacaturetitel + bedrijf uit een vacaturetekst."""
    titel = ""
    bedrijf = ""
    for regel in tekst.splitlines():
        upper = regel.upper()
        if upper.startswith("VACATURE:"):
            titel = regel.split(":", 1)[1].strip()
        elif upper.startswith("BEDRIJF:"):
            bedrijf = regel.split(":", 1)[1].strip()
        if titel and bedrijf:
            break
    return f"{titel} - {bedrijf}" if bedrijf else titel or "Onbekende vacature"


def _fout_resultaat(reden: str) -> dict:
    return {
        "match_percentage": 0,
        "matchende_punten": [],
        "ontbrekende_punten": [reden],
        "onderbouwing": reden,
    }


def vraag_ollama(cv_tekst: str, vacature_tekst: str) -> dict:
    """Stuur een prompt naar Ollama en parse het JSON-antwoord."""
    prompt = MATCH_PROMPT.format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.3},
            "think": False,
            },
            timeout=600,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("  ⚠ Kan geen verbinding maken met Ollama. Draait het? (ollama serve)", file=sys.stderr)
        return _fout_resultaat("Ollama niet bereikbaar")
    except requests.exceptions.Timeout:
        print("  ⚠ Timeout bij Ollama (>10min). Model te langzaam?", file=sys.stderr)
        return _fout_resultaat("Timeout bij analyse")

    antwoord = response.json().get("response", "")

    # Probeer JSON te extracten uit het antwoord
    json_match = re.search(r"\{.*\}", antwoord, re.DOTALL)
    if not json_match:
        print(f"  ⚠ Kon geen JSON parsen uit model-antwoord", file=sys.stderr)
        return {
            "match_percentage": 0,
            "matchende_punten": [],
            "ontbrekende_punten": ["Analyse mislukt"],
            "onderbouwing": "Model gaf geen geldig JSON-antwoord.",
        }

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        print(f"  ⚠ Ongeldig JSON in model-antwoord", file=sys.stderr)
        return {
            "match_percentage": 0,
            "matchende_punten": [],
            "ontbrekende_punten": ["Analyse mislukt"],
            "onderbouwing": "Model gaf ongeldig JSON-antwoord.",
        }


def maak_balk(percentage: int, breedte: int = 10) -> str:
    """Maak een visuele voortgangsbalk."""
    gevuld = round(percentage / 100 * breedte)
    return "█" * gevuld + "░" * (breedte - gevuld)


def genereer_rapport(naam: str, matches: list[dict]) -> str:
    """Genereer een tekstrapport voor één kandidaat."""
    matches.sort(key=lambda m: m["match_percentage"], reverse=True)

    lijnen = [
        "=" * 60,
        f"MATCH RAPPORT: {naam}",
        "=" * 60,
        "",
    ]

    for i, m in enumerate(matches, 1):
        pct = m["match_percentage"]
        balk = maak_balk(pct)
        lijnen.append(f"{i}. {m['vacature_titel']:<45} [{pct:>3}%] {balk}")

        for punt in m.get("matchende_punten", []):
            lijnen.append(f"   ✓ {punt}")
        for punt in m.get("ontbrekende_punten", []):
            lijnen.append(f"   ✗ {punt}")
        if m.get("onderbouwing"):
            lijnen.append(f"   → {m['onderbouwing']}")
        lijnen.append("")

    return "\n".join(lijnen)


def main():
    parser = argparse.ArgumentParser(description="Match CV's met vacatures via Ollama")
    parser.add_argument("--cv", help="Specifiek CV-bestand (bijv. cv_sarah_de_vries.txt)")
    args = parser.parse_args()

    # Controleer of mappen bestaan
    for pad, label in [(CV_DIR, "CV-map"), (VACATURE_DIR, "Vacature-map")]:
        if not os.path.isdir(pad):
            print(f"Fout: {label} niet gevonden: {pad}", file=sys.stderr)
            sys.exit(1)

    # Maak rapportmap aan als die niet bestaat
    os.makedirs(RAPPORT_DIR, exist_ok=True)

    # Lees bestanden
    cvs = lees_bestanden(CV_DIR, filter_bestand=args.cv)
    vacatures = lees_bestanden(VACATURE_DIR)

    if not cvs:
        print(f"Geen CV's gevonden" + (f" (filter: {args.cv})" if args.cv else ""), file=sys.stderr)
        sys.exit(1)
    if not vacatures:
        print("Geen vacatures gevonden", file=sys.stderr)
        sys.exit(1)

    print(f"Gevonden: {len(cvs)} CV('s), {len(vacatures)} vacature(s)\n")

    for cv_bestand, cv_tekst in cvs.items():
        naam = extract_naam_uit_cv(cv_tekst)
        print(f"▶ Analyseren: {naam} ({cv_bestand})")

        matches = []
        for vac_bestand, vac_tekst in vacatures.items():
            vac_titel = extract_vacature_titel(vac_tekst)
            print(f"  ↳ vs. {vac_titel}...", end=" ", flush=True)

            resultaat = vraag_ollama(cv_tekst, vac_tekst)
            resultaat["vacature_titel"] = vac_titel
            matches.append(resultaat)

            print(f"{resultaat['match_percentage']}%")

        rapport = genereer_rapport(naam, matches)
        print(f"\n{rapport}")

        # Sla rapport op
        rapport_naam = f"rapport_{cv_bestand}"
        rapport_pad = os.path.join(RAPPORT_DIR, rapport_naam)
        with open(rapport_pad, "w", encoding="utf-8") as f:
            f.write(rapport)
        print(f"💾 Opgeslagen: {rapport_pad}\n")


if __name__ == "__main__":
    main()
