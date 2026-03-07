#!/usr/bin/env python3
"""Match-agent: matcht kandidaat-CV's met vacatures via Ollama (Qwen 3.5)."""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import hashlib

from config import (
    KANDIDATEN_DIR,
    MATCH_MODI,
    MATCH_PROMPT,
    OLLAMA_MODEL,
    OLLAMA_URL,
    RAPPORT_DIR,
    SYSTEM_PROMPT,
    WERKGEVERSVRAGEN_DIR,
    CACHE_DIR,
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


def _valideer_resultaat(data: dict) -> bool:
    """Valideer of het match-resultaat een geldig schema heeft."""
    if not isinstance(data, dict):
        return False
    pct = data.get("match_percentage")
    if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
        return False
    if not isinstance(data.get("matchende_punten"), list):
        return False
    if not isinstance(data.get("ontbrekende_punten"), list):
        return False
    return True


def _parse_json_antwoord(antwoord: str) -> dict | None:
    """Probeer JSON te parsen: eerst direct, dan regex fallback."""
    # Probeer direct parsen
    try:
        return json.loads(antwoord)
    except (json.JSONDecodeError, ValueError):
        pass
    # Regex fallback: zoek het grootste JSON-blok
    json_match = re.search(r"\{.*\}", antwoord, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def _verkort_tekst(tekst: str, max_lengte: int) -> tuple[str, bool]:
    """Compact JSON-tekst en geef aan of de tekst nog steeds te lang is.

    Retourneert (tekst, is_afgekapt). Als is_afgekapt=True is de tekst te lang
    zelfs na compact maken en wordt de originele compacte tekst onverkort teruggegeven
    zodat de aanroeper kan beslissen wat te doen (bijv. waarschuwing tonen).
    """
    if len(tekst) <= max_lengte:
        return tekst, False
    # Probeer JSON compact te maken — scheelt ~40-60% ruimte bij indent=2
    try:
        data = json.loads(tekst)
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(compact) <= max_lengte:
            return compact, False
        # Nog steeds te lang na compact maken — geef volledige compacte tekst terug
        return compact, True
    except (json.JSONDecodeError, ValueError):
        pass
    # Geen JSON: geef originele tekst terug en markeer als te lang
    return tekst, True


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
        "think": modi.get("think", False) if modi else False,
    }


def vraag_ollama(cv_tekst: str, vacature_tekst: str, modus: str | None = None, max_retries: int = 1) -> dict:
    """Stuur een prompt naar Ollama en parse het JSON-antwoord. Automatische retry bij ongeldig resultaat."""
    params = _modus_params(modus)
    model = params["model_override"] or OLLAMA_MODEL
    
    # Caching check
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = hashlib.md5(f"{cv_tekst}{vacature_tekst}{modus}{model}{SYSTEM_PROMPT}".encode()).hexdigest()
    cache_pad = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_pad):
        try:
            with open(cache_pad, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if params["max_tekst_lengte"]:
        cv_tekst, cv_afgekapt = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, vac_afgekapt = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
        if cv_afgekapt or vac_afgekapt:
            print(f"  ⚠ Profiel te lang voor quick scan — gebruik 'diepte-analyse' voor volledige context", file=sys.stderr)
    model = params["model_override"] or OLLAMA_MODEL
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)

    for poging in range(max_retries + 1):
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
                    "think": params["think"],
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
        resultaat = _parse_json_antwoord(antwoord)

        if resultaat and _valideer_resultaat(resultaat):
            # Zorg dat match_percentage een integer is
            resultaat["match_percentage"] = int(round(resultaat["match_percentage"]))
            # Bewaar in cache voor resultaten van vraag_ollama (CLI / Batch)
            try:
                with open(cache_pad, "w", encoding="utf-8") as f:
                    json.dump(resultaat, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return resultaat

        if poging < max_retries:
            print(f"  ⚠ Ongeldig resultaat, retry ({poging + 1}/{max_retries})...", file=sys.stderr)
            continue

    print(f"  ⚠ Kon geen geldig JSON-resultaat krijgen na {max_retries + 1} pogingen", file=sys.stderr)
    return _fout_resultaat("Model gaf geen geldig JSON-antwoord na meerdere pogingen.")


def vraag_ollama_stream(cv_tekst: str, vacature_tekst: str, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL, temperature: float = 0.3, modus: str | None = None):
    """Streaming-variant van vraag_ollama. Yieldt tekstfragmenten, retourneert uiteindelijk het parsed JSON-resultaat."""
    params = _modus_params(modus)
    model = params["model_override"] or model
    
    # Caching check voor stream
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = hashlib.md5(f"{cv_tekst}{vacature_tekst}{modus}{model}{SYSTEM_PROMPT}".encode()).hexdigest()
    cache_pad = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_pad):
        try:
            with open(cache_pad, "r", encoding="utf-8") as f:
                resultaat = json.load(f)
                yield {"type": "token", "data": "(geladen uit cache)"}
                yield {"type": "result", "data": resultaat}
                return
        except Exception:
            pass

    if params["max_tekst_lengte"]:
        cv_tekst, cv_afgekapt = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, vac_afgekapt = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
        if cv_afgekapt or vac_afgekapt:
            yield {"type": "warning", "data": "Profiel te lang voor quick scan modus — resultaat kan onvolledig zijn. Gebruik 'diepte-analyse' voor volledige context."}
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
                "think": params["think"],
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

    # Parse en valideer het volledige antwoord als JSON
    resultaat = _parse_json_antwoord(volledig_antwoord)
    if resultaat and _valideer_resultaat(resultaat):
        resultaat["match_percentage"] = int(round(resultaat["match_percentage"]))
        # Bewaar in cache
        try:
            with open(cache_pad, "w", encoding="utf-8") as f:
                json.dump(resultaat, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        yield {"type": "result", "data": resultaat}
    elif resultaat:
        # JSON geparsed maar schema klopt niet — laat zien wat we kregen
        pct = resultaat.get("match_percentage")
        reden = f"Ongeldig schema: match_percentage={pct!r}, keys={list(resultaat.keys())}"
        yield {"type": "warning", "data": f"LLM gaf ongeldig antwoord: {reden}"}
        yield {"type": "result", "data": _fout_resultaat(reden)}
    else:
        # Kon helemaal geen JSON parsen
        preview = volledig_antwoord[:300] if volledig_antwoord else "(leeg antwoord)"
        yield {"type": "warning", "data": f"Kon geen JSON parsen uit LLM-antwoord: {preview}"}
        yield {"type": "result", "data": _fout_resultaat("Model gaf geen geldig JSON-antwoord.")}


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
        
        if m.get("verrassings_element"):
            lijnen.append(f"   💡 Verrassend: {m['verrassings_element']}")
        if m.get("cultuur_fit"):
            lijnen.append(f"   🌟 Cultuur fit: {m['cultuur_fit']}")
        if m.get("groeipotentieel"):
            lijnen.append(f"   🌱 Groeipotentieel: {m['groeipotentieel']}")
        if m.get("risico_mitigatie"):
            lijnen.append(f"   🛡️ Risico-mitigatie: {m['risico_mitigatie']}")
        if m.get("aandachtspunten"):
            lijnen.append(f"   ⚠️ Aandachtspunten: {m['aandachtspunten']}")
        if m.get("gedeelde_waarden"):
            lijnen.append("   🤝 Gedeelde waarden:")
            for w in m["gedeelde_waarden"]:
                lijnen.append(f"      - {w}")
        if m.get("gespreksstarters"):
            lijnen.append("   🎤 Gespreksstarters:")
            for idx, vraag in enumerate(m["gespreksstarters"], 1):
                lijnen.append(f"      {idx}. {vraag}")
        if m.get("boodschap_aan_kandidaat"):
            lijnen.append(f"   💬 Boodschap aan kandidaat: {m['boodschap_aan_kandidaat']}")
                
        if m.get("onderbouwing"):
            lijnen.append(f"   → Onderbouwing: {m['onderbouwing']}")
            
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
