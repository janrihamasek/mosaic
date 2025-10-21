import sqlite3
from pathlib import Path

# Cesty k databázi a schématu
BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "mosaic.db"
schema_path = BASE_DIR / "schema.sql"

# Načtení SQL schématu
with schema_path.open("r", encoding="utf-8") as f:
    schema = f.read()

# Připojení k databázi
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Kontrola, zda DB existuje a jaké má tabulky
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
existing_tables = {row[0] for row in cursor.fetchall()}

# Zpracování jednotlivých CREATE TABLE příkazů ze schématu
# a spuštění jen těch, které chybí
created_tables = []
for statement in schema.split(";"):
    stmt = statement.strip()
    if not stmt.upper().startswith("CREATE TABLE"):
        continue
    # z názvu tabulky vytáhneme identifikátor
    try:
        table_name = stmt.split("TABLE")[1].split("(")[0].strip().replace("IF NOT EXISTS", "").strip()
    except Exception:
        table_name = "unknown"
    if table_name and table_name not in existing_tables:
        cursor.execute(stmt + ";")
        created_tables.append(table_name)

conn.commit()
conn.close()

if created_tables:
    print("✅ Přidány nové tabulky:", ", ".join(created_tables))
else:
    print("ℹ️  Databáze již obsahuje všechny tabulky – žádná změna nebyla provedena.")

print("📁 Cesta k databázi:", db_path)
