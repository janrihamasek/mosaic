import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from import_data import import_csv as run_import_csv
from security import (
    ValidationError,
    rate_limit,
    require_api_key,
    validate_activity_create_payload,
    validate_activity_update_payload,
    validate_entry_payload,
)

app = Flask(__name__)
CORS(app)

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "../database/mosaic.db"
DB_PATH = os.environ.get("MOSAIC_DB_PATH") or DEFAULT_DB_PATH
app.config["DB_PATH"] = str(DB_PATH)
app.config["_SCHEMA_READY"] = False
app.config.setdefault(
    "RATE_LIMITS",
    {
        "add_entry": {"limit": 60, "window": 60},
        "add_activity": {"limit": 30, "window": 60},
        "activity_status": {"limit": 60, "window": 60},
        "update_activity": {"limit": 60, "window": 60},
        "delete_activity": {"limit": 30, "window": 60},
        "delete_entry": {"limit": 90, "window": 60},
        "finalize_day": {"limit": 10, "window": 60},
        "import_csv": {"limit": 5, "window": 300},
    },
)
app.config["API_KEY"] = os.environ.get("MOSAIC_API_KEY")
app.config.setdefault("PUBLIC_ENDPOINTS", {"home"})

def ensure_schema(conn):
    if app.config.get("_SCHEMA_READY"):
        return

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
        column_names.add("category")
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

    app.config["_SCHEMA_READY"] = True


def get_db_connection():
    db_path = app.config.get("DB_PATH", str(DB_PATH))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


@app.get("/")
def home():
    return jsonify({"message": "Backend běží!", "database": DB_PATH})


@app.before_request
def _enforce_api_key():
    auth_result = require_api_key()
    if auth_result:
        return auth_result


@app.errorhandler(ValidationError)
def handle_validation(error: ValidationError):
    return jsonify({"error": error.message}), 400


