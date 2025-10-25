import csv
import sqlite3
import os
from datetime import datetime

# Cesta k databázi (shodná s app.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "../database/mosaic.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_activity_exists(conn, activity_name, description=""):
    cur = conn.execute("SELECT id FROM activities WHERE name = ?", (activity_name,))
    if not cur.fetchone():
        conn.execute(
            "INSERT INTO activities (name, description, active) VALUES (?, ?, 1)",
            (activity_name, description)
        )
        print(f"✅ Přidána nová aktivita: {activity_name}")
        conn.commit()

def import_csv(csv_path):
    conn = get_db_connection()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_date = row.get("date")
            activity = row.get("activity")
            value = row.get("value", 0)
            note = row.get("note", "")
            desc = row.get("description", "")

            if not raw_date or not activity:
                print(f"⚠️ Přeskočeno – chybí date nebo activity: {row}")
                continue

            # --- převod datumu na jednotný formát YYYY-MM-DD ---
            date = raw_date.strip()
            try:
                # pokud je ve formátu DD/MM/YYYY → převést
                if "/" in date:
                    date = datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")
                else:
                    # pokus o validaci formátu YYYY-MM-DD
                    datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                print(f"⚠️ Neplatné datum: {raw_date}")
                continue
            # ----------------------------------------------------

            ensure_activity_exists(conn, activity, desc)

            cur = conn.execute(
                "UPDATE entries SET value = ?, note = ?, description = ? WHERE date = ? AND activity = ?",
                (value, note, desc, date, activity)
            )
            if cur.rowcount == 0:
                conn.execute(
                    "INSERT INTO entries (date, activity, description, value, note) VALUES (?, ?, ?, ?, ?)",
                    (date, activity, desc, value, note)
                )
                print(f"🆕 Nový záznam: {date} | {activity} | {value} | {note}")
            else:
                print(f"🔄 Aktualizováno: {date} | {activity}")
        conn.commit()
    conn.close()
    print("🎯 Import dokončen.")


if __name__ == "__main__":
    CSV_PATH = os.path.join(os.path.dirname(__file__), "data_for_mosaic - january.csv")
    import_csv(CSV_PATH)
