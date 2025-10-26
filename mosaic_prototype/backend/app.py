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
    validate_activity_payload,
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
    columns = {row[1] for row in cursor.fetchall()}
    if "category" not in columns:
        conn.execute("ALTER TABLE activities ADD COLUMN category TEXT NOT NULL DEFAULT ''")
        conn.commit()
    if "goal" not in columns:
        conn.execute("ALTER TABLE activities ADD COLUMN goal INTEGER NOT NULL DEFAULT 0")
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
    payload = validate_activity_payload(data)
    name = payload["name"]
    category = payload["category"]
    goal = payload["goal"]
    description = payload["description"]

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO activities (name, category, goal, description) VALUES (?, ?, ?, ?)",
            (name, category, goal, description)
        )
        conn.commit()
        return jsonify({"message": "Kategorie přidána"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Kategorie s tímto názvem již existuje"}), 409
    finally:
        conn.close()


@app.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_deactivate", limits["limit"], limits["window"])
    if limited:
        return limited

    conn = get_db_connection()
    try:
        cur = conn.execute("UPDATE activities SET active = 0 WHERE id = ?", (activity_id,))
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
        cur = conn.execute("UPDATE activities SET active = 1 WHERE id = ?", (activity_id,))
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
                e.id AS entry_id,
                e.value,
                e.note
            FROM activities a
            LEFT JOIN entries e
              ON e.activity = a.name AND e.date = ?
            WHERE a.active = 1
            ORDER BY a.name ASC
        """, (date,)).fetchall()
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
        active_activities = conn.execute("SELECT name, description FROM activities WHERE active = 1").fetchall()
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
