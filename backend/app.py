import json
import os
import secrets
import tempfile
import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import wraps
from time import time
from typing import Any, Dict, Iterator, List, Optional, Tuple, cast

import click
import structlog
import jwt  # type: ignore[import]
from flask import Flask, Response, jsonify, request, g
from flask_cors import CORS
from flask.cli import with_appcontext
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from backup_manager import BackupManager
from import_data import import_csv as run_import_csv
from https_utils import resolve_ssl_context
from models import Activity, Entry  # noqa: F401 - ensure models registered
from services import auth_service, admin_service, activities_service, nightmotion_service
from controllers.helpers import current_user_id as _current_user_id, is_admin_user as _is_admin_user, parse_pagination
from infra.cache_manager import (
    cache_get,
    cache_set,
    invalidate_cache,
    CacheScope,
    TODAY_CACHE_TTL,
    STATS_CACHE_TTL,
    cache_health,
)
from infra import metrics_manager

# Expose streaming helper for legacy callers/tests
stream_rtsp = nightmotion_service.stream_rtsp
from security import (
    ValidationError,
    error_response,
    rate_limit,
    require_api_key,
    limit_request,
    validate_csv_import_payload,
    require_admin,
    jwt_required,
)
from extensions import db, migrate
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from db_utils import connection as sa_connection, transactional_connection


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        context_class=dict,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("flask.app").setLevel(logging.WARNING)


configure_logging()

from audit import install_runtime_log_handler, log_event  # noqa: E402
from routes.logs import logs_bp  # noqa: E402
from wearable_read import wearable_read_bp  # noqa: E402

install_runtime_log_handler()

logger = structlog.get_logger("mosaic.backend")

metrics_manager.ensure_metrics_logger_started()
get_metrics_json = metrics_manager.get_metrics_json
get_metrics_text = metrics_manager.get_metrics_text
reset_metrics_state = metrics_manager.reset_metrics_state


class MosaicFlask(Flask):
    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        debug: Optional[bool] = None,
        load_dotenv: bool = True,
        **options,
    ) -> None:
        if host is None:
            host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
        if port is None:
            port = int(os.environ.get("FLASK_RUN_PORT", os.environ.get("PORT", "5000")))
        ssl_context = options.get("ssl_context")
        if ssl_context is None:
            ssl_context = resolve_ssl_context()
            if ssl_context:
                options["ssl_context"] = ssl_context
        super().run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = MosaicFlask(__name__)


def _resolve_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "")
    if raw.strip():
        parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if parsed:
            return parsed
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


CORS(
    app,
    origins=_resolve_cors_origins(),
    supports_credentials=True,
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-CSRF-Token",
        "X-API-Key",
        "X-Idempotency-Key",
        "X-Overwrite-Existing",
    ],
    expose_headers=["Content-Disposition"],
)


def _resolve_database_uri() -> str:
    direct_uri = os.environ.get("DATABASE_URL")
    if direct_uri:
        return direct_uri

    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")

    if user and password and database:
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    default_uri = "postgresql+psycopg2://postgres:postgres@localhost:5432/mosaic"
    return default_uri


app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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
        "wearable_ingest": {"limit": 60, "window": 60},
        "login": {"limit": 10, "window": 60},
        "register": {"limit": 5, "window": 3600},
    },
)
app.config["API_KEY"] = os.environ.get("MOSAIC_API_KEY")
app.config.setdefault("PUBLIC_ENDPOINTS", {"home"})
app.config.setdefault("JWT_SECRET", os.environ.get("MOSAIC_JWT_SECRET") or "change-me")
app.config.setdefault("JWT_ALGORITHM", "HS256")
app.config.setdefault("JWT_EXP_MINUTES", int(os.environ.get("MOSAIC_JWT_EXP_MINUTES", "60")))
app.config["PUBLIC_ENDPOINTS"].update({"login", "register", "metrics", "health", "healthz"})

db.init_app(app)
migrate.init_app(app, db)
app.register_blueprint(logs_bp)
app.register_blueprint(wearable_read_bp)

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

def _create_access_token(
    user_id: int,
    username: str,
    *,
    is_admin: bool = False,
    display_name: Optional[str] = None,
) -> tuple[str, str]:
    csrf_token = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    exp_minutes = app.config.get("JWT_EXP_MINUTES", 60)
    payload = {
        "sub": str(user_id),
        "username": username,
        "csrf": csrf_token,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=int(exp_minutes))).timestamp()),
        "is_admin": bool(is_admin),
        "display_name": (display_name or "").strip(),
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
    if endpoint in public:
        return True
    endpoint_name = endpoint.split(".", 1)[-1]
    return endpoint_name in public


