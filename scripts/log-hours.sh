#!/bin/bash
# Berekent gewerkte uren sinds start-day.sh en logt ze in LOGBOOK.md
# Aangeroepen door .githooks/post-commit

TIMESTAMP_FILE=".day-start"
LOGBOOK="LOGBOOK.md"

if [ ! -f "$TIMESTAMP_FILE" ]; then
  echo "Geen starttijd gevonden. Draai eerst: bash start-day.sh"
  exit 0
fi

START=$(cat "$TIMESTAMP_FILE")
NOW=$(date +%s)
DIFF=$((NOW - START))
HOURS=$(echo "scale=1; $DIFF / 3600" | bc)
TODAY=$(date '+%Y-%m-%d')
DESCRIPTION=$(git log -1 --pretty=format:'%s' 2>/dev/null || echo "werk")

# Controleer of er vandaag al een entry is
if grep -q "$TODAY" "$LOGBOOK" 2>/dev/null; then
  # Update bestaande entry: vervang de regel
  sed -i '' "s/| $TODAY .*/| $TODAY | $HOURS   | $DESCRIPTION |/" "$LOGBOOK"
else
  # Voeg nieuwe entry toe (voor de lege regel aan het eind van de tabel)
  sed -i '' "/^|            |      |/i\\
| $TODAY | $HOURS   | $DESCRIPTION |
" "$LOGBOOK"
fi

echo "Uren gelogd: ${HOURS}h — $DESCRIPTION"
