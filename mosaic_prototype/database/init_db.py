import sqlite3
from pathlib import Path

# resolve paths relative to this script's folder
BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "mosaic.db"
schema_path = BASE_DIR / "schema.sql"

# read schema
with schema_path.open("r", encoding="utf-8") as f:
    schema = f.read()

# connect and initialize
conn = sqlite3.connect(str(db_path))
conn.executescript(schema)
conn.commit()
conn.close()

print("✅ Databáze byla úspěšně inicializována:", db_path)