def _row_value(row, key, default=None):
    if hasattr(row, "_mapping"):
        return row._mapping.get(key, default)
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _serialize_user_row(row) -> dict:
    username = _row_value(row, "username", "")
    display_name = _row_value(row, "display_name", "") or username
    created_at_value = _row_value(row, "created_at")
    if isinstance(created_at_value, datetime):
        created_at_str = created_at_value.replace(
            tzinfo=created_at_value.tzinfo or timezone.utc
        ).isoformat()
    elif created_at_value:
        created_at_str = str(created_at_value)
    else:
        created_at_str = None

    return {
        "id": _row_value(row, "id"),
        "username": username,
        "display_name": display_name,
        "is_admin": bool(_row_value(row, "is_admin", False)),
        "created_at": created_at_str,
    }


def _build_export_filename(extension: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"mosaic-export-{timestamp}.{extension}"


def get_current_user_profile():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    user_id = current_user["id"]
    payload = auth_service.get_user_profile(user_id)
    return jsonify(payload)


def update_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)

    data = request.get_json(silent=True) or {}
    result, status = auth_service.update_user_profile(current_user["id"], data)
    return jsonify(result), status


def delete_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    user_id = current_user["id"]

    result, status = auth_service.delete_user(user_id, invalidate_cache_cb=invalidate_cache)

    return jsonify(result), status


def list_users():
    users = admin_service.list_users()
    return jsonify(users)


def admin_delete_user(user_id: int):
    current_user = getattr(g, "current_user", None)
    result, status = admin_service.delete_user(
        user_id,
        requester_id=current_user.get("id") if current_user else None,
        invalidate_cache_cb=invalidate_cache,
    )
    return jsonify(result), status


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

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        return error_response("unauthorized", "Invalid access token", 401)
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return error_response("unauthorized", "Invalid access token", 401)

    csrf_claim = payload.get("csrf")
    if not csrf_claim:
        return error_response("invalid_csrf", "Missing CSRF token claim", 403)

    g.current_user = {
        "id": user_id,
        "username": payload.get("username"),
        "is_admin": bool(payload.get("is_admin", False)),
        "display_name": payload.get("display_name") or "",
    }
    g.csrf_token = csrf_claim

    if request.method not in SAFE_METHODS:
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header or csrf_header != csrf_claim:
            return error_response("invalid_csrf", "Missing or invalid CSRF token", 403)

    return None


@app.before_request
def _start_request_timer():
    g.metrics_start_time = metrics_manager.now_perf_counter()
    g.metrics_endpoint = request.endpoint or (request.url_rule.rule if getattr(request, "url_rule", None) else request.path)
    g.metrics_method = (request.method or "GET").upper()


@app.after_request
def _log_request(response: Response):
    try:
        start = getattr(g, "metrics_start_time", None)
        if start is not None:
            duration_ms = (metrics_manager.now_perf_counter() - start) * 1000
        else:
            duration_ms = 0.0
        metrics_manager.record_request_metrics(g.metrics_method, g.metrics_endpoint, response.status_code, duration_ms)
        logger.bind(
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            user_id=getattr(g, "current_user", {}).get("id"),
        ).info("request.completed")
    except Exception:
        pass
    return response


@app.teardown_request
def _record_metrics_on_teardown(exc: Optional[BaseException]):
    if exc is None:
        return
    try:
        start = getattr(g, "metrics_start_time", None)
        duration_ms = (metrics_manager.now_perf_counter() - start) * 1000 if start else 0.0
        metrics_manager.record_request_metrics(g.metrics_method, g.metrics_endpoint, 500, duration_ms, is_error=True)
    except Exception:
        pass


@app.errorhandler(ValidationError)
def handle_validation(error: ValidationError):
    logger.bind(status_code=error.status, error_code=error.code).warning(
        "request.validation_error",
        details=error.details,
        message=error.message,
    )
    return error_response(error.code, error.message, error.status, error.details)


