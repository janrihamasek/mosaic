import copy
import os
import secrets
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import time
from typing import Dict, Iterator, Optional, Tuple, cast

import jwt
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from threading import Lock

from import_data import import_csv as run_import_csv
from models import Activity, Entry  # noqa: F401 - ensure models registered
from security import (
    ValidationError,
    error_response,
    rate_limit,
    require_api_key,
    validate_activity_create_payload,
    validate_activity_update_payload,
    validate_csv_import_payload,
    validate_entry_payload,
    validate_finalize_day_payload,
    validate_login_payload,
    validate_register_payload,
)
from extensions import db, migrate

app = Flask(__name__)
CORS(app)

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "../database/mosaic.db"
DB_PATH = os.environ.get("MOSAIC_DB_PATH") or DEFAULT_DB_PATH
app.config["DB_PATH"] = str(DB_PATH)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Path(app.config['DB_PATH']).resolve()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["_SCHEMA_READY"] = False
app.config.setdefault("_ENTRY_METADATA_READY", False)
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
        "login": {"limit": 10, "window": 60},
        "register": {"limit": 5, "window": 3600},
    },
)
app.config["API_KEY"] = os.environ.get("MOSAIC_API_KEY")
app.config.setdefault("PUBLIC_ENDPOINTS", {"home"})
app.config.setdefault("JWT_SECRET", os.environ.get("MOSAIC_JWT_SECRET") or "change-me")
app.config.setdefault("JWT_ALGORITHM", "HS256")
app.config.setdefault("JWT_EXP_MINUTES", int(os.environ.get("MOSAIC_JWT_EXP_MINUTES", "60")))
app.config["PUBLIC_ENDPOINTS"].update({"login", "register"})

db.init_app(app)
migrate.init_app(app, db)

ERROR_CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    429: "too_many_requests",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
}

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_cache_storage: Dict[str, Tuple[float, object]] = {}
_cache_lock = Lock()
TODAY_CACHE_TTL = 60
STATS_CACHE_TTL = 300


def _cache_build_key(prefix: str, key_parts: Tuple) -> str:
    return prefix + "::" + "::".join(str(part) for part in key_parts)


def cache_get(prefix: str, key_parts: Tuple) -> Optional[object]:
    key = _cache_build_key(prefix, key_parts)
    now = time()
    with _cache_lock:
        entry = _cache_storage.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            del _cache_storage[key]
            return None
        return copy.deepcopy(value)


def cache_set(prefix: str, key_parts: Tuple, value: object, ttl: int) -> None:
    key = _cache_build_key(prefix, key_parts)
    with _cache_lock:
        _cache_storage[key] = (time() + ttl, copy.deepcopy(value))


def invalidate_cache(prefix: str) -> None:
    key_prefix = prefix + "::"
    with _cache_lock:
        for key in list(_cache_storage.keys()):
            if key.startswith(key_prefix):
                del _cache_storage[key]


def _create_access_token(user_id: int, username: str) -> tuple[str, str]:
    csrf_token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    exp_minutes = app.config.get("JWT_EXP_MINUTES", 60)
    payload = {
        "sub": str(user_id),
        "username": username,
        "csrf": csrf_token,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=int(exp_minutes))).timestamp()),
    }
    token = jwt.encode(
        payload,
        app.config["JWT_SECRET"],
        algorithm=app.config.get("JWT_ALGORITHM", "HS256"),
    )
    return token, csrf_token


def _decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        app.config["JWT_SECRET"],
        algorithms=[app.config.get("JWT_ALGORITHM", "HS256")],
    )


def _is_public_endpoint(endpoint: Optional[str]) -> bool:
    if not endpoint:
        return False
    if endpoint.startswith("static"):
        return True
    public = app.config.get("PUBLIC_ENDPOINTS", set())
    return endpoint in public