@app.get("/entries")
def get_entries():
    conn = get_db_connection()
    try:
        entries = conn.execute(
            """
            SELECT e.*, IFNULL(a.category, '') AS category, IFNULL(a.goal, 0) AS goal, IFNULL(a.description, '') AS activity_description
            FROM entries e
            LEFT JOIN activities a ON a.name = e.activity
            ORDER BY e.date DESC, a.category ASC, e.activity ASC
            """
        ).fetchall()
        return jsonify([dict(row) for row in entries])
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.post("/add_entry")
def add_entry():
    limits = app.config["RATE_LIMITS"]["add_entry"]
    limited = rate_limit("add_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_entry_payload(data)
    date = payload["date"]
    activity = payload["activity"]
    note = payload["note"]
    float_value = payload["value"]

    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT description FROM activities WHERE name = ?", (activity,))
        desc = cur.fetchone()
        description = desc["description"] if desc else ""

        # 1. Attempt to UPDATE the existing entry (the "upsert" logic)
        cur = conn.execute(
            "UPDATE entries SET value = ?, note = ?, description = ? WHERE date = ? AND activity = ?",
            (float_value, note, description, date, activity),
        )
        conn.commit()

        if cur.rowcount > 0:
            # An entry was updated
            return jsonify({"message": "Záznam aktualizován"}), 200
        else:
            # 2. If no entry was updated, INSERT a new entry
            conn.execute(
                "INSERT INTO entries (date, activity, description, value, note) VALUES (?, ?, ?, ?, ?)",
                (date, activity, description, float_value, note),
            )
            conn.commit()
            return jsonify({"message": "Záznam uložen"}), 201
            
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.delete("/entries/<int:entry_id>")
def delete_entry(entry_id):
    limits = app.config["RATE_LIMITS"]["delete_entry"]
    limited = rate_limit("delete_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    conn = get_db_connection()
    try:
        cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Záznam nenalezen"}), 404
        return jsonify({"message": "Záznam smazán"}), 200
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.get("/activities")
def get_activities():
    show_all = request.args.get("all", "false").lower() in ("1", "true", "yes")
    conn = get_db_connection()
    try:
        if show_all:
            rows = conn.execute(
                "SELECT * FROM activities ORDER BY active DESC, category ASC, name ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activities WHERE active = 1 ORDER BY active DESC, category ASC, name ASC"
            ).fetchall()
        return jsonify([dict(r) for r in rows])
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.post("/add_activity")
def add_activity():
    limits = app.config["RATE_LIMITS"]["add_activity"]
    limited = rate_limit("add_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_activity_create_payload(data)
    name = payload["name"]
    category = payload["category"]
    goal = payload["goal"]
    description = payload["description"]
    frequency_per_day = payload["frequency_per_day"]
    frequency_per_week = payload["frequency_per_week"]

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO activities (name, category, goal, description, frequency_per_day, frequency_per_week, deactivated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (name, category, goal, description, frequency_per_day, frequency_per_week)
        )
        conn.commit()
        return jsonify({"message": "Kategorie přidána"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Kategorie s tímto názvem již existuje"}), 409
    finally:
        conn.close()


@app.put("/activities/<int:activity_id>")
def update_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["update_activity"]
    limited = rate_limit("update_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_activity_update_payload(data)

    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT name FROM activities WHERE id = ?", (activity_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Aktivita nenalezena"}), 404

        update_clauses = []
        params = []
        for key in ("category", "goal", "description", "frequency_per_day", "frequency_per_week"):
            if key in payload:
                update_clauses.append(f"{key} = ?")
                params.append(payload[key])

        if not update_clauses:
            return jsonify({"message": "No changes detected"}), 200

        params.append(activity_id)
        conn.execute(f"UPDATE activities SET {', '.join(update_clauses)} WHERE id = ?", params)

        if "description" in payload:
            conn.execute(
                "UPDATE entries SET description = ? WHERE activity = ?",
                (payload["description"], row["name"]),
            )

        conn.commit()
        return jsonify({"message": "Aktivita aktualizována"}), 200
    finally:
        conn.close()


@app.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_deactivate", limits["limit"], limits["window"])
    if limited:
        return limited
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    try:
        cur = conn.execute(
            "UPDATE activities SET active = 0, deactivated_at = ? WHERE id = ?",
            (deactivation_date, activity_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Aktivita nenalezena"}), 404
        return jsonify({"message": "Aktivita deaktivována"}), 200
    finally:
        conn.close()


@app.patch("/activities/<int:activity_id>/activate")
def activate_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_activate", limits["limit"], limits["window"])
    if limited:
        return limited

    conn = get_db_connection()
    try:
        cur = conn.execute("UPDATE activities SET active = 1, deactivated_at = NULL WHERE id = ?", (activity_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Aktivita nenalezena"}), 404
        return jsonify({"message": "Aktivita aktivována"}), 200
    finally:
        conn.close()


@app.get("/today")
def get_today():
    date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT 
                a.id AS activity_id,
                a.name,
                a.category,
                a.description,
                a.active,
                a.deactivated_at,
                e.id AS entry_id,
                e.value,
                e.note
            FROM activities a
            LEFT JOIN entries e
              ON e.activity = a.name AND e.date = ?
            WHERE a.active = 1
               OR (a.deactivated_at IS NOT NULL AND ? < a.deactivated_at)
            ORDER BY a.name ASC
        """, (date, date)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.delete("/activities/<int:activity_id>")
def delete_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["delete_activity"]
    limited = rate_limit("delete_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    conn = get_db_connection()
    try:
        row = conn.execute("SELECT active FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not row:
            return jsonify({"error": "Aktivita nenalezena"}), 404
        if row["active"] == 1:
            return jsonify({"error": "Aktivitu nelze smazat, nejprve ji deaktivujte"}), 400

        cur = conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()
        return jsonify({"message": "Aktivita smazána"}), 200
    finally:
        conn.close()


@app.post("/finalize_day")
def finalize_day():
    limits = app.config["RATE_LIMITS"]["finalize_day"]
    limited = rate_limit("finalize_day", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    # Validate date format if provided explicitly
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("Date must be in YYYY-MM-DD format")

    conn = get_db_connection()
    try:
        # získej všechny aktivní aktivity
        active_activities = conn.execute(
            """
            SELECT name, description
            FROM activities
            WHERE active = 1
               OR (deactivated_at IS NOT NULL AND ? < deactivated_at)
            """,
            (date,),
        ).fetchall()
        existing = conn.execute("SELECT activity FROM entries WHERE date = ?", (date,)).fetchall()
        existing_names = {e["activity"] for e in existing}

        created = 0
        for a in active_activities:
            if a["name"] not in existing_names:
                conn.execute(
                    "INSERT INTO entries (date, activity, description, value, note) VALUES (?, ?, ?, 0, '')",
                    (date, a["name"], a["description"])
                )
                created += 1
        conn.commit()
        return jsonify({"message": f"{created} missing entries added for {date}"}), 200
    finally:
        conn.close()


@app.post("/import_csv")
def import_csv_endpoint():
    limits = app.config["RATE_LIMITS"]["import_csv"]
    limited = rate_limit("import_csv", limits["limit"], limits["window"])
    if limited:
        return limited

    if "file" not in request.files:
        return jsonify({"error": "Missing CSV file"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Missing CSV file"}), 400

    filename = secure_filename(file.filename)
    suffix = os.path.splitext(filename)[1] or ".csv"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        summary = run_import_csv(tmp_path, app.config["DB_PATH"])
    except Exception as exc:  # pragma: no cover - defensive
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": f"Failed to import CSV: {exc}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return jsonify({"message": "CSV import completed", "summary": summary}), 200



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
