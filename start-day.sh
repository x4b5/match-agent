#!/bin/bash
# Registreert het starttijdstip van de werkdag
# Wordt gebruikt door scripts/log-hours.sh om uren te berekenen

TIMESTAMP_FILE=".day-start"

echo "$(date +%s)" > "$TIMESTAMP_FILE"
echo "Werkdag gestart om $(date '+%H:%M') — succes!"
echo "Tip: commit regelmatig, uren worden automatisch gelogd via post-commit hook."
