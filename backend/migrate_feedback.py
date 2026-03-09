import sqlite3
import os

db_path = os.path.expanduser('~/Library/Application Support/matchflix/matchflix.db')
conn = sqlite3.connect(db_path)
try:
    conn.execute('ALTER TABLE matches ADD COLUMN feedback_tekst TEXT')
    print('Added feedback_tekst')
except Exception as e:
    print(f'feedback_tekst likely exists')

try:
    conn.execute('ALTER TABLE matches ADD COLUMN feedback_verwerkt BOOLEAN DEFAULT 0')
    print('Added feedback_verwerkt')
except Exception as e:
    print(f'feedback_verwerkt likely exists')

conn.commit()
conn.close()
print('Migration script finished')
