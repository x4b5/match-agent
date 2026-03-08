"""
PII Scrubber – maskeert persoonlijk identificeerbare informatie (PII)
voordat tekst naar het LLM wordt gestuurd.

Detecteert en maskeert:
- BSN (Burgerservicenummer) — met elfproef validatie
- E-mailadressen
- Telefoonnummers (NL formaten)
- IBAN-nummers
- Postcodes (NL)
- Geboortedata (diverse formaten)
"""
import re
from typing import Tuple


def _is_geldig_bsn(nummer: str) -> bool:
    """
    Valideer een BSN met de elfproef (11-proef).
    Een geldig BSN heeft 8 of 9 cijfers en voldoet aan:
    (9*d1 + 8*d2 + 7*d3 + 6*d4 + 5*d5 + 4*d6 + 3*d7 + 2*d8 - 1*d9) % 11 == 0
    waarbij het resultaat niet 0 mag zijn door alleen nullen.
    """
    # Strip formatting
    cijfers = re.sub(r'[\.\-\s]', '', nummer)
    
    if len(cijfers) == 8:
        cijfers = '0' + cijfers
    
    if len(cijfers) != 9 or not cijfers.isdigit():
        return False
    
    # Allemaal nullen is geen geldig BSN
    if cijfers == '000000000':
        return False
    
    # Elfproef berekening
    gewichten = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    totaal = sum(int(d) * w for d, w in zip(cijfers, gewichten))
    
    return totaal % 11 == 0 and totaal != 0


# ── Regex patronen voor veelvoorkomende PII in Nederlandse context ──

# BSN patronen (worden later gevalideerd met elfproef)
BSN_PATRONEN = [
    r'\b\d{9}\b',
    r'\b\d{3}[\.\-]\d{3}[\.\-]\d{3}\b',
]

PATRONEN: list[Tuple[str, str, str]] = [
    # E-mail
    (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-VERWIJDERD]', 'email'),
    
    # Telefoonnummer (NL) — diverse formaten
    (r'(?:\+31|0031)\s?[1-9](?:[\s\-]?\d){8}', '[TELEFOON-VERWIJDERD]', 'telefoon'),
    (r'\b06[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}\b', '[TELEFOON-VERWIJDERD]', 'telefoon'),
    (r'\b0[1-9][\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}[\s\-]?\d{2}\b', '[TELEFOON-VERWIJDERD]', 'telefoon'),
    
    # IBAN
    (r'\b[A-Z]{2}\d{2}\s?[A-Z]{4}\s?\d{4}\s?\d{4}\s?\d{2,4}\b', '[IBAN-VERWIJDERD]', 'iban'),
    
    # Postcode (NL)
    (r'\b\d{4}\s?[A-Z]{2}\b', '[POSTCODE-VERWIJDERD]', 'postcode'),
    
    # Geboortedatum (dd-mm-yyyy, dd/mm/yyyy, dd.mm.yyyy)
    (r'\b\d{2}[\-/\.]\d{2}[\-/\.]\d{4}\b', '[DATUM-VERWIJDERD]', 'datum'),
]


def _scrub_bsn(tekst: str) -> Tuple[str, int]:
    """Scrub BSN-nummers met elfproef validatie. Retourneert (geschoonde_tekst, aantal_gevonden)."""
    aantal = 0
    
    for patroon in BSN_PATRONEN:
        def vervang_als_geldig(match):
            nonlocal aantal
            if _is_geldig_bsn(match.group()):
                aantal += 1
                return '[BSN-VERWIJDERD]'
            return match.group()  # Niet vervangen als het geen geldig BSN is
        
        tekst = re.sub(patroon, vervang_als_geldig, tekst)
    
    return tekst, aantal


def scrub_pii(tekst: str) -> Tuple[str, dict]:
    """
    Maskeert PII in de gegeven tekst.
    
    Returns:
        Tuple van (geschoonde_tekst, rapport) waar rapport een dict is met
        het aantal gevonden en gemaskeerde items per categorie.
    """
    rapport = {}
    geschoond = tekst
    
    # BSN scrubbing met elfproef (eerst, voordat andere patronen cijfers matchen)
    geschoond, bsn_aantal = _scrub_bsn(geschoond)
    if bsn_aantal > 0:
        rapport['bsn'] = bsn_aantal
    
    # Overige PII patronen
    for patroon, vervanging, categorie in PATRONEN:
        matches = re.findall(patroon, geschoond)
        if matches:
            rapport[categorie] = rapport.get(categorie, 0) + len(matches)
            geschoond = re.sub(patroon, vervanging, geschoond)
    
    return geschoond, rapport


def heeft_pii(tekst: str) -> bool:
    """Snelle check of een tekst PII bevat."""
    for patroon in BSN_PATRONEN:
        matches = re.finditer(patroon, tekst)
        for match in matches:
            if _is_geldig_bsn(match.group()):
                return True
    
    for patroon, _, _ in PATRONEN:
        if re.search(patroon, tekst):
            return True
    return False