@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    status = exc.code or 500
    message = exc.description or exc.name or "HTTP error"
    code = ERROR_CODE_BY_STATUS.get(status)
    if code is None:
        code = "internal_error" if status >= 500 else "bad_request"
    log_method = logger.error if status >= 500 else logger.warning
    log_method(
        "request.http_exception",
        status_code=status,
        error_code=code,
        description=message,
    )
    return error_response(code, message, status)


def stream_proxy():
    limited = limit_request("stream_proxy", per_minute=2)
    if limited:
        return limited

    rtsp_url = request.args.get("url", type=str)
    if not rtsp_url:
        return jsonify({"error": "Missing RTSP URL"}), 400

    cam_user = request.args.get("username", "", type=str) or ""
    cam_pass = request.args.get("password", "", type=str) or ""
    if cam_user and cam_pass and "@" not in rtsp_url:
        rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{cam_user}:{cam_pass}@", 1)

    logger.bind(stream="nightmotion", rtsp_url=rtsp_url).info("nightmotion.proxy_start")

    try:
        response = Response(
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        response.headers["Cache-Control"] = "no-store"
        return response
    except ValidationError as exc:
        return error_response(exc.code, exc.message, exc.status, exc.details)
    except PermissionError:
        return error_response("unauthorized", "Unauthorized", 401)
    except RuntimeError as exc:
        logger.bind(stream="nightmotion").exception("nightmotion.stream_error", error=str(exc))
        return error_response("internal_error", "Stream nelze navázat", 500)
    except Exception as exc:
        logger.bind(stream="nightmotion").exception("nightmotion.stream_error_unexpected", error=str(exc))
        return error_response("internal_error", "Stream nelze navázat", 500)


@app.errorhandler(Exception)
def handle_unexpected_exception(exc: Exception):
    logger.bind(status_code=500).exception("request.unhandled_exception", error=str(exc))
    return error_response("internal_error", "An unexpected error occurred", 500)


def import_csv_endpoint():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)
    limits = app.config["RATE_LIMITS"]["import_csv"]
    limited = rate_limit("import_csv", limits["limit"], limits["window"])
    if limited:
        return limited

    file = cast(FileStorage, validate_csv_import_payload(request.files))
    filename_input = file.filename or "import.csv"
    filename = secure_filename(filename_input)
    suffix = os.path.splitext(filename)[1] or ".csv"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        summary = run_import_csv(tmp_path, user_id=user_id)
    except Exception as exc:  # pragma: no cover - defensive
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        log_event(
            "import.csv_failed",
            "CSV import failed",
            user_id=user_id,
            level="error",
            context={"error": str(exc), "filename": filename},
        )
        return error_response("import_failed", f"Failed to import CSV: {exc}", 500)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    invalidate_cache("today")
    invalidate_cache("stats")
    log_event(
        "import.csv",
        "CSV import completed",
        user_id=user_id,
        context={"summary": summary, "filename": filename},
    )
    return jsonify({"message": "CSV import completed", "summary": summary}), 200



from controllers import register_controllers

register_controllers(app)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug)
def _check_db_connection() -> bool:
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("health.db_check_failed", error=str(exc))
        return False


def _check_cache_state() -> bool:
    try:
        return cache_health()
    except Exception as exc:
        logger.warning("health.cache_check_failed", error=str(exc))
        return False


def _current_uptime_seconds() -> float:
    return max(0.0, time() - metrics_manager._SERVER_START_TIME)


def _build_health_summary() -> Tuple[Dict[str, object], bool]:
    metrics_snapshot = metrics_manager.get_metrics_json()
    uptime_s = round(_current_uptime_seconds(), 2)
    requests_total = metrics_snapshot["requests_total"]
    uptime_minutes = uptime_s / 60 if uptime_s else 0.0
    if uptime_minutes <= 0:
        req_per_min = float(requests_total)
    else:
        req_per_min = requests_total / uptime_minutes
    error_total = metrics_snapshot["errors_total"]["4xx"] + metrics_snapshot["errors_total"]["5xx"]
    error_rate = error_total / requests_total if requests_total else 0.0
    db_ok = _check_db_connection()
    cache_ok = _check_cache_state()
    summary = {
        "uptime_s": uptime_s,
        "db_ok": db_ok,
        "cache_ok": cache_ok,
        "req_per_min": round(req_per_min, 2),
        "error_rate": round(error_rate, 4),
        "last_metrics_update": metrics_snapshot.get("last_updated"),
    }
    healthy = db_ok and cache_ok
    return summary, healthy
