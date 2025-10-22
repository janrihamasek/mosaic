import sqlite3
from pathlib import Path
import os

# resolve paths relative to this script's folder
BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "mosaic.db"
schema_path = BASE_DIR / "schema.sql"

# pokud databáze už existuje, smažeme ji
if db_path.exists():
    os.remove(db_path)
    print(f"🗑️  Starý soubor databáze odstraněn: {db_path}")

# načteme schéma
with schema_path.open("r", encoding="utf-8") as f:
    schema = f.read()

# vytvoříme novou databázi
conn = sqlite3.connect(str(db_path))
conn.executescript(schema)
conn.commit()
conn.close()

print("✅ Databáze byla úspěšně inicializována:", db_path)
