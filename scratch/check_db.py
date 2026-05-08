import sqlite3
from pathlib import Path

db_path = Path("rws.db")
if not db_path.exists():
    print("Error: rws.db not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM runs").fetchall()

for row in rows:
    print(dict(row))

conn.close()
