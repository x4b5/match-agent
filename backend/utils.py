import os
import shutil
import json
import uuid
import time
from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR
from backend.services.agents import extract_text_sync

def lijst_mappen(directory: str) -> list[str]:
    if not os.path.exists(directory):
        return []
    return [d for d in sorted(os.listdir(directory)) if not d.startswith(".") and os.path.isdir(os.path.join(directory, d))]

def heeft_profiel(directory: str, map_naam: str) -> bool:
    pad = os.path.join(directory, map_naam)
    if not os.path.isdir(pad):
        return False
    return any(f.endswith(".json") for f in os.listdir(pad))

def vind_meest_recente_profiel(map_pad: str) -> str | None:
    import glob
    zoekpad = os.path.join(map_pad, "*.json")
    bestanden = glob.glob(zoekpad)
    if not bestanden:
        return None
    return max(bestanden, key=os.path.getmtime)

def laad_profiel_uit_map(map_pad: str) -> dict | None:
    profiel_pad = vind_meest_recente_profiel(map_pad)
    if profiel_pad and os.path.exists(profiel_pad):
        try:
            with open(profiel_pad, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def opslaan_profiel(map_pad: str, profiel: dict) -> str:
    map_naam = os.path.basename(os.path.normpath(map_pad))
    tijdstempel = time.strftime("%Y%m%d_%H%M%S")
    profiel_naam = f"{map_naam}_{tijdstempel}.json"
    profiel_pad = os.path.join(map_pad, profiel_naam)
    with open(profiel_pad, "w", encoding="utf-8") as f:
        json.dump(profiel, f, ensure_ascii=False, indent=2)
    return profiel_pad

def zorg_voor_uuid(map_pad: str) -> str:
    if not os.path.isdir(map_pad):
        return ""
    uuid_pad = os.path.join(map_pad, "uuid.txt")
    if os.path.exists(uuid_pad):
        try:
            with open(uuid_pad, "r", encoding="utf-8") as f:
                bestaande_uuid = f.read().strip()
                if bestaande_uuid:
                    return bestaande_uuid
        except Exception:
            pass
    nieuwe_uuid = str(uuid.uuid4())
    try:
        with open(uuid_pad, "w", encoding="utf-8") as f:
            f.write(nieuwe_uuid)
    except Exception:
        pass
    return nieuwe_uuid

def lijst_bestanden(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    return sorted([f for f in os.listdir(directory) if not f.startswith(".") and os.path.isfile(os.path.join(directory, f))])

def formatteer_directory_response(base_dir: str):
    mappen = lijst_mappen(base_dir)
    data = []
    for m in mappen:
        pad = os.path.join(base_dir, m)
        docs = [f for f in lijst_bestanden(pad) if not f.endswith(".json")]
        prof_pad = vind_meest_recente_profiel(pad)
        profiel = laad_profiel_uit_map(pad)
        laatst_gen = os.path.getmtime(prof_pad) if prof_pad else 0
        
        uuid_val = zorg_voor_uuid(pad)
            
        data.append({
            "id": uuid_val,
            "naam": m,
            "doc_count": len(docs),
            "docs": docs,
            "has_profile": bool(profiel),
            "profile_score": profiel.get("profiel_betrouwbaarheid", 0) if profiel else 0,
            "last_generated": laatst_gen,
            "profile_data": profiel
        })
    return data
