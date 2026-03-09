"""
Eenmalig migratiescript: scrub PII uit bestaande ruwe_tekst in de documenten-tabel.

Gebruik:
    python scripts/scrub_bestaande_pii.py [--dry-run]
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import _get_connection
from backend.services.pii_scrubber import scrub_pii


async def scrub_bestaande_documenten(dry_run: bool = False):
    conn = await _get_connection()
    try:
        cursor = await conn.execute("SELECT document_id, naam, ruwe_tekst FROM documenten WHERE ruwe_tekst IS NOT NULL AND ruwe_tekst != ''")
        rows = await cursor.fetchall()

        geschoond_count = 0
        for row in rows:
            doc_id = row["document_id"]
            naam = row["naam"]
            tekst = row["ruwe_tekst"]

            geschoond, rapport = scrub_pii(tekst)
            if rapport:
                print(f"  {naam}: PII gevonden en gemaskeerd — {rapport}")
                geschoond_count += 1
                if not dry_run:
                    await conn.execute(
                        "UPDATE documenten SET ruwe_tekst = ? WHERE document_id = ?",
                        (geschoond, doc_id),
                    )

        if not dry_run and geschoond_count > 0:
            await conn.commit()

        print(f"\nKlaar. {geschoond_count}/{len(rows)} documenten {'zouden worden ' if dry_run else ''}geschoond.")
        if dry_run:
            print("(Dry-run modus — geen wijzigingen opgeslagen. Draai zonder --dry-run om echt te scrubben.)")
    finally:
        await conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(scrub_bestaande_documenten(dry_run=dry_run))
