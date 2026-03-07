import os
import glob
import json
import requests
from datetime import datetime
from config import (
    OLLAMA_URL, 
    PROFIEL_MODEL, 
    SYSTEM_PROMPT, 
    PROFIEL_KANDIDAAT_PROMPT, 
    PROFIEL_WERKGEVERSVRAAG_PROMPT
)

def _vraag_ollama_profiel(prompt: str) -> dict:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": PROFIEL_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,  # Lage temperatuur voor consistente data extractie
                    "num_predict": 1024,
                },
                "think": False,
            },
            timeout=300,
        )
        response.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Fout bij profiel extractie: {e}")
        return {}

    antwoord = response.json().get("response", "")
    import re
    json_match = re.search(r"\{.*\}", antwoord, re.DOTALL)
    if not json_match:
        return {}
    
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return {}

def profileer_kandidaat(tekst: str) -> dict:
    """Zet ruwe kandidaattekst om naar gestandaardiseerd profiel via LLM."""
    prompt = PROFIEL_KANDIDAAT_PROMPT.format(tekst=tekst)
    return _vraag_ollama_profiel(prompt)

def profileer_werkgeversvraag(tekst: str) -> dict:
    """Zet ruwe werkgeversvraag om naar gestandaardiseerd profiel via LLM."""
    prompt = PROFIEL_WERKGEVERSVRAAG_PROMPT.format(tekst=tekst)
    return _vraag_ollama_profiel(prompt)

def vind_meest_recente_profiel(map_pad: str) -> str | None:
    """Vindt het meest recente .json bestand in de map."""
    zoekpad = os.path.join(map_pad, "*.json")
    bestanden = glob.glob(zoekpad)
    if not bestanden:
        return None
    return max(bestanden, key=os.path.getmtime)

def laad_profiel_uit_map(map_pad: str) -> dict | None:
    """Laad het meest recente profiel (.json) uit een specifieke map, indien aanwezig."""
    profiel_pad = vind_meest_recente_profiel(map_pad)
    if profiel_pad and os.path.exists(profiel_pad):
        try:
            with open(profiel_pad, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Fout bij lezen {profiel_pad}: {e}")
    return None

def genereer_profiel_voor_map(map_pad: str, profileer_fn) -> dict | None:
    """
    Lees alle .txt en .docx bestanden in de map, plak ze aan elkaar, 
    stuur naar Ollama, en sla het resultaat op als <mapnaam>_<tijdstempel>.json in de map.
    """
    if not os.path.isdir(map_pad):
        print(f"Fout: {map_pad} is geen map.")
        return None
        
    gecombineerde_tekst = ""
    baseless_bestanden = os.listdir(map_pad)
    tekst_extensies = (".txt", ".md", ".csv", ".eml", ".json", ".log", ".rtf")
    verwerkbare_bestanden = [f for f in baseless_bestanden if f.lower().endswith(tekst_extensies) or f.lower().endswith(".docx") or f.lower().endswith(".pdf")]
    
    if not verwerkbare_bestanden:
        print(f"Geen leesbare bestanden gevonden in {map_pad}")
        return None
        
    for doc in sorted(verwerkbare_bestanden):
        pad = os.path.join(map_pad, doc)
        gecombineerde_tekst += f"\n\n--- Inhoud uit {doc} ---\n\n"
        try:
            if doc.lower().endswith(tekst_extensies):
                with open(pad, "r", encoding="utf-8") as f:
                    gecombineerde_tekst += f.read()
            elif doc.endswith(".docx"):
                try:
                    from docx import Document
                    document = Document(pad)
                    voor_docx = "\\n".join([p.text for p in document.paragraphs])
                    gecombineerde_tekst += voor_docx
                except ImportError:
                    print("Fout: python-docx module is niet geïnstalleerd. Kan .docx niet lezen.")
                    gecombineerde_tekst += "[Kon .docx niet uitlezen: module docx ontbreekt]"
            elif doc.endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(pad)
                    voor_pdf = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            voor_pdf += text + "\\n"
                    gecombineerde_tekst += voor_pdf
                except ImportError:
                    print("Fout: pypdf module is niet geïnstalleerd. Kan .pdf niet lezen.")
                    gecombineerde_tekst += "[Kon .pdf niet uitlezen: module pypdf ontbreekt]"
        except Exception as e:
            print(f"Kon {pad} niet lezen: {e}")
            
    if not gecombineerde_tekst.strip():
        print(f"Geen leesbare tekst in {map_pad}")
        return None
        
    profiel = profileer_fn(gecombineerde_tekst)
    
    if profiel:
        map_naam = os.path.basename(os.path.normpath(map_pad))
        tijdstempel = datetime.now().strftime("%Y%m%d_%H%M%S")
        profiel_naam = f"{map_naam}_{tijdstempel}.json"
        profiel_pad = os.path.join(map_pad, profiel_naam)
        try:
            with open(profiel_pad, "w", encoding="utf-8") as f:
                json.dump(profiel, f, ensure_ascii=False, indent=2)
            return profiel
        except Exception as e:
            print(f"Kon {profiel_pad} niet opslaan: {e}")
            
    return None
