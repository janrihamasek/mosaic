import csv
import os
import sqlite3
from datetime import datetime
from typing import Optional

# Cesta k databázi (shodná s app.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "../database/mosaic.db")


def ensure_schema(conn):
    cursor = conn.execute("PRAGMA table_info(activities)")
    columns = {row[1] for row in cursor.fetchall()}
    if "category" not in columns:
        conn.execute("ALTER TABLE activities ADD COLUMN category TEXT NOT NULL DEFAULT ''")
        conn.commit()


def get_db_connection(db_path: Optional[str] = None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def ensure_activity_exists(conn, activity_name, category="", description=""):
    cur = conn.execute(
        "SELECT id, category, description FROM activities WHERE name = ?", (activity_name,)
    )
    row = cur.fetchone()
    if row:
        updates = []
        params = []
        if category and (row["category"] or "") != category:
            updates.append("category = ?")
            params.append(category)
        if description and (row["description"] or "") != description:
            updates.append("description = ?")
            params.append(description)
        if updates:
            params.append(activity_name)
            conn.execute(f"UPDATE activities SET {', '.join(updates)} WHERE name = ?", params)
            conn.commit()
        return

    conn.execute(
        "INSERT INTO activities (name, category, description, active) VALUES (?, ?, ?, 1)",
        (activity_name, category, description),
    )
    print(f"✅ Přidána nová aktivita: {activity_name}")
    conn.commit()


def import_csv(csv_path, db_path: Optional[str] = None):
    conn = get_db_connection(db_path)
    created = 0
    updated = 0
    skipped = 0
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_date = row.get("date")
            activity = row.get("activity")
            value_raw = row.get("value", 0)
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                print(f"⚠️ Neplatná hodnota value '{value_raw}' – řádek přeskočen")
                skipped += 1
                continue
            note = (row.get("note", "") or "").strip()
            desc = (row.get("description", "") or "").strip()
            category = (row.get("category", "") or "").strip()
            activity = (activity or "").strip()

            if not raw_date or not activity:
                print(f"⚠️ Přeskočeno – chybí date nebo activity: {row}")
                skipped += 1
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
                skipped += 1
                continue
            # ----------------------------------------------------

            ensure_activity_exists(conn, activity, category, desc)

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
                created += 1
            else:
                print(f"🔄 Aktualizováno: {date} | {activity}")
                updated += 1
        conn.commit()
    conn.close()
    summary = {"created": created, "updated": updated, "skipped": skipped}
    print(f"🎯 Import dokončen. Vytvořeno: {created}, aktualizováno: {updated}, přeskočeno: {skipped}")
    return summary


if __name__ == "__main__":
    CSV_PATH = os.path.join(os.path.dirname(__file__), "data_for_mosaic - january.csv")
    import_csv(CSV_PATH)
