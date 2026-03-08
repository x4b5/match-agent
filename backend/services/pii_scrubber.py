"""
PII Scrubber – maskeert persoonlijk identificeerbare informatie (PII)
voordat tekst naar het LLM wordt gestuurd.

Detecteert en maskeert:
- BSN (Burgerservicenummer)
- E-mailadressen
- Telefoonnummers (NL formaten)
- IBAN-nummers
- Postcodes (NL)
- Geboortedata (diverse formaten)
"""
import re
from typing import Tuple

# ── Regex patronen voor veelvoorkomende PII in Nederlandse context ──

PATRONEN: list[Tuple[str, str, str]] = [
    # BSN: 8 of 9 cijfers (standalone)
    (r'\b\d{9}\b', '[BSN-VERWIJDERD]', 'bsn'),
    (r'\b\d{3}[\.\-]\d{3}[\.\-]\d{3}\b', '[BSN-VERWIJDERD]', 'bsn'),
    
    # E-mail
    (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-VERWIJDERD]', 'email'),
    
    # Telefoonnummer (NL)
    (r'\b(?:\+31|0031|0)\s?[1-9](?:[\s\-]?\d){8}\b', '[TELEFOON-VERWIJDERD]', 'telefoon'),
    (r'\b06[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}\b', '[TELEFOON-VERWIJDERD]', 'telefoon'),
    
    # IBAN
    (r'\b[A-Z]{2}\d{2}\s?[A-Z]{4}\s?\d{4}\s?\d{4}\s?\d{2,4}\b', '[IBAN-VERWIJDERD]', 'iban'),
    
    # Postcode (NL)
    (r'\b\d{4}\s?[A-Z]{2}\b', '[POSTCODE-VERWIJDERD]', 'postcode'),
    
    # Geboortedatum (dd-mm-yyyy, dd/mm/yyyy, dd.mm.yyyy)
    (r'\b\d{2}[\-/\.]\d{2}[\-/\.]\d{4}\b', '[DATUM-VERWIJDERD]', 'datum'),
]

def scrub_pii(tekst: str) -> Tuple[str, dict]:
    """
    Maskeert PII in de gegeven tekst.
    
    Returns:
        Tuple van (geschoonde_tekst, rapport) waar rapport een dict is met
        het aantal gevonden en gemaskeerde items per categorie.
    """
    rapport = {}
    geschoond = tekst
    
    for patroon, vervanging, categorie in PATRONEN:
        matches = re.findall(patroon, geschoond)
        if matches:
            rapport[categorie] = rapport.get(categorie, 0) + len(matches)
            geschoond = re.sub(patroon, vervanging, geschoond)
    
    return geschoond, rapport

def heeft_pii(tekst: str) -> bool:
    """Snelle check of een tekst PII bevat."""
    for patroon, _, _ in PATRONEN:
        if re.search(patroon, tekst):
            return True
    return False
