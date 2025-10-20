from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

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
    category = data.get("category")
    value = data.get("value")
    note = data.get("note")

    if not date:
        return jsonify({"error": "Missing 'date' field"}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO entries (date, category, value, note) VALUES (?, ?, ?, ?)",
            (date, category, value, note),
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
