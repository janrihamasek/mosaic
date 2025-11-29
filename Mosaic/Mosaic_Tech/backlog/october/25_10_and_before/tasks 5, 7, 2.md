# Daily Log – 2024-10-25

- Date: 2024-10-25
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: tasks 5, 7, 2.md

## Notes (raw import)

## 5 Error reporting
The code returns SQLite error text as JSON on OperationalError. Do not expose raw DB errors in a public production service.

Když aplikace vrací přímo text chyb z databáze prozrazuje strukturu databáze a kód, což je v produkčním prostředí velké riziko.   

Řešení:
Vytvořit pomocnou funkci pro jednotnou odpověď na chyby:

```python
def handle_db_error(e):
    app.logger.error(f"Database error: {e}")
    return jsonify({"error": "A database error occurred."}), 500
```

a pak ji používat na všech místech, kde se pracuje s DB:

```python
try:
    # DB operace
except sqlite3.OperationalError as e:
    return handle_db_error(e)
```

## 7 Move DB path 
and other settings into a config or environment variables (e.g., via `FLASK_ENV` or a `.env` file).

**Problém současného přístupu**
Pokud je teď v kódu něco jako:

```python
DB_PATH = "mosaic.db"
```

nebo dokonce přímo v `get_db_connection()`:

```python
conn = sqlite3.connect("mosaic.db")
```

pak:
- musíš měnit kód, když chceš použít jinou databázi (např. testovací),
- hrozí, že si omylem smažeš produkční data,
- a nejde snadno nasadit aplikaci na jiný server.

**Lepší přístup – konfigurace přes `.env`**
Použij balíček [`python-dotenv`](https://pypi.org/project/python-dotenv/), který načte proměnné z `.env` souboru.
#### 1. Nainstaluj
```bash
pip install python-dotenv
```
#### 2. Vytvoř soubor `.env`
```env
FLASK_ENV=development
DATABASE_URL=sqlite:///mosaic.db
SECRET_KEY=super-secret-key
```
#### 3. Načti konfiguraci v `app.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()  # načte .env soubor

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///mosaic.db")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key")
ENV = os.getenv("FLASK_ENV", "production")
```
Prostý SQLite soubor lze zjednodušit:
```python
DB_PATH = os.getenv("DB_PATH", "mosaic.db")
```
a pak:
```python
conn = sqlite3.connect(DB_PATH)
```

**Pro Mosaic konkrétně**

Zatím bude stačit jednoduché rozdělení:

| Prostředí   | Soubor DB         | Cíl                  |
| ----------- | ----------------- | -------------------- |
| Development | `mosaic.db`       | běžné používání      |
| Test        | `test.db`         | automatizované testy |
| Production  | `/data/mosaic.db` | nasazení online      |
## 2. Database access:
- `get_db_connection()` opens a new sqlite3 connection and sets `row_factory` to `sqlite3.Row` so results can be converted to dicts. 
- The code uses parameterized queries (`?` placeholders), which prevents SQL injection. 
- SQLite has concurrency limits. For higher load or multi-process deployments use a more robust RDBMS or a correctly configured connection pool and WSGI server.

Tohle jsou tři velmi podstatné body — každý se týká jiné části práce s databází.
- **Funkce `get_db_connection()`**  
To, že nastavuje `row_factory = sqlite3.Row`, je výborné — díky tomu se výsledky dotazů chovají jako slovníky (můžeš přistupovat ke sloupcům podle názvů místo indexů). To výrazně zjednodušuje práci s daty a je to dobrá praxe.
	- *Tedy je to v pořádku?*
- **Používání parametrizovaných dotazů (`?`)**  
Toto je naprosto správný způsob, jak zabránit SQL injection. Kdybys místo toho skládal SQL dotaz jako řetězec, riskoval bys, že uživatel vloží do vstupu škodlivý kód. Takže tohle je perfektní.
	- *Jak se to děje nyní?*
- **Omezení SQLite při vícenásobném přístupu (concurrency)**  
SQLite je ideální pro malé projekty, vývoj, nebo aplikace s jedním uživatelem (např. lokální deník aktivit jako Mosaic v rané fázi).  

Ale pokud bys spustil backend jako více procesů (např. přes Gunicorn nebo uvicorn workers), nebo měl více uživatelů zapisujících zároveň, tak by SQLite mohl začít házet chyby typu _database is locked_.

 **Doporučení do budoucna:**
- Pro lehkou víceuživatelskou verzi můžeš zkusit přidat _connection pooling_ (např. pomocí SQLAlchemy).
- Pro produkční server nebo cloudové nasazení je lepší přejít na PostgreSQL nebo MariaDB/MySQL.
- Když zůstaneš u SQLite, dá se aspoň přepnout do WAL režimu (Write-Ahead Logging):
 
    ```sql
    PRAGMA journal_mode = WAL;
    ```
Tím se zlepší výkon a částečně i paralelní přístup.
- *Potřebujeme nyní zvyšovat výkon?*

**Doporučení pro Mosaic teď:**
Pro současný účel (sledování aktivit, osobní aplikace) je SQLite naprosto dostačující.  
Počítám s tím, že **Mosaic by časem mohl mít více uživatelů nebo mobilní verzi se synchronizací**, proto stojí za to:
- psát SQL dotazy přes jednoduché rozhraní (`db.query(...)`, `db.insert(...)`),
- a ukládat veškerý kód související s databází do jednoho modulu.
Díky tomu bude přechod na PostgreSQL v budoucnu v řádu **jednoho víkendu**.
- *Dělá se to nyní takto?*