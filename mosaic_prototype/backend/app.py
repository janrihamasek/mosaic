from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "../database/mosaic.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def home():
    return jsonify({"message": "Backend běží!", "database": DB_PATH})


@app.get("/entries")
def get_entries():
    conn = get_db_connection()
    try:
        entries = conn.execute("SELECT * FROM entries ORDER BY date DESC").fetchall()
        return jsonify([dict(row) for row in entries])
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.post("/add_entry")
def add_entry():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    date = data.get("date")
    activity = data.get("activity")
    value = data.get("value")
    note = data.get("note")

    if not date or not activity:
        return jsonify({"error": "Missing 'date' or 'activity' field"}), 400
    
    # Ensure value is treated as a number; if missing, default to 0
    # The React component sends value as a string representation of a number or 0
    try:
        # Convert value to float for storage consistency, default to 0 if none is sent
        float_value = float(value) if value is not None else 0.0
    except ValueError:
        return jsonify({"error": "'value' must be a number"}), 400


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
            rows = conn.execute("SELECT * FROM activities ORDER BY name ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM activities WHERE active = 1 ORDER BY name ASC").fetchall()
        return jsonify([dict(r) for r in rows])
    except sqlite3.OperationalError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.post("/add_activity")
def add_activity():
    data = request.get_json()
    name = data.get("name")
    description = data.get("description", "")
    if not name:
        return jsonify({"error": "Missing 'name'"}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO activities (name, description) VALUES (?, ?)",
            (name, description)
        )
        conn.commit()
        return jsonify({"message": "Kategorie přidána"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Kategorie s tímto názvem již existuje"}), 409
    finally:
        conn.close()


@app.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id):
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
    data = request.get_json() or {}
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")

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



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)