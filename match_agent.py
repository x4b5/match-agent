#!/usr/bin/env python3
"""Match-agent: matcht kandidaat-CV's met vacatures via Ollama (Qwen 3.5)."""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import (
    KANDIDATEN_DIR,
    MATCH_MODI,
    MATCH_PROMPT,
    OLLAMA_MODEL,
    OLLAMA_URL,
    RAPPORT_DIR,
    SYSTEM_PROMPT,
    WERKGEVERSVRAGEN_DIR,
)
from profiel_agent import laad_profiel_uit_map

def lijst_mappen(directory: str) -> list[str]:
    """Lijst alle submappen in een directory (exclusief verborgen zoals .git)."""
    if not os.path.isdir(directory):
        return []
    mappen = []
    for f in sorted(os.listdir(directory)):
        if f.startswith("."):
            continue
        if os.path.isdir(os.path.join(directory, f)):
            mappen.append(f)
    return mappen


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


def _verkort_tekst(tekst: str, max_lengte: int) -> str:
    """Verkort tekst tot max_lengte karakters, knip op hele regels."""
    if len(tekst) <= max_lengte:
        return tekst
    afgekapt = tekst[:max_lengte]
    # Knip op laatste volledige regel
    laatste_newline = afgekapt.rfind("\n")
    if laatste_newline > max_lengte // 2:
        afgekapt = afgekapt[:laatste_newline]
    return afgekapt


def _modus_params(modus: str | None) -> dict:
    """Haal parameters op voor een match-modus."""
    modi = MATCH_MODI.get(modus) if modus else None
    return {
        "prompt_template": modi["prompt"] if modi else MATCH_PROMPT,
        "temperature": modi["temperature"] if modi else 0.3,
        "num_predict": modi["num_predict"] if modi else 512,
        "num_ctx": modi.get("num_ctx", 8192) if modi else 8192,
        "model_override": modi.get("model_override") if modi else None,
        "max_tekst_lengte": modi.get("max_tekst_lengte") if modi else None,
    }


def vraag_ollama(cv_tekst: str, vacature_tekst: str, modus: str | None = None) -> dict:
    """Stuur een prompt naar Ollama en parse het JSON-antwoord."""
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
    model = params["model_override"] or OLLAMA_MODEL
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": params["temperature"],
                    "num_predict": params["num_predict"],
                    "num_ctx": params["num_ctx"],
                },
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


def vraag_ollama_stream(cv_tekst: str, vacature_tekst: str, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL, temperature: float = 0.3, modus: str | None = None):
    """Streaming-variant van vraag_ollama. Yieldt tekstfragmenten, retourneert uiteindelijk het parsed JSON-resultaat."""
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
    # Modus overschrijft model en temperature als die zijn ingesteld
    model = params["model_override"] or model
    temperature = params["temperature"]
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)

    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": True,
                "format": "json",
                "options": {
                    "temperature": temperature,
                    "num_predict": params["num_predict"],
                    "num_ctx": params["num_ctx"],
                },
                "think": False,
            },
            timeout=600,
            stream=True,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "data": _fout_resultaat("Ollama niet bereikbaar")}
        return
    except requests.exceptions.Timeout:
        yield {"type": "error", "data": _fout_resultaat("Timeout bij analyse")}
        return

    volledig_antwoord = ""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue
        fragment = chunk.get("response", "")
        if fragment:
            volledig_antwoord += fragment
            yield {"type": "token", "data": fragment}
        if chunk.get("done"):
            break

    # Parse het volledige antwoord als JSON
    json_match = re.search(r"\{.*\}", volledig_antwoord, re.DOTALL)
    if not json_match:
        yield {"type": "result", "data": _fout_resultaat("Model gaf geen geldig JSON-antwoord.")}
        return

    try:
        yield {"type": "result", "data": json.loads(json_match.group())}
    except json.JSONDecodeError:
        yield {"type": "result", "data": _fout_resultaat("Model gaf ongeldig JSON-antwoord.")}


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
    parser.add_argument("--modus", choices=["quick_scan", "diepte_analyse"], default=None,
                        help="Match-modus: quick_scan (snel), diepte_analyse (uitgebreid)")
    args = parser.parse_args()

    # Controleer of mappen bestaan
    for pad, label in [(KANDIDATEN_DIR, "Kandidaten-map"), (WERKGEVERSVRAGEN_DIR, "Werkgeversvragen-map")]:
        if not os.path.isdir(pad):
            print(f"Fout: {label} niet gevonden: {pad}", file=sys.stderr)
            sys.exit(1)

    # Maak rapportmap aan als die niet bestaat
    os.makedirs(RAPPORT_DIR, exist_ok=True)

    # Lees bestanden (nu via mappenlijst)
    cvs = lijst_mappen(KANDIDATEN_DIR)
    if args.cv:
        cvs = [m for m in cvs if m == args.cv]
        
    vacatures = lijst_mappen(WERKGEVERSVRAGEN_DIR)

    if not cvs:
        print(f"Geen CV's gevonden" + (f" (filter: {args.cv})" if args.cv else ""), file=sys.stderr)
        sys.exit(1)
    if not vacatures:
        print("Geen vacatures gevonden", file=sys.stderr)
        sys.exit(1)

    print(f"Gevonden: {len(cvs)} CV('s), {len(vacatures)} vacature(s)\n")
    for cv_map in cvs:
        cv_pad = os.path.join(KANDIDATEN_DIR, cv_map)
        cv_profiel = laad_profiel_uit_map(cv_pad)
        
        if not cv_profiel:
            print(f"Skipping {cv_map} (geen profiel.json in map)", file=sys.stderr)
            continue
            
        naam = cv_profiel.get("naam", cv_map)
        print(f"▶ Analyseren: {naam} ({cv_map})")

        cv_profiel_json = json.dumps(cv_profiel, indent=2, ensure_ascii=False)

        # Parallel matchen: alle vacatures tegelijk
        def _match_vacature(vac_map):
            vac_pad = os.path.join(WERKGEVERSVRAGEN_DIR, vac_map)
            vac_eisen = laad_profiel_uit_map(vac_pad)
            
            if not vac_eisen:
                return vac_map, _fout_resultaat("Geen profiel.json", vac_map)
                
            vac_eisen_json = json.dumps(vac_eisen, indent=2, ensure_ascii=False)
            vac_titel = vac_eisen.get("titel", vac_map)
            resultaat = vraag_ollama(cv_profiel_json, vac_eisen_json, modus=args.modus)
            resultaat["vacature_titel"] = vac_titel
            return vac_titel, resultaat

        matches = []
        with ThreadPoolExecutor(max_workers=min(4, len(vacatures))) as pool:
            futures = {pool.submit(_match_vacature, item): item for item in vacatures}
            for future in as_completed(futures):
                vac_titel, resultaat = future.result()
                matches.append(resultaat)
                print(f"  ↳ vs. {vac_titel}... {resultaat['match_percentage']}%")

        rapport = genereer_rapport(naam, matches)
        print(f"\n{rapport}")

        # Sla rapport op
        rapport_naam = f"rapport_{cv_map}.txt"
        rapport_pad = os.path.join(RAPPORT_DIR, rapport_naam)
        with open(rapport_pad, "w", encoding="utf-8") as f:
            f.write(rapport)
        print(f"💾 Opgeslagen: {rapport_pad}\n")


if __name__ == "__main__":
    main()