def parse_pagination(default_limit: int = 100, max_limit: int = 500) -> Dict[str, int]:
    try:
        limit_raw = request.args.get("limit", default_limit)
        limit = int(limit_raw)
        if limit <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("limit must be a positive integer", code="invalid_query")

    try:
        offset_raw = request.args.get("offset", 0)
        offset = int(offset_raw)
        if offset < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("offset must be a non-negative integer", code="invalid_query")

    limit = min(limit, max_limit)
    return {"limit": limit, "offset": offset}


def configure_database_path(path: str):
    absolute = Path(path).resolve()
    app.config["DB_PATH"] = str(absolute)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{absolute}"
    app.config["_SCHEMA_READY"] = False


configure_database_path(app.config["DB_PATH"])


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

    cursor = conn.execute("PRAGMA table_info(entries)")
    entry_columns_info = cursor.fetchall()
    entry_columns = {row[1] for row in entry_columns_info}
    if "activity_category" not in entry_columns:
        conn.execute("ALTER TABLE entries ADD COLUMN activity_category TEXT NOT NULL DEFAULT ''")
        conn.commit()
    if "activity_goal" not in entry_columns:
        conn.execute("ALTER TABLE entries ADD COLUMN activity_goal REAL NOT NULL DEFAULT 0")
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

    # backfill newly added entry metadata when possible
    if not app.config.get("_ENTRY_METADATA_READY"):
        conn.execute(
            """
            UPDATE entries
            SET activity_category = (
                SELECT category FROM activities WHERE activities.name = entries.activity
            )
            WHERE (activity_category IS NULL OR activity_category = '')
              AND EXISTS (
                  SELECT 1 FROM activities WHERE activities.name = entries.activity
              )
            """
        )
        conn.execute(
            """
            UPDATE entries
            SET activity_goal = (
                SELECT goal FROM activities WHERE activities.name = entries.activity
            )
            WHERE (activity_goal IS NULL OR activity_goal = 0)
              AND EXISTS (
                  SELECT 1 FROM activities WHERE activities.name = entries.activity
              )
            """
        )
        conn.commit()
        app.config["_ENTRY_METADATA_READY"] = True

    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_activity ON entries(activity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_activity_category ON entries(activity_category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category)")

    app.config["_SCHEMA_READY"] = True


def get_db_connection():
    db_path = app.config.get("DB_PATH", str(DB_PATH))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    ensure_schema(conn)
    return conn


@contextmanager
def db_transaction() -> Iterator[sqlite3.Connection]:
    conn = get_db_connection()
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


@app.get("/")
def home():
    return jsonify({"message": "Backend běží!", "database": DB_PATH})


@app.post("/register")
def register():
    limits = app.config["RATE_LIMITS"]["register"]
    limited = rate_limit("register", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_register_payload(data)
    username = payload["username"]
    password_hash = generate_password_hash(payload["password"])
    del payload

    try:
        with db_transaction() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError:
        return error_response("conflict", "Username already exists", 409)

    return jsonify({"message": "User registered"}), 201


@app.post("/login")
def login():
    limits = app.config["RATE_LIMITS"]["login"]
    limited = rate_limit("login", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_login_payload(data)

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (payload["username"],),
        ).fetchone()
    finally:
        conn.close()

    if not row or not check_password_hash(row["password_hash"], payload["password"]):
        return error_response("invalid_credentials", "Invalid username or password", 401)

    access_token, csrf_token = _create_access_token(row["id"], payload["username"])
    return jsonify(
        {
            "access_token": access_token,
            "csrf_token": csrf_token,
            "token_type": "Bearer",
            "expires_in": int(app.config.get("JWT_EXP_MINUTES", 60)) * 60,
        }
    )


@app.before_request
def _enforce_api_key():
    auth_result = require_api_key()
    if auth_result:
        return auth_result


@app.before_request
def _enforce_jwt_authentication():
    if request.method == "OPTIONS":  # preflight requests are exempt
        return None

    endpoint = request.endpoint
    if _is_public_endpoint(endpoint):
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return error_response("unauthorized", "Missing or invalid access token", 401)

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return error_response("unauthorized", "Missing or invalid access token", 401)

    try:
        payload = _decode_access_token(token)
    except jwt.ExpiredSignatureError:
        return error_response("token_expired", "Access token expired", 401)
    except jwt.InvalidTokenError:
        return error_response("unauthorized", "Invalid access token", 401)

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return error_response("unauthorized", "Invalid access token", 401)

    csrf_claim = payload.get("csrf")
    if not csrf_claim:
        return error_response("invalid_csrf", "Missing CSRF token claim", 403)

    g.current_user = {"id": user_id, "username": payload.get("username")}
    g.csrf_token = csrf_claim

    if request.method not in SAFE_METHODS:
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header or csrf_header != csrf_claim:
            return error_response("invalid_csrf", "Missing or invalid CSRF token", 403)

    return None


@app.errorhandler(ValidationError)
def handle_validation(error: ValidationError):
    return error_response(error.code, error.message, error.status, error.details)


@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    status = exc.code or 500
    message = exc.description or exc.name or "HTTP error"
    code = ERROR_CODE_BY_STATUS.get(status)
    if code is None:
        code = "internal_error" if status >= 500 else "bad_request"
    return error_response(code, message, status)


@app.errorhandler(Exception)
def handle_unexpected_exception(exc: Exception):
    app.logger.exception("Unhandled exception", exc_info=exc)
    return error_response("internal_error", "An unexpected error occurred", 500)


@app.get("/entries")
def get_entries():
    start_date = (request.args.get("start_date") or "").strip() or None
    end_date = (request.args.get("end_date") or "").strip() or None
    activity_filter_raw = request.args.get("activity") or ""
    category_filter_raw = request.args.get("category") or ""

    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return error_response("invalid_query", "Invalid date filter", 400)

    def normalize_filter(value, all_markers):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.lower() in all_markers:
            return None
        return candidate

    activity_filter = normalize_filter(activity_filter_raw, {"all", "all activities", "all_activities"})
    category_filter = normalize_filter(category_filter_raw, {"all", "all categories", "all_categories"})

    conn = get_db_connection()
    try:
        clauses = []
        params: list = []
        if start_date:
            clauses.append("e.date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("e.date <= ?")
            params.append(end_date)
        if activity_filter:
            clauses.append("e.activity = ?")
            params.append(activity_filter)
        if category_filter:
            clauses.append("COALESCE(a.category, e.activity_category, '') = ?")
            params.append(category_filter)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        query = f"""
            SELECT e.*,
                   COALESCE(a.category, e.activity_category, '') AS category,
                   COALESCE(a.goal, e.activity_goal, 0) AS goal,
                   COALESCE(a.description, e.description, '') AS activity_description
            FROM entries e
            LEFT JOIN activities a ON a.name = e.activity
            {where_sql}
            ORDER BY e.date DESC, e.activity ASC
        """
        pagination = parse_pagination()
        query += " LIMIT ? OFFSET ?"
        params.extend([pagination["limit"], pagination["offset"]])
        entries = conn.execute(query, params).fetchall()
        return jsonify([dict(row) for row in entries])
    except sqlite3.OperationalError as e:
        return error_response("database_error", str(e), 500)
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

    try:
        with db_transaction() as conn:
            cur = conn.execute(
                "SELECT category, goal, description FROM activities WHERE name = ?",
                (activity,),
            )
            activity_row = cur.fetchone()
            description = activity_row["description"] if activity_row else ""
            activity_category = activity_row["category"] if activity_row else ""
            activity_goal = activity_row["goal"] if activity_row else 0

            existing_entry = conn.execute(
                "SELECT activity_category, activity_goal FROM entries WHERE date = ? AND activity = ?",
                (date, activity),
            ).fetchone()
            if not activity_row and existing_entry:
                activity_category = existing_entry["activity_category"] or activity_category
                activity_goal = existing_entry["activity_goal"] if existing_entry["activity_goal"] is not None else activity_goal

            update_cur = conn.execute(
                """
                UPDATE entries
                SET value = ?,
                    note = ?,
                    description = ?,
                    activity_category = ?,
                    activity_goal = ?
                WHERE date = ? AND activity = ?
                """,
                (float_value, note, description, activity_category, activity_goal, date, activity),
            )

            if update_cur.rowcount > 0:
                response = jsonify({"message": "Záznam aktualizován"}), 200
            else:
                conn.execute(
                    """
                    INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (date, activity, description, float_value, note, activity_category, activity_goal),
                )
                response = jsonify({"message": "Záznam uložen"}), 201
    except sqlite3.OperationalError as e:
        return error_response("database_error", str(e), 500)
    else:
        invalidate_cache("today")
        invalidate_cache("stats")
        return response


@app.delete("/entries/<int:entry_id>")
def delete_entry(entry_id):
    limits = app.config["RATE_LIMITS"]["delete_entry"]
    limited = rate_limit("delete_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    try:
        with db_transaction() as conn:
            cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        if cur.rowcount == 0:
            return error_response("not_found", "Záznam nenalezen", 404)
        invalidate_cache("today")
        invalidate_cache("stats")
        return jsonify({"message": "Záznam smazán"}), 200
    except sqlite3.OperationalError as e:
        return error_response("database_error", str(e), 500)


@app.get("/activities")
def get_activities():
    show_all = request.args.get("all", "false").lower() in ("1", "true", "yes")
    conn = get_db_connection()
    try:
        pagination = parse_pagination()
        params = [pagination["limit"], pagination["offset"]]
        if show_all:
            rows = conn.execute(
                "SELECT * FROM activities ORDER BY active DESC, category ASC, name ASC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activities WHERE active = 1 ORDER BY active DESC, category ASC, name ASC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
        return jsonify([dict(r) for r in rows])
    except sqlite3.OperationalError as e:
        return error_response("database_error", str(e), 500)
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

    try:
        with db_transaction() as conn:
            conn.execute(
                """
                INSERT INTO activities (name, category, goal, description, frequency_per_day, frequency_per_week, deactivated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (name, category, goal, description, frequency_per_day, frequency_per_week)
            )
        invalidate_cache("today")
        invalidate_cache("stats")
        return jsonify({"message": "Kategorie přidána"}), 201
    except sqlite3.IntegrityError:
        return error_response("conflict", "Kategorie s tímto názvem již existuje", 409)


@app.put("/activities/<int:activity_id>")
def update_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["update_activity"]
    limited = rate_limit("update_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_activity_update_payload(data)

    with db_transaction() as conn:
        cur = conn.execute("SELECT name FROM activities WHERE id = ?", (activity_id,))
        row = cur.fetchone()
        if not row:
            return error_response("not_found", "Aktivita nenalezena", 404)

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

        entry_update_clauses = []
        entry_params = []
        if "description" in payload:
            entry_update_clauses.append("description = ?")
            entry_params.append(payload["description"])
        if "category" in payload:
            entry_update_clauses.append("activity_category = ?")
            entry_params.append(payload["category"])
        if "goal" in payload:
            entry_update_clauses.append("activity_goal = ?")
            entry_params.append(payload["goal"])
        if entry_update_clauses:
            entry_params.append(row["name"])
            conn.execute(
                f"UPDATE entries SET {', '.join(entry_update_clauses)} WHERE activity = ?",
                entry_params,
            )

    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita aktualizována"}), 200


@app.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_deactivate", limits["limit"], limits["window"])
    if limited:
        return limited
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    with db_transaction() as conn:
        cur = conn.execute(
            "UPDATE activities SET active = 0, deactivated_at = ? WHERE id = ?",
            (deactivation_date, activity_id),
        )
        if cur.rowcount == 0:
            return error_response("not_found", "Aktivita nenalezena", 404)
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita deaktivována"}), 200


@app.patch("/activities/<int:activity_id>/activate")
def activate_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_activate", limits["limit"], limits["window"])
    if limited:
        return limited

    with db_transaction() as conn:
        cur = conn.execute("UPDATE activities SET active = 1, deactivated_at = NULL WHERE id = ?", (activity_id,))
        if cur.rowcount == 0:
            return error_response("not_found", "Aktivita nenalezena", 404)
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita aktivována"}), 200


@app.get("/stats/progress")
def get_progress_stats():
    date_raw = request.args.get("date")
    if date_raw:
        try:
            target_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError:
            return error_response("invalid_query", "Invalid date", 400)
    else:
        target_date = datetime.now().date()

    cache_key_parts = ("dashboard", target_date.isoformat())
    cached = cache_get("stats", cache_key_parts)
    if cached is not None:
        return jsonify(cached)

    today_str = target_date.strftime("%Y-%m-%d")
    window_30_start = (target_date - timedelta(days=29)).strftime("%Y-%m-%d")

    def compute_completion(total_value: Optional[float], total_goal: Optional[float]) -> float:
        value = float(total_value or 0.0)
        goal = float(total_goal or 0.0)
        if goal <= 0:
            return 0.0
        return min(value / goal, 1.0)

    conn = get_db_connection()
    try:
        daily_rows = conn.execute(
            """
            SELECT
                date,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY date
        """,
            (window_30_start, today_str),
        ).fetchall()

        daily_completion = {}
        for row in daily_rows:
            ratio = compute_completion(row["total_value"], row["total_goal"])
            daily_completion[row["date"]] = ratio

        goal_completion_today = round(daily_completion.get(today_str, 0.0) * 100, 1)

        streak_rows = conn.execute(
            """
            SELECT
                date,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal
            FROM entries
            WHERE date <= ?
            GROUP BY date
            ORDER BY date DESC
        """,
            (today_str,),
        ).fetchall()

        streak_map = {row["date"]: compute_completion(row["total_value"], row["total_goal"]) for row in streak_rows}
        streak_length = 0
        cursor = target_date
        while True:
            key = cursor.strftime("%Y-%m-%d")
            ratio = streak_map.get(key)
            if ratio is None or ratio < 1.0:
                break
            streak_length += 1
            cursor -= timedelta(days=1)

        distribution_rows = conn.execute(
            """
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY entry_count DESC, category COLLATE NOCASE ASC
        """,
            (window_30_start, today_str),
        ).fetchall()

        total_entries = sum(int(row["entry_count"] or 0) for row in distribution_rows)
        activity_distribution = []
        for row in distribution_rows:
            count = int(row["entry_count"] or 0)
            percent = round((count / total_entries) * 100, 1) if total_entries else 0.0
            activity_distribution.append(
                {
                    "category": row["category"] or "Other",
                    "count": count,
                    "percent": percent,
                }
            )

        def average_completion(days: int) -> float:
            total_ratio = 0.0
            for offset in range(days):
                key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
                total_ratio += daily_completion.get(key, 0.0)
            return round((total_ratio / days) * 100, 1) if days else 0.0

        avg_goal_fulfillment = {
            "last_7_days": average_completion(7),
            "last_30_days": average_completion(30),
        }

        active_days = len(daily_rows)
        active_days_ratio = {
            "active_days": active_days,
            "total_days": 30,
            "percent": round((active_days / 30) * 100, 1) if active_days else 0.0,
        }

        pos_neg_row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN COALESCE(value, 0) >= COALESCE(activity_goal, 0) THEN 1 ELSE 0 END) AS positive_count,
                SUM(CASE WHEN COALESCE(value, 0) < COALESCE(activity_goal, 0) THEN 1 ELSE 0 END) AS negative_count
            FROM entries
            WHERE date BETWEEN ? AND ?
        """,
            (window_30_start, today_str),
        ).fetchone()

        positive_count = int(pos_neg_row["positive_count"] or 0)
        negative_count = int(pos_neg_row["negative_count"] or 0)
        if negative_count > 0:
            ratio_value = round(positive_count / negative_count, 1)
        else:
            ratio_value = round(float(positive_count), 1) if positive_count else 0.0
        positive_vs_negative = {
            "positive": positive_count,
            "negative": negative_count,
            "ratio": ratio_value,
        }

        consistent_rows = conn.execute(
            """
            SELECT
                activity AS name,
                COUNT(DISTINCT date) AS active_days
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY activity
            ORDER BY active_days DESC, name COLLATE NOCASE ASC
            LIMIT 3
        """,
            (window_30_start, today_str),
        ).fetchall()

        top_consistent_activities = []
        for row in consistent_rows:
            days_present = int(row["active_days"] or 0)
            percent = round((days_present / 30) * 100, 1) if days_present else 0.0
            top_consistent_activities.append(
                {
                    "name": row["name"],
                    "consistency_percent": percent,
                }
            )

        payload = {
            "goal_completion_today": goal_completion_today,
            "streak_length": streak_length,
            "activity_distribution": activity_distribution,
            "avg_goal_fulfillment": avg_goal_fulfillment,
            "active_days_ratio": active_days_ratio,
            "positive_vs_negative": positive_vs_negative,
            "top_consistent_activities": top_consistent_activities,
        }
        cache_set("stats", cache_key_parts, payload, STATS_CACHE_TTL)
        return jsonify(payload)
    finally:
        conn.close()


@app.get("/today")
def get_today():
    date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    pagination = parse_pagination(default_limit=200)
    cache_key_parts = (date, pagination["limit"], pagination["offset"])
    cached = cache_get("today", cache_key_parts)
    if cached is not None:
        return jsonify(cached)
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
                a.goal,
                e.id AS entry_id,
                e.value,
                e.note,
                e.activity_goal
            FROM activities a
            LEFT JOIN entries e
              ON e.activity = a.name AND e.date = ?
            WHERE a.active = 1
               OR (a.deactivated_at IS NOT NULL AND ? < a.deactivated_at)
            ORDER BY a.name ASC
            LIMIT ? OFFSET ?
        """, (date, date, pagination["limit"], pagination["offset"]))
        rows = rows.fetchall()
        data = [dict(r) for r in rows]
    finally:
        conn.close()
    cache_set("today", cache_key_parts, data, TODAY_CACHE_TTL)
    return jsonify(data)


@app.delete("/activities/<int:activity_id>")
def delete_activity(activity_id):
    limits = app.config["RATE_LIMITS"]["delete_activity"]
    limited = rate_limit("delete_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    with db_transaction() as conn:
        row = conn.execute("SELECT active FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not row:
            return error_response("not_found", "Aktivita nenalezena", 404)
        if row["active"] == 1:
            return error_response("invalid_state", "Aktivitu nelze smazat, nejprve ji deaktivujte", 400)

        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita smazána"}), 200


@app.post("/finalize_day")
def finalize_day():
    limits = app.config["RATE_LIMITS"]["finalize_day"]
    limited = rate_limit("finalize_day", limits["limit"], limits["window"])
    if limited:
        return limited

    payload = validate_finalize_day_payload(request.get_json() or {})
    date = payload["date"]

    with db_transaction() as conn:
        # získej všechny aktivní aktivity
        active_activities = conn.execute(
            """
            SELECT name, description, category, goal
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
                    """
                    INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal)
                    VALUES (?, ?, ?, 0, '', ?, ?)
                    """,
                    (date, a["name"], a["description"], a["category"], a["goal"])
                )
                created += 1
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": f"{created} missing entries added for {date}"}), 200


@app.post("/import_csv")
def import_csv_endpoint():
    limits = app.config["RATE_LIMITS"]["import_csv"]
    limited = rate_limit("import_csv", limits["limit"], limits["window"])
    if limited:
        return limited

    file = cast(FileStorage, validate_csv_import_payload(request.files))
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
        return error_response("import_failed", f"Failed to import CSV: {exc}", 500)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "CSV import completed", "summary": summary}), 200



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
