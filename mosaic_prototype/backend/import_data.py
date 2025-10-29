import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional

# Cesta k databázi (shodná s app.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "../database/mosaic.db")


def ensure_schema(conn):
    cursor = conn.execute("PRAGMA table_info(activities)")
    columns_info = cursor.fetchall()
    column_names = {row[1] for row in columns_info}
    goal_info = next((row for row in columns_info if row[1] == "goal"), None)
    goal_type = goal_info[2].upper() if goal_info and goal_info[2] else None

    has_freq_day = "frequency_per_day" in column_names
    has_freq_week = "frequency_per_week" in column_names

    if goal_type and goal_type != "REAL":
        category_select = "IFNULL(category, '')" if "category" in column_names else "''"
        description_select = "description" if "description" in column_names else "NULL"
        active_select = "IFNULL(active, 1)" if "active" in column_names else "1"
        freq_day_select = "frequency_per_day" if has_freq_day else "1"
        freq_week_select = "frequency_per_week" if has_freq_week else "1"
        deactivated_select = "deactivated_at" if "deactivated_at" in column_names else "NULL"
        conn.executescript(
            f"""
            ALTER TABLE activities RENAME TO activities_old;
            CREATE TABLE activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT '',
                goal REAL NOT NULL DEFAULT 0,
                description TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                frequency_per_day INTEGER NOT NULL DEFAULT 1,
                frequency_per_week INTEGER NOT NULL DEFAULT 1,
                deactivated_at TEXT
            );
            INSERT INTO activities (id, name, category, goal, description, active, frequency_per_day, frequency_per_week, deactivated_at)
            SELECT id,
                   name,
                   {category_select},
                   CAST(goal AS REAL),
                   {description_select},
                   {active_select},
                   {freq_day_select},
                   {freq_week_select},
                   {deactivated_select}
            FROM activities_old;
            DROP TABLE activities_old;
            """
        )
        conn.commit()
        cursor = conn.execute("PRAGMA table_info(activities)")
        columns_info = cursor.fetchall()
        column_names = {row[1] for row in columns_info}

    if "category" not in column_names:
        conn.execute("ALTER TABLE activities ADD COLUMN category TEXT NOT NULL DEFAULT ''")
        conn.commit()
    if "goal" not in column_names:
        conn.execute("ALTER TABLE activities ADD COLUMN goal REAL NOT NULL DEFAULT 0")
        conn.commit()
    if "frequency_per_day" not in column_names:
        conn.execute("ALTER TABLE activities ADD COLUMN frequency_per_day INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    if "frequency_per_week" not in column_names:
        conn.execute("ALTER TABLE activities ADD COLUMN frequency_per_week INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    if "deactivated_at" not in column_names:
        conn.execute("ALTER TABLE activities ADD COLUMN deactivated_at TEXT")
        conn.commit()

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


def get_db_connection(db_path: Optional[str] = None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


@contextmanager
def db_transaction(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = get_db_connection(db_path)
    try:
        conn.execute("BEGIN")
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


def ensure_activity_exists(conn, activity_name, category="", description="", goal=0.0,
                           frequency_per_day=1, frequency_per_week=1):
    cur = conn.execute(
        "SELECT id, category, description, goal, frequency_per_day, frequency_per_week, deactivated_at FROM activities WHERE name = ?",
        (activity_name,),
    )
    row = cur.fetchone()
    if row:
        row_dict = dict(row)
        updates = []
        params = []
        if category and (row_dict.get("category") or "") != category:
            updates.append("category = ?")
            params.append(category)
        if description and (row_dict.get("description") or "") != description:
            updates.append("description = ?")
            params.append(description)
        if goal is not None and float(row_dict.get("goal", 0)) != float(goal):
            updates.append("goal = ?")
            params.append(goal)
        if row_dict.get("frequency_per_day") != frequency_per_day:
            updates.append("frequency_per_day = ?")
            params.append(frequency_per_day)
        if row_dict.get("frequency_per_week") != frequency_per_week:
            updates.append("frequency_per_week = ?")
            params.append(frequency_per_week)
        if updates:
            params.append(activity_name)
            conn.execute(f"UPDATE activities SET {', '.join(updates)} WHERE name = ?", params)
        return

    conn.execute(
        """
        INSERT INTO activities (name, category, goal, description, active, frequency_per_day, frequency_per_week, deactivated_at)
        VALUES (?, ?, ?, ?, 1, ?, ?, NULL)
        """,
        (activity_name, category, goal, description, frequency_per_day, frequency_per_week),
    )
    print(f"✅ Přidána nová aktivita: {activity_name}")


def import_csv(csv_path, db_path: Optional[str] = None):
    created = 0
    updated = 0
    skipped = 0
    with db_transaction(db_path) as conn:
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
                goal_raw = (row.get("goal", "0") or "0").strip()
                try:
                    goal = float(goal_raw or "0")
                except (TypeError, ValueError):
                    print(f"⚠️ Neplatná hodnota goal '{goal_raw}' – řádek přeskočen")
                    skipped += 1
                    continue
                activity = (activity or "").strip()

                if not raw_date or not activity:
                    print(f"⚠️ Přeskočeno – chybí date nebo activity: {row}")
                    skipped += 1
                    continue

                date = raw_date.strip()
                try:
                    if "/" in date:
                        date = datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")
                    else:
                        datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    print(f"⚠️ Neplatné datum: {raw_date}")
                    skipped += 1
                    continue

                ensure_activity_exists(conn, activity, category, desc, goal)

                cur = conn.execute(
                    """
                    UPDATE entries
                    SET value = ?,
                        note = ?,
                        description = ?,
                        activity_category = ?,
                        activity_goal = ?
                    WHERE date = ? AND activity = ?
                    """,
                    (value, note, desc, category, goal, date, activity)
                )
                if cur.rowcount == 0:
                    conn.execute(
                        """
                        INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (date, activity, desc, value, note, category, goal)
                    )
                    print(f"🆕 Nový záznam: {date} | {activity} | {value} | {note}")
                    created += 1
                else:
                    print(f"🔄 Aktualizováno: {date} | {activity}")
                    updated += 1
    summary = {"created": created, "updated": updated, "skipped": skipped}
    print(f"🎯 Import dokončen. Vytvořeno: {created}, aktualizováno: {updated}, přeskočeno: {skipped}")
    return summary


if __name__ == "__main__":
    CSV_PATH = os.path.join(os.path.dirname(__file__), "data_for_mosaic - january.csv")
    import_csv(CSV_PATH)
