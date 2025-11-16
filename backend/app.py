import copy
import csv
import io
import json
import os
import secrets
import subprocess
import tempfile
import logging
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from functools import wraps
from threading import Lock, Thread
from time import perf_counter, sleep, time
from typing import Any, DefaultDict, Dict, Iterator, List, NamedTuple, Optional, Tuple, TypedDict, cast
from urllib.parse import urlparse, urlunparse

import click
import structlog
import jwt  # type: ignore[import]
from flask import Flask, Response, jsonify, request, g, stream_with_context, send_file
from flask_cors import CORS
from flask.cli import with_appcontext
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from backup_manager import BackupManager
from import_data import import_csv as run_import_csv
from https_utils import resolve_ssl_context
from ingest import process_wearable_raw_by_dedupe_keys
from models import Activity, Entry  # noqa: F401 - ensure models registered
from security import (
    ValidationError,
    error_response,
    rate_limit,
    require_api_key,
    validate_activity_create_payload,
    limit_request,
    validate_activity_update_payload,
    validate_csv_import_payload,
    validate_entry_payload,
    validate_finalize_day_payload,
    validate_login_payload,
    validate_register_payload,
    validate_user_update_payload,
    validate_wearable_batch_payload,
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

class CacheScope(NamedTuple):
    user_id: Optional[int]
    is_admin: bool


CacheEntry = Tuple[float, object, Optional[CacheScope]]


_cache_storage: Dict[str, CacheEntry] = {}
_cache_lock = Lock()
TODAY_CACHE_TTL = 60
STATS_CACHE_TTL = 300

_IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("IDEMPOTENCY_TTL_SECONDS", "600"))
_idempotency_lock = Lock()
_idempotency_store: Dict[str, Tuple[float, dict, int]] = {}


def _cache_scope_key_parts(scope: Optional[CacheScope]) -> Tuple[str, ...]:
    if scope is None:
        return tuple()
    user_component = (
        f"user:{scope.user_id}"
        if scope.user_id is not None
        else "user:anonymous"
    )
    role_component = "role:admin" if scope.is_admin else "role:user"
    return (user_component, role_component)


def _namespaced_cache_key_parts(key_parts: Tuple, scope: Optional[CacheScope]) -> Tuple:
    return _cache_scope_key_parts(scope) + key_parts

_SERVER_START_TIME = time()
_METRICS_LOG_INTERVAL_SECONDS = int(os.environ.get("METRICS_LOG_INTERVAL_SECONDS", "60"))
_metrics_lock = Lock()


class EndpointSnapshot(TypedDict):
    method: str
    endpoint: str
    count: int
    avg_latency_ms: float
    total_latency_ms: float
    errors_4xx: int
    errors_5xx: int
    status_counts: Dict[str, int]


class MetricsSnapshot(TypedDict):
    requests_total: int
    total_latency_ms: float
    avg_latency_ms: float
    errors_total: Dict[str, int]
    status_counts: Dict[str, int]
    endpoints: List[EndpointSnapshot]
    last_updated: Optional[str]


class EndpointBucket(TypedDict):
    count: int
    total_latency_ms: float
    errors_4xx: int
    errors_5xx: int
    status_counts: Dict[int, int]


class MetricsState(TypedDict):
    requests_total: int
    latency_total_ms: float
    errors_4xx: int
    errors_5xx: int
    status_counts: Dict[int, int]
    per_endpoint: DefaultDict[Tuple[str, str], EndpointBucket]
    last_updated: Optional[float]


def _endpoint_bucket_factory() -> EndpointBucket:
    return EndpointBucket(
        count=0,
        total_latency_ms=0.0,
        errors_4xx=0,
        errors_5xx=0,
        status_counts=defaultdict(int),
    )


def _initialize_metrics_state() -> MetricsState:
    return MetricsState(
        requests_total=0,
        latency_total_ms=0.0,
        errors_4xx=0,
        errors_5xx=0,
        status_counts=defaultdict(int),
        per_endpoint=defaultdict(_endpoint_bucket_factory),
        last_updated=None,
    )


_metrics_state: MetricsState = _initialize_metrics_state()
_metrics_logger_thread: Optional[Thread] = None


def _resolve_metrics_dimensions() -> Tuple[str, str]:
    method = (getattr(g, "metrics_method", None) or getattr(request, "method", "GET") or "GET").upper()
    endpoint = getattr(g, "metrics_endpoint", None)
    if not endpoint:
        endpoint = request.endpoint
    if not endpoint:
        rule = getattr(request, "url_rule", None)
        endpoint = getattr(rule, "rule", None) if rule else None
    if not endpoint:
        endpoint = request.path or "<unmatched>"
    return method, endpoint


def _record_request_metrics(status_code: int, duration_ms: float, *, is_error: bool = False) -> None:
    method, endpoint = _resolve_metrics_dimensions()
    is_client_error = 400 <= status_code < 500
    is_server_error = status_code >= 500
    now = time()

    with _metrics_lock:
        bucket = _metrics_state["per_endpoint"][(method, endpoint)]
        bucket["count"] += 1
        bucket["total_latency_ms"] += duration_ms
        bucket["status_counts"][status_code] += 1

        _metrics_state["requests_total"] += 1
        _metrics_state["latency_total_ms"] += duration_ms
        _metrics_state["status_counts"][status_code] += 1

        error_recorded = False
        if is_client_error:
            bucket["errors_4xx"] += 1
            _metrics_state["errors_4xx"] += 1
            error_recorded = True
        if is_server_error:
            bucket["errors_5xx"] += 1
            _metrics_state["errors_5xx"] += 1
            error_recorded = True
        if is_error and not error_recorded:
            bucket["errors_5xx"] += 1
            _metrics_state["errors_5xx"] += 1
        _metrics_state["last_updated"] = now


def _now_perf_counter() -> float:
    """Indirection so tests can monkeypatch app.perf_counter reliably."""
    return getattr(sys.modules[__name__], "perf_counter")()


def reset_metrics_state() -> None:
    """
    Reset the in-memory metrics store. Intended for use in tests.
    """

    global _metrics_state
    with _metrics_lock:
        _metrics_state = _initialize_metrics_state()


def get_metrics_json() -> MetricsSnapshot:
    with _metrics_lock:
        requests_total = _metrics_state["requests_total"]
        total_latency_ms = _metrics_state["latency_total_ms"]
        avg_latency_ms = total_latency_ms / requests_total if requests_total else 0.0
        last_updated = _metrics_state.get("last_updated")
        endpoints: List[EndpointSnapshot] = []
        for (method, endpoint), bucket in _metrics_state["per_endpoint"].items():
            count = bucket["count"]
            avg_endpoint_latency = bucket["total_latency_ms"] / count if count else 0.0
            endpoints.append(
                EndpointSnapshot(
                    method=method,
                    endpoint=endpoint,
                    count=count,
                    avg_latency_ms=round(avg_endpoint_latency, 2),
                    total_latency_ms=round(bucket["total_latency_ms"], 2),
                    errors_4xx=bucket["errors_4xx"],
                    errors_5xx=bucket["errors_5xx"],
                    status_counts={
                        str(code): value for code, value in bucket["status_counts"].items()
                    },
                )
            )
        endpoints.sort(key=lambda item: (item["endpoint"], item["method"]))

        return MetricsSnapshot(
            requests_total=requests_total,
            total_latency_ms=round(total_latency_ms, 2),
            avg_latency_ms=round(avg_latency_ms, 2),
            errors_total={
                "4xx": _metrics_state["errors_4xx"],
                "5xx": _metrics_state["errors_5xx"],
            },
            status_counts={
                str(code): value for code, value in _metrics_state["status_counts"].items()
            },
            endpoints=endpoints,
            last_updated=_format_timestamp(last_updated),
        )


def get_metrics_text() -> str:
    snapshot = get_metrics_json()
    lines = [
        "# HELP mosaic_requests_total Total HTTP requests processed by the Mosaic backend",
        "# TYPE mosaic_requests_total counter",
    ]
    for entry in snapshot["endpoints"]:
        lines.append(
            f'mosaic_requests_total{{method="{entry["method"]}",endpoint="{entry["endpoint"]}"}} '
            f'{entry["count"]}'
        )
    lines.append(f'mosaic_requests_global_total {snapshot["requests_total"]}')

    lines.extend(
        [
            "# HELP mosaic_request_latency_ms_total Cumulative request latency in milliseconds",
            "# TYPE mosaic_request_latency_ms_total counter",
        ]
    )
    for entry in snapshot["endpoints"]:
        lines.append(
            f'mosaic_request_latency_ms_total{{method="{entry["method"]}",endpoint="{entry["endpoint"]}"}} '
            f'{entry["total_latency_ms"]}'
        )
    lines.append(
        f'mosaic_request_latency_ms_average {snapshot["avg_latency_ms"]}'
    )

    lines.extend(
        [
            "# HELP mosaic_requests_errors_total Request error counts grouped by class",
            "# TYPE mosaic_requests_errors_total counter",
        ]
    )
    for error_type, value in snapshot["errors_total"].items():
        lines.append(f'mosaic_requests_errors_total{{type="{error_type}"}} {value}')

    status_counts = snapshot["status_counts"]
    if status_counts:
        lines.extend(
            [
                "# HELP mosaic_status_code_total Total responses grouped by HTTP status code",
                "# TYPE mosaic_status_code_total counter",
            ]
        )
        for status_code, value in status_counts.items():
            lines.append(f'mosaic_status_code_total{{status="{status_code}"}} {value}')

    return "\n".join(lines) + "\n"


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
        with _cache_lock:
            _ = len(_cache_storage)
        return True
    except Exception as exc:
        logger.warning("health.cache_check_failed", error=str(exc))
        return False


def _build_health_summary() -> Tuple[Dict[str, object], bool]:
    metrics_snapshot = get_metrics_json()
    uptime_s = round(_current_uptime_seconds(), 2)
    requests_total = metrics_snapshot["requests_total"]
    uptime_minutes = uptime_s / 60 if uptime_s else 0.0
    if uptime_minutes <= 0:
        req_per_min = float(requests_total)
    else:
        req_per_min = requests_total / uptime_minutes
    error_total = (
        metrics_snapshot["errors_total"]["4xx"] + metrics_snapshot["errors_total"]["5xx"]
    )
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


def _metrics_logger_loop() -> None:
    while True:
        sleep(_METRICS_LOG_INTERVAL_SECONDS)
        snapshot = get_metrics_json()
        logger.info("metrics.snapshot", metrics=snapshot)


def _ensure_metrics_logger_started() -> None:
    global _metrics_logger_thread
    if _metrics_logger_thread and _metrics_logger_thread.is_alive():
        return
    thread = Thread(target=_metrics_logger_loop, daemon=True, name="metrics-logger")
    thread.start()
    _metrics_logger_thread = thread


_ensure_metrics_logger_started()


def _current_uptime_seconds() -> float:
    return max(0.0, time() - _SERVER_START_TIME)


def _format_timestamp(timestamp: Optional[float]) -> Optional[str]:
    if timestamp is None:
        return None
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.isoformat()


def _get_current_user() -> Optional[dict]:
    current = getattr(g, "current_user", None)
    return current if isinstance(current, dict) else None


def _current_user_id() -> Optional[int]:
    user = _get_current_user()
    if not user:
        return None
    return cast(Optional[int], user.get("id"))


def _is_admin_user() -> bool:
    user = _get_current_user()
    if not user:
        return False
    return bool(user.get("is_admin"))


def _user_scope_clause(column: str, *, include_unassigned: bool = False) -> str:
    if include_unassigned:
        return f"({column} = ? OR {column} IS NULL)"
    return f"{column} = ?"


def _cache_build_key(prefix: str, key_parts: Tuple) -> str:
    return prefix + "::" + "::".join(str(part) for part in key_parts)


def build_cache_key(prefix: str, key_parts: Tuple, *, scope: Optional[CacheScope] = None) -> str:
    return _cache_build_key(prefix, _namespaced_cache_key_parts(key_parts, scope))


@app.before_request
def _start_request_timer() -> None:
    g.request_start_time = _now_perf_counter()
    g.request_id = secrets.token_hex(8)
    route = request.endpoint or request.path
    g.metrics_method = (request.method or "GET").upper()
    g.metrics_endpoint = route or "<unmatched>"
    structlog.contextvars.bind_contextvars(
        request_id=g.request_id,
        route=route,
        path=request.path,
        method=request.method,
    )


@app.after_request
def _log_request(response: Response) -> Response:
    start = getattr(g, "request_start_time", None)
    duration_ms = (_now_perf_counter() - start) * 1000 if start is not None else 0.0
    current_user = getattr(g, "current_user", None)
    user_id = current_user.get("id") if isinstance(current_user, dict) else None
    if user_id is not None:
        structlog.contextvars.bind_contextvars(user_id=user_id)

    status_code = response.status_code
    g.metrics_endpoint = request.endpoint or getattr(g, "metrics_endpoint", request.path)
    g.metrics_method = (request.method or "GET").upper()
    logger.bind(
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
    ).info("request.completed")
    _record_request_metrics(status_code, duration_ms)
    g.metrics_recorded = True
    return response


@app.teardown_request
def _clear_request_context(exc: Optional[BaseException]) -> None:
    if exc is not None and not getattr(g, "metrics_recorded", False):
        start = getattr(g, "request_start_time", None)
        duration_ms = (_now_perf_counter() - start) * 1000 if start is not None else 0.0
        status_code = getattr(exc, "code", 500) if hasattr(exc, "code") else 500
        _record_request_metrics(status_code, duration_ms, is_error=True)
        g.metrics_recorded = True
    structlog.contextvars.clear_contextvars()


def cache_get(prefix: str, key_parts: Tuple, *, scope: Optional[CacheScope] = None) -> Optional[object]:
    key = build_cache_key(prefix, key_parts, scope=scope)
    now = time()
    with _cache_lock:
        entry = _cache_storage.get(key)
        if not entry:
            return None
        expires_at, value, entry_scope = entry
        if expires_at <= now:
            del _cache_storage[key]
            return None
        if scope and entry_scope and scope != entry_scope:
            logger.warning(
                "cache.cross_user_hit",
                prefix=prefix,
                key=key,
                cached_user_id=entry_scope.user_id,
                requested_user_id=scope.user_id,
                cached_is_admin=entry_scope.is_admin,
                requested_is_admin=scope.is_admin,
            )
        return copy.deepcopy(value)


def cache_set(
    prefix: str,
    key_parts: Tuple,
    value: object,
    ttl: int,
    *,
    scope: Optional[CacheScope] = None,
) -> None:
    key = build_cache_key(prefix, key_parts, scope=scope)
    with _cache_lock:
        _cache_storage[key] = (time() + ttl, copy.deepcopy(value), scope)


def invalidate_cache(prefix: str) -> None:
    key_prefix = prefix + "::"
    with _cache_lock:
        for key in list(_cache_storage.keys()):
            if key.startswith(key_prefix):
                del _cache_storage[key]


def _coerce_utc(dt_value: datetime, tzinfo: ZoneInfo) -> datetime:
    if dt_value.tzinfo is None:
        aware = dt_value.replace(tzinfo=tzinfo)
    else:
        aware = dt_value
    return aware.astimezone(timezone.utc)


def _compose_idempotency_token(user_id: Optional[int], key: Optional[str]) -> Optional[str]:
    if user_id is None or not key:
        return None
    return f"{user_id}::{key.strip()}"


def _idempotency_lookup(user_id: Optional[int], key: Optional[str]) -> Optional[Tuple[dict, int]]:
    token = _compose_idempotency_token(user_id, key)
    if not token:
        return None
    now = time()
    with _idempotency_lock:
        entry = _idempotency_store.get(token)
        if not entry:
            return None
        expires_at, payload, status_code = entry
        if expires_at <= now:
            del _idempotency_store[token]
            return None
        return payload, status_code


def _idempotency_store_response(user_id: Optional[int], key: Optional[str], payload: dict, status_code: int) -> None:
    token = _compose_idempotency_token(user_id, key)
    if not token:
        return
    expires_at = time() + _IDEMPOTENCY_TTL_SECONDS
    with _idempotency_lock:
        _idempotency_store[token] = (expires_at, payload, status_code)


def _header_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "force", "overwrite")


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
    return endpoint in public


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


def _build_export_filename(extension: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"mosaic-export-{timestamp}.{extension}"


def _set_export_headers(
    response: Response,
    extension: str,
    *,
    limit: int,
    offset: int,
    total_entries: int,
    total_activities: int,
) -> Response:
    response.headers["Content-Disposition"] = f'attachment; filename="{_build_export_filename(extension)}"'
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    response.headers["X-Total-Entries"] = str(total_entries)
    response.headers["X-Total-Activities"] = str(total_activities)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


def _fetch_export_data(limit: int, offset: int) -> tuple[list[dict], list[dict], int, int]:
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        raise ValidationError("Missing user context", code="unauthorized", status=401)

    conn = get_db_connection()
    try:
        entry_params: list = []
        entry_where = ""
        if user_id is not None:
            entry_where = f"WHERE {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            entry_params.append(user_id)

        entries_cursor = conn.execute(
            f"""
            SELECT
                e.id AS entry_id,
                e.date,
                e.activity,
                e.description AS entry_description,
                e.value,
                e.note,
                e.activity_category,
                e.activity_goal
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {entry_where}
            ORDER BY e.date ASC, e.id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(entry_params + [limit, offset]),
        )

        activity_params: list = []
        activity_where = ""
        if user_id is not None:
            activity_where = f"WHERE {_user_scope_clause('a.user_id', include_unassigned=is_admin)}"
            activity_params.append(user_id)

        activities_cursor = conn.execute(
            f"""
            SELECT
                a.id AS activity_id,
                a.name,
                a.category,
                a.activity_type,
                a.goal,
                a.description AS activity_description,
                a.active,
                a.frequency_per_day,
                a.frequency_per_week,
                a.deactivated_at
            FROM activities a
            {activity_where}
            ORDER BY a.name ASC, a.id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(activity_params + [limit, offset]),
        )

        if user_id is None:
            total_entries_stmt = "SELECT COUNT(1) FROM entries"
            total_entries_params: Tuple = ()
            total_activities_stmt = "SELECT COUNT(1) FROM activities"
            total_activities_params: Tuple = ()
        else:
            total_entries_stmt = f"SELECT COUNT(1) FROM entries WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            total_entries_params = (user_id,)
            total_activities_stmt = f"SELECT COUNT(1) FROM activities WHERE {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            total_activities_params = (user_id,)

        total_entries = conn.execute(total_entries_stmt, total_entries_params).scalar_one()
        total_activities = conn.execute(total_activities_stmt, total_activities_params).scalar_one()
        entries = [dict(row) for row in entries_cursor.fetchall()]
        activities = [dict(row) for row in activities_cursor.fetchall()]
        return entries, activities, int(total_entries), int(total_activities)
    finally:
        conn.close()


default_backup_dir = Path(app.root_path) / "backups"
app.config.setdefault("BACKUP_DIR", str(default_backup_dir))

backup_manager = BackupManager(app)

def _normalize_rtsp_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme.lower() != "rtsp":
        raise ValidationError("URL must use rtsp scheme", code="invalid_query")
    if not parsed.hostname:
        raise ValidationError("Invalid stream URL", code="invalid_query")

    normalized = parsed._replace()
    return urlunparse(normalized)


def _drain_process_stream(pipe, collector: list[str]) -> None:
    try:
        for raw in iter(pipe.readline, b""):
            try:
                text = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                text = ""
            if text:
                collector.append(text)
                if len(collector) > 100:
                    del collector[: len(collector) - 100]
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _raise_stream_error(stderr_lines: list[str], return_code: Optional[int]) -> None:
    snippet = "\n".join(stderr_lines[-10:]).lower()
    if "401" in snippet or "unauthorized" in snippet:
        raise PermissionError("Unauthorized stream access")
    raise RuntimeError(f"Unable to proxy stream (ffmpeg exited with code {return_code})")


def stream_rtsp(url: str) -> Iterator[bytes]:
    normalized_url = _normalize_rtsp_url(url)
    command = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        normalized_url,
        "-f",
        "mjpeg",
        "-q:v",
        "5",
        "-an",
        "-sn",
        "-dn",
        "pipe:1",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    if not process.stdout:
        raise RuntimeError("Failed to start stream process")

    stderr_lines: list[str] = []
    stderr_thread: Optional[Thread] = None
    if process.stderr is not None:
        stderr_thread = Thread(
            target=_drain_process_stream,
            args=(process.stderr, stderr_lines),
            daemon=True,
        )
        stderr_thread.start()

    buffer = bytearray()
    frame_emitted = False
    try:
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                if process.poll() is None:
                    continue
                if not frame_emitted:
                    _raise_stream_error(stderr_lines, process.returncode)
                break

            buffer.extend(chunk)
            while True:
                start_idx = buffer.find(b"\xff\xd8")
                if start_idx == -1:
                    if len(buffer) > 65536:
                        buffer.clear()
                    break
                if start_idx > 0:
                    del buffer[:start_idx]
                end_idx = buffer.find(b"\xff\xd9")
                if end_idx == -1:
                    break

                frame = bytes(buffer[: end_idx + 2])
                del buffer[: end_idx + 2]
                frame_emitted = True

                headers = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: "
                    + str(len(frame)).encode()
                    + b"\r\n\r\n"
                )
                yield headers + frame + b"\r\n"
    except GeneratorExit:
        raise
    finally:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                process.wait(timeout=0.5)
        except Exception:
            pass
        try:
            process.stdout.close()
        except Exception:
            pass
        if process.stderr:
            try:
                process.stderr.close()
            except Exception:
                pass
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=0.5)
def get_db_connection():
    return sa_connection(db.engine)


@contextmanager
def db_transaction():
    with transactional_connection(db.engine) as conn:
        yield conn


@app.get("/")
def home():
    return jsonify({"message": "Backend běží!", "database": app.config.get("SQLALCHEMY_DATABASE_URI")})


@app.get("/metrics")
def metrics():
    if (request.args.get("format") or "").lower() == "json":
        return jsonify(get_metrics_json())
    text_body = get_metrics_text()
    return Response(text_body, mimetype="text/plain; version=0.0.4; charset=utf-8")


@app.get("/healthz")
def health():
    summary, healthy = _build_health_summary()
    status_code = 200 if healthy else 503
    return jsonify(summary), status_code


@app.cli.command("health")
@with_appcontext
def health_command():
    summary, healthy = _build_health_summary()
    status_text = "HEALTHY" if healthy else "UNHEALTHY"
    metric_col_width = max(len("Metric"), max(len(key) for key in summary))
    header = f'{"Metric":<{metric_col_width}} | Value'
    divider = "-" * len(header)
    click.echo(header)
    click.echo(divider)
    for key, value in summary.items():
        click.echo(f"{key:<{metric_col_width}} | {value}")
    click.echo(divider)
    click.echo(f"Status: {status_text}")


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
    display_name = payload.get("display_name") or username

    new_user_id: Optional[int] = None
    try:
        with db_transaction() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at, display_name, is_admin) VALUES (?, ?, ?, ?, FALSE)",
                (username, password_hash, datetime.now(timezone.utc).isoformat(), display_name),
            )
            new_row = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if new_row:
                new_user_id = new_row["id"]
    except IntegrityError:
        log_event(
            "auth.register_failed",
            "Username already exists",
            level="warning",
            context={"username": username},
        )
        return error_response("conflict", "Username already exists", 409)

    log_event(
        "auth.register",
        "User registered",
        user_id=new_user_id,
        context={"username": username},
    )
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
    row = None
    is_admin_flag = False
    display_name = None
    try:
        try:
            row = conn.execute(
                """
                SELECT
                    id,
                    password_hash,
                    COALESCE(is_admin, FALSE) AS is_admin,
                    COALESCE(NULLIF(display_name, ''), username) AS display_name
                FROM users
                WHERE username = ?
                """,
                (payload["username"],),
            ).fetchone()
        except SQLAlchemyError as exc:
            error_message = str(exc).lower()
            if "is_admin" not in error_message:
                raise
            row = conn.execute(
                """
                SELECT
                    id,
                    password_hash,
                    FALSE AS is_admin,
                    username AS display_name
                FROM users
                WHERE username = ?
                """,
                (payload["username"],),
            ).fetchone()
    finally:
        conn.close()

    if not row or not check_password_hash(row["password_hash"], payload["password"]):
        log_event(
            "auth.login_failed",
            "Invalid username or password",
            user_id=row["id"] if row else None,
            level="warning",
            context={"username": payload["username"]},
        )
        return error_response("invalid_credentials", "Invalid username or password", 401)

    if row and "is_admin" in row.keys():
        is_admin_flag = bool(row["is_admin"])
    if row and "display_name" in row.keys():
        display_name = row["display_name"]

    access_token, csrf_token = _create_access_token(
        row["id"],
        payload["username"],
        is_admin=is_admin_flag,
        display_name=display_name,
    )
    log_event(
        "auth.login",
        "User logged in",
        user_id=row["id"],
        context={"username": payload["username"], "is_admin": is_admin_flag},
    )
    return jsonify(
        {
            "access_token": access_token,
            "csrf_token": csrf_token,
            "token_type": "Bearer",
            "expires_in": int(app.config.get("JWT_EXP_MINUTES", 60)) * 60,
            "display_name": display_name,
            "is_admin": is_admin_flag,
        }
    )


@app.get("/user")
@jwt_required()
def get_current_user_profile():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    user_id = current_user["id"]
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT
                id,
                username,
                COALESCE(NULLIF(display_name, ''), username) AS display_name,
                COALESCE(is_admin, FALSE) AS is_admin,
                created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return error_response("not_found", "User not found", 404)
    return jsonify(_serialize_user_row(row))


@app.patch("/user")
@jwt_required()
def update_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)

    data = request.get_json(silent=True) or {}
    payload = validate_user_update_payload(data)

    updates = []
    params: list = []
    if "display_name" in payload:
        updates.append("display_name = ?")
        params.append(payload["display_name"].strip())
    if "password" in payload:
        updates.append("password_hash = ?")
        params.append(generate_password_hash(payload["password"]))

    if not updates:
        return jsonify({"message": "No changes detected"}), 200

    params.append(current_user["id"])

    with db_transaction() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        row = conn.execute(
            """
            SELECT
                id,
                username,
                COALESCE(NULLIF(display_name, ''), username) AS display_name,
                COALESCE(is_admin, FALSE) AS is_admin,
                created_at
            FROM users
            WHERE id = ?
            """,
            (current_user["id"],),
        ).fetchone()

    if not row:
        return error_response("not_found", "User not found", 404)

    return jsonify(
        {
            "message": "Profile updated",
            "user": _serialize_user_row(row),
        }
    )


@app.delete("/user")
@jwt_required()
def delete_current_user():
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("unauthorized", "Unauthorized", 401)
    user_id = current_user["id"]

    with db_transaction() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount == 0:
        return error_response("not_found", "User not found", 404)

    invalidate_cache("today")
    invalidate_cache("stats")

    return jsonify({"message": "Account deleted"}), 200


@app.get("/users")
@jwt_required()
@require_admin
def list_users():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                COALESCE(NULLIF(display_name, ''), username) AS display_name,
                COALESCE(is_admin, FALSE) AS is_admin,
                created_at
            FROM users
            ORDER BY LOWER(username) ASC
            """
        ).fetchall()
    finally:
        conn.close()
    return jsonify([_serialize_user_row(row) for row in rows])


@app.delete("/users/<int:user_id>")
@jwt_required()
@require_admin
def admin_delete_user(user_id: int):
    current_user = getattr(g, "current_user", None)
    if current_user and current_user.get("id") == user_id:
        return error_response("invalid_operation", "Admins cannot delete their own account", 400)

    with db_transaction() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    if cur.rowcount == 0:
        return error_response("not_found", "User not found", 404)

    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": f"User {user_id} deleted"}), 200


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


@app.route("/api/stream-proxy", methods=["GET"])
@jwt_required()
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
            stream_with_context(stream_rtsp(rtsp_url)),
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


@app.get("/backup/status")
@jwt_required()
def backup_status():
    try:
        status = backup_manager.get_status()
    except Exception as exc:
        logger.bind(status_code=500).exception("backup.status_error", error=str(exc))
        return error_response("backup_error", "Unable to fetch backup status", 500)
    return jsonify(status)


@app.post("/backup/run")
@jwt_required()
def backup_run():
    operator_id = _current_user_id()
    try:
        result = backup_manager.create_backup(initiated_by="api")
    except Exception as exc:
        logger.bind(status_code=500).exception("backup.run_error", error=str(exc))
        log_event(
            "backup.run_failed",
            "Backup creation failed",
            user_id=operator_id,
            level="error",
            context={"error": str(exc)},
        )
        return error_response("backup_error", "Failed to create backup", 500)
    log_event(
        "backup.run",
        "Backup created",
        user_id=operator_id,
        context={"backup": result},
    )
    return jsonify({"message": "Backup completed", "backup": result})


@app.post("/backup/toggle")
@jwt_required()
def backup_toggle():
    operator_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    enabled = payload.get("enabled")
    interval = payload.get("interval_minutes")

    if enabled is not None and not isinstance(enabled, bool):
        return error_response("invalid_input", "enabled must be a boolean", 400)
    if interval is not None:
        try:
            interval = int(interval)
        except (TypeError, ValueError):
            return error_response("invalid_input", "interval_minutes must be an integer", 400)
        if interval < 5:
            return error_response("invalid_input", "interval_minutes must be at least 5", 400)

    try:
        status = backup_manager.toggle(enabled=enabled, interval_minutes=interval)
    except Exception as exc:
        logger.bind(status_code=500).exception("backup.toggle_error", error=str(exc))
        log_event(
            "backup.toggle_failed",
            "Backup settings update failed",
            user_id=operator_id,
            level="error",
            context={"error": str(exc)},
        )
        return error_response("backup_error", "Unable to update backup settings", 500)
    log_event(
        "backup.toggle",
        "Backup settings updated",
        user_id=operator_id,
        context={"status": status},
    )
    return jsonify({"message": "Backup settings updated", "status": status})


@app.get("/backup/download/<path:filename>")
@jwt_required()
def backup_download(filename: str):
    try:
        path = backup_manager.get_backup_path(filename)
    except ValueError:
        return error_response("invalid_input", "Invalid backup filename", 400)
    except FileNotFoundError:
        return error_response("not_found", "Backup not found", 404)

    log_event(
        "backup.download",
        "Backup downloaded",
        user_id=_current_user_id(),
        context={"filename": filename},
    )
    return send_file(path, as_attachment=True, download_name=path.name)


@app.get("/export/json")
@jwt_required()
def export_json():
    pagination = parse_pagination(default_limit=500, max_limit=2000)
    limit = pagination["limit"]
    offset = pagination["offset"]
    entries, activities, total_entries, total_activities = _fetch_export_data(limit, offset)

    payload = {
        "entries": entries,
        "activities": activities,
        "meta": {
            "entries": {"limit": limit, "offset": offset, "total": total_entries},
            "activities": {"limit": limit, "offset": offset, "total": total_activities},
        },
    }
    response = jsonify(payload)
    return _set_export_headers(
        response,
        "json",
        limit=limit,
        offset=offset,
        total_entries=total_entries,
        total_activities=total_activities,
    )


@app.get("/export/csv")
@jwt_required()
def export_csv():
    pagination = parse_pagination(default_limit=500, max_limit=2000)
    limit = pagination["limit"]
    offset = pagination["offset"]
    entries, activities, total_entries, total_activities = _fetch_export_data(limit, offset)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "dataset",
            "entry_id",
            "date",
            "activity",
            "entry_description",
            "value",
            "note",
            "activity_category",
            "activity_goal",
        ]
    )
    for entry in entries:
        writer.writerow(
            [
                "entries",
                entry.get("entry_id"),
                entry.get("date"),
                entry.get("activity"),
                entry.get("entry_description"),
                entry.get("value"),
                entry.get("note"),
                entry.get("activity_category"),
                entry.get("activity_goal"),
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "dataset",
            "activity_id",
            "name",
            "category",
            "activity_type",
            "goal",
            "activity_description",
            "active",
            "frequency_per_day",
            "frequency_per_week",
            "deactivated_at",
        ]
    )
    for activity in activities:
        writer.writerow(
            [
                "activities",
                activity.get("activity_id"),
                activity.get("name"),
                activity.get("category"),
                activity.get("activity_type"),
                activity.get("goal"),
                activity.get("activity_description"),
                activity.get("active"),
                activity.get("frequency_per_day"),
                activity.get("frequency_per_week"),
                activity.get("deactivated_at"),
            ]
        )

    csv_data = output.getvalue()
    response = Response(csv_data, mimetype="text/csv")
    return _set_export_headers(
        response,
        "csv",
        limit=limit,
        offset=offset,
        total_entries=total_entries,
        total_activities=total_activities,
    )


@app.get("/entries")
def get_entries():
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

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
        if user_id is not None:
            clauses.append(_user_scope_clause("e.user_id", include_unassigned=is_admin))
            params.append(user_id)

        where_sql = ""
        if clauses:
            where_sql = "WHERE " + " AND ".join(clauses)

        query = f"""
            SELECT e.*,
                   COALESCE(a.category, e.activity_category, '') AS category,
                   COALESCE(a.goal, e.activity_goal, 0) AS goal,
                   COALESCE(a.description, e.description, '') AS activity_description
            FROM entries e
            LEFT JOIN activities a
              ON a.name = e.activity
             AND (a.user_id = e.user_id OR a.user_id IS NULL)
            {where_sql}
            ORDER BY e.date DESC, e.activity ASC
        """
        pagination = parse_pagination()
        query += " LIMIT ? OFFSET ?"
        params.extend([pagination["limit"], pagination["offset"]])
        result = conn.execute(query, params)
        entries = [dict(row) for row in result.fetchall()]
        return jsonify(entries)
    except SQLAlchemyError as exc:
        return error_response("database_error", str(exc), 500)
    finally:
        conn.close()


@app.post("/add_entry")
def add_entry():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["add_entry"]
    limited = rate_limit("add_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    idempotency_key = request.headers.get("X-Idempotency-Key")
    cached_response = _idempotency_lookup(user_id, idempotency_key)
    if cached_response:
        payload, status_code = cached_response
        return jsonify(payload), status_code

    data = request.get_json() or {}
    payload = validate_entry_payload(data)
    date = payload["date"]
    activity = payload["activity"]
    note = payload["note"]
    float_value = payload["value"]

    try:
        with db_transaction() as conn:
            activity_row = conn.execute(
                "SELECT category, goal, description FROM activities WHERE name = ? AND user_id = ?",
                (activity, user_id),
            ).fetchone()
            if not activity_row:
                activity_row = conn.execute(
                    "SELECT category, goal, description FROM activities WHERE name = ? AND user_id IS NULL",
                    (activity,),
                ).fetchone()

            description = activity_row["description"] if activity_row else ""
            activity_category = activity_row["category"] if activity_row else ""
            activity_goal = activity_row["goal"] if activity_row else 0

            existing_entry = conn.execute(
                "SELECT activity_category, activity_goal FROM entries WHERE date = ? AND activity = ? AND user_id = ?",
                (date, activity, user_id),
            ).fetchone()
            if not existing_entry:
                existing_entry = conn.execute(
                    "SELECT activity_category, activity_goal FROM entries WHERE date = ? AND activity = ? AND user_id IS NULL",
                    (date, activity),
                ).fetchone()
            if not activity_row and existing_entry:
                activity_category = existing_entry["activity_category"] or activity_category
                activity_goal = (
                    existing_entry["activity_goal"] if existing_entry["activity_goal"] is not None else activity_goal
                )
            if not activity_row:
                # ensure activity exists so that /today and other queries include the new entry
                try:
                    conn.execute(
                        """
                        INSERT INTO activities (
                            name,
                            category,
                            activity_type,
                            goal,
                            description,
                            active,
                            frequency_per_day,
                            frequency_per_week,
                            deactivated_at,
                            user_id
                        )
                        VALUES (?, ?, ?, ?, ?, TRUE, ?, ?, NULL, ?)
                        """,
                        (
                            activity,
                            activity_category or "",
                            "positive",
                            float(activity_goal or 0),
                            description or "",
                            1,
                            1,
                            user_id,
                        ),
                    )
                except IntegrityError:
                    # another request may have created it concurrently; safe to ignore
                    pass

            update_cur = conn.execute(
                """
                UPDATE entries
                SET value = ?,
                    note = ?,
                    description = ?,
                    activity_category = ?,
                    activity_goal = ?,
                    user_id = ?
                WHERE date = ? AND activity = ? AND user_id = ?
                """,
                (
                    float_value,
                    note,
                    description,
                    activity_category,
                    activity_goal,
                    user_id,
                    date,
                    activity,
                    user_id,
                ),
            )

            if update_cur.rowcount > 0:
                response_payload = {"message": "Záznam aktualizován"}
                status_code = 200
                response = jsonify(response_payload), status_code
            else:
                update_cur = conn.execute(
                    """
                    UPDATE entries
                    SET value = ?,
                        note = ?,
                        description = ?,
                        activity_category = ?,
                        activity_goal = ?,
                        user_id = ?
                    WHERE date = ? AND activity = ? AND user_id IS NULL
                    """,
                    (
                        float_value,
                        note,
                        description,
                        activity_category,
                        activity_goal,
                        user_id,
                        date,
                        activity,
                    ),
                )

                if update_cur.rowcount > 0:
                    response_payload = {"message": "Záznam aktualizován"}
                    status_code = 200
                    response = jsonify(response_payload), status_code
                else:
                    conn.execute(
                        """
                    INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (date, activity, description, float_value, note, activity_category, activity_goal, user_id),
                    )
                    response_payload = {"message": "Záznam uložen"}
                    status_code = 201
                    response = jsonify(response_payload), status_code
    except SQLAlchemyError as exc:
        return error_response("database_error", str(exc), 500)
    else:
        invalidate_cache("today")
        invalidate_cache("stats")
        if idempotency_key:
            _idempotency_store_response(user_id, idempotency_key, response_payload, status_code)
        return response


@app.delete("/entries/<int:entry_id>")
def delete_entry(entry_id):
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["delete_entry"]
    limited = rate_limit("delete_entry", limits["limit"], limits["window"])
    if limited:
        return limited

    try:
        with db_transaction() as conn:
            if is_admin:
                cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM entries WHERE id = ? AND user_id = ?",
                    (entry_id, user_id),
                )
        if cur.rowcount == 0:
            log_event(
                "entry.delete_missing",
                "Entry delete attempted but not found",
                user_id=user_id,
                level="warning",
                context={"entry_id": entry_id, "as_admin": is_admin},
            )
            return error_response("not_found", "Záznam nenalezen", 404)
        invalidate_cache("today")
        invalidate_cache("stats")
        log_event(
            "entry.delete",
            "Entry deleted",
            user_id=user_id,
            context={"entry_id": entry_id, "as_admin": is_admin},
        )
        return jsonify({"message": "Záznam smazán"}), 200
    except SQLAlchemyError as exc:
        return error_response("database_error", str(exc), 500)


@app.get("/activities")
def get_activities():
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    show_all = request.args.get("all", "false").lower() in ("1", "true", "yes")
    conn = get_db_connection()
    try:
        pagination = parse_pagination()
        params: list = []
        where_clauses = []
        if user_id is not None:
            where_clauses.append(_user_scope_clause("user_id", include_unassigned=is_admin))
            params.append(user_id)
        if not show_all:
            where_clauses.append("active = TRUE")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        params.extend([pagination["limit"], pagination["offset"]])
        query = f"""
            SELECT *
            FROM activities
            {where_sql}
            ORDER BY active DESC, category ASC, name ASC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, params).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            if "active" in item:
                item["active"] = 1 if bool(item["active"]) else 0
            payload.append(item)
        return jsonify(payload)
    except SQLAlchemyError as exc:
        return error_response("database_error", str(exc), 500)
    finally:
        conn.close()


@app.post("/add_activity")
def add_activity():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["add_activity"]
    limited = rate_limit("add_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    idempotency_key = request.headers.get("X-Idempotency-Key")
    cached_response = _idempotency_lookup(user_id, idempotency_key)
    if cached_response:
        payload, status_code = cached_response
        return jsonify(payload), status_code

    overwrite_requested = _header_truthy(request.headers.get("X-Overwrite-Existing"))

    data = request.get_json() or {}
    payload = validate_activity_create_payload(data)
    name = payload["name"]
    category = payload["category"]
    activity_type = payload["activity_type"]
    goal = payload["goal"]
    description = payload["description"]
    frequency_per_day = payload["frequency_per_day"]
    frequency_per_week = payload["frequency_per_week"]

    try:
        with db_transaction() as conn:
            conn.execute(
                """
                INSERT INTO activities (
                    name,
                    category,
                    activity_type,
                    goal,
                    description,
                    active,
                    frequency_per_day,
                    frequency_per_week,
                    deactivated_at,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, TRUE, ?, ?, NULL, ?)
                """,
                (
                    name,
                    category,
                    activity_type,
                    goal,
                    description,
                    frequency_per_day,
                    frequency_per_week,
                    user_id,
                ),
            )
        invalidate_cache("today")
        invalidate_cache("stats")
        log_event(
            "activity.create",
            "Activity created",
            user_id=user_id,
            context={
                "name": name,
                "category": category,
            },
        )
        response_payload = {"message": "Kategorie přidána"}
        if idempotency_key:
            _idempotency_store_response(user_id, idempotency_key, response_payload, 201)
        return jsonify(response_payload), 201
    except IntegrityError as exc:
        if overwrite_requested:
            with db_transaction() as conn:
                cur = conn.execute(
                    """
                    UPDATE activities
                    SET category = ?, activity_type = ?, goal = ?, description = ?, frequency_per_day = ?, frequency_per_week = ?, active = TRUE, deactivated_at = NULL
                    WHERE name = ? AND user_id = ?
                    """,
                    (
                        category,
                        activity_type,
                        goal,
                        description,
                        frequency_per_day,
                        frequency_per_week,
                        name,
                        user_id,
                    ),
                )
            if cur.rowcount > 0:
                invalidate_cache("today")
                invalidate_cache("stats")
                response_payload = {"message": "Kategorie aktualizována", "overwrite": True}
                if idempotency_key:
                    _idempotency_store_response(user_id, idempotency_key, response_payload, 200)
                return jsonify(response_payload), 200
        logger.exception("activities.insert_conflict", error=str(exc))
        log_event(
            "activity.create_failed",
            "Activity creation failed",
            user_id=user_id,
            level="warning",
            context={"name": name, "error": "duplicate"},
        )
        return error_response(
            "conflict",
            "Kategorie s tímto názvem již existuje",
            409,
            details={"reason": str(getattr(exc.orig, "diag", "")) or str(exc.orig) if getattr(exc, "orig", None) else str(exc)},
        )


@app.put("/activities/<int:activity_id>")
def update_activity(activity_id):
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["update_activity"]
    limited = rate_limit("update_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    data = request.get_json() or {}
    payload = validate_activity_update_payload(data)

    with db_transaction() as conn:
        select_query = "SELECT name, user_id FROM activities WHERE id = ?"
        select_params: list = [activity_id]
        if not is_admin:
            select_query += " AND user_id = ?"
            select_params.append(user_id)
        row = conn.execute(select_query, select_params).fetchone()
        if not row:
            return error_response("not_found", "Aktivita nenalezena", 404)

        owner_user_id = row["user_id"]

        update_clauses = []
        params = []
        for key in (
            "category",
            "activity_type",
            "goal",
            "description",
            "frequency_per_day",
            "frequency_per_week",
        ):
            if key in payload:
                update_clauses.append(f"{key} = ?")
                params.append(payload[key])

        if not update_clauses:
            return jsonify({"message": "No changes detected"}), 200

        params.append(activity_id)
        update_where = "id = ?"
        if not is_admin:
            update_where += " AND user_id = ?"
            params.append(user_id)
        conn.execute(f"UPDATE activities SET {', '.join(update_clauses)} WHERE {update_where}", params)

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
            entry_where = "activity = ?"
            if owner_user_id is not None:
                entry_where += " AND user_id = ?"
                entry_params.append(owner_user_id)
            conn.execute(
                f"UPDATE entries SET {', '.join(entry_update_clauses)} WHERE {entry_where}",
                entry_params,
            )

    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita aktualizována"}), 200


@app.patch("/activities/<int:activity_id>/deactivate")
def deactivate_activity(activity_id):
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_deactivate", limits["limit"], limits["window"])
    if limited:
        return limited
    deactivation_date = datetime.now().strftime("%Y-%m-%d")

    with db_transaction() as conn:
        params = [deactivation_date, activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)
        cur = conn.execute(
            f"UPDATE activities SET active = FALSE, deactivated_at = ? WHERE {where_clause}",
            params,
        )
        if cur.rowcount == 0:
            return error_response("not_found", "Aktivita nenalezena", 404)
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita deaktivována"}), 200


@app.patch("/activities/<int:activity_id>/activate")
def activate_activity(activity_id):
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["activity_status"]
    limited = rate_limit("activities_activate", limits["limit"], limits["window"])
    if limited:
        return limited

    with db_transaction() as conn:
        params = [activity_id]
        where_clause = "id = ?"
        if not is_admin:
            where_clause += " AND user_id = ?"
            params.append(user_id)
        cur = conn.execute(
            f"UPDATE activities SET active = TRUE, deactivated_at = NULL WHERE {where_clause}",
            params,
        )
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

    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    cache_scope = CacheScope(user_id, is_admin)
    cache_key_parts = ("dashboard", target_date.isoformat())
    cached = cache_get("stats", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return jsonify(cached)

    today_str = target_date.strftime("%Y-%m-%d")
    window_30_start = (target_date - timedelta(days=29)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    try:
        activity_goal_sql = """
            SELECT
                COALESCE(NULLIF(category, ''), 'Other') AS category,
                COALESCE(SUM(goal), 0) AS total_goal
            FROM activities
            WHERE active = TRUE
        """
        activity_goal_params: list = []
        if user_id is not None:
            activity_goal_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            activity_goal_params.append(user_id)
        activity_goal_sql += "\n            GROUP BY category"
        activity_goal_rows = conn.execute(activity_goal_sql, activity_goal_params).fetchall()

        total_active_goal = 0.0
        category_goal_totals: Dict[str, float] = {}
        for row in activity_goal_rows:
            category_name = row["category"] or "Other"
            goal_value = max(float(row["total_goal"] or 0.0), 0.0)
            category_goal_totals[category_name] = goal_value
            total_active_goal += goal_value

        def compute_ratio(total_value: Optional[float]) -> float:
            if total_active_goal <= 0:
                return 0.0
            value = max(float(total_value or 0.0), 0.0)
            return min(value / total_active_goal, 1.0)

        daily_sql = """
            SELECT
                date,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        daily_params: list = [window_30_start, today_str]
        if user_id is not None:
            daily_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            daily_params.append(user_id)
        daily_sql += "\n            GROUP BY date"
        daily_rows = conn.execute(daily_sql, daily_params).fetchall()

        daily_completion = {}
        for row in daily_rows:
            ratio = compute_ratio(row["total_value"])
            daily_completion[row["date"]] = ratio

        category_daily_sql = """
            SELECT
                date,
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COALESCE(SUM(value), 0) AS total_value,
                COALESCE(SUM(activity_goal), 0) AS total_goal
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        category_daily_params: list = [window_30_start, today_str]
        if user_id is not None:
            category_daily_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            category_daily_params.append(user_id)
        category_daily_sql += "\n            GROUP BY date, category"
        category_daily_rows = conn.execute(category_daily_sql, category_daily_params).fetchall()

        categories_seen = set(category_goal_totals.keys())
        category_daily_completion: Dict[str, Dict[str, float]] = defaultdict(dict)
        for row in category_daily_rows:
            category = row["category"] or "Other"
            categories_seen.add(category)
            denominator = category_goal_totals.get(category, 0.0)
            if denominator <= 0:
                denominator = max(float(row["total_goal"] or 0.0), 0.0)
            total_value = max(float(row["total_value"] or 0.0), 0.0)
            if denominator <= 0:
                ratio = 0.0
            else:
                ratio = min(total_value / denominator, 1.0)
            category_daily_completion[category][row["date"]] = ratio

        streak_length = 0
        active_day_threshold = 0.5
        for offset in range(1, 31):
            key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
            if daily_completion.get(key, 0.0) >= active_day_threshold:
                streak_length += 1
            else:
                break

        goal_ratio_today = daily_completion.get(today_str, 0.0)
        goal_completion_today = round(min(goal_ratio_today * 100, 100.0), 1)


        distribution_sql = """
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                COUNT(*) AS entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        distribution_params: list = [window_30_start, today_str]
        if user_id is not None:
            distribution_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            distribution_params.append(user_id)
        distribution_sql += """
            GROUP BY COALESCE(NULLIF(activity_category, ''), 'Other')
            ORDER BY entry_count DESC, LOWER(COALESCE(NULLIF(activity_category, ''), 'Other')) ASC
        """
        distribution_rows = conn.execute(distribution_sql, distribution_params).fetchall()

        total_entries = sum(int(row["entry_count"] or 0) for row in distribution_rows)
        activity_distribution = []
        for row in distribution_rows:
            count = int(row["entry_count"] or 0)
            percent = round((count / total_entries) * 100, 1) if total_entries else 0.0
            category_name = row["category"] or "Other"
            categories_seen.add(category_name)
            activity_distribution.append(
                {
                    "category": category_name,
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

        active_days = 0
        for offset in range(1, 31):
            key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
            if daily_completion.get(key, 0.0) >= active_day_threshold:
                active_days += 1
        active_days_ratio = {
            "active_days": active_days,
            "total_days": 30,
            "percent": round((active_days / 30) * 100, 1) if active_days else 0.0,
        }

        pos_neg_sql = """
            SELECT
                SUM(CASE WHEN COALESCE(value, 0) > 0 THEN 1 ELSE 0 END) AS positive_count,
                SUM(CASE WHEN COALESCE(value, 0) = 0 THEN 1 ELSE 0 END) AS negative_count
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        pos_neg_params: list = [window_30_start, today_str]
        if user_id is not None:
            pos_neg_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            pos_neg_params.append(user_id)
        pos_neg_row = conn.execute(pos_neg_sql, pos_neg_params).fetchone()

        positive_count = int(pos_neg_row["positive_count"] or 0)
        negative_count = int(pos_neg_row["negative_count"] or 0)
        ratio_value = round(positive_count / max(negative_count, 1), 1)
        positive_vs_negative = {
            "positive": positive_count,
            "negative": negative_count,
            "ratio": ratio_value,
        }

        consistent_sql = """
            SELECT
                COALESCE(NULLIF(activity_category, ''), 'Other') AS category,
                activity AS name,
                COUNT(DISTINCT date) AS active_days
            FROM entries
            WHERE date BETWEEN ? AND ?
        """
        consistent_params: list = [window_30_start, today_str]
        if user_id is not None:
            consistent_sql += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            consistent_params.append(user_id)
        consistent_sql += """
            GROUP BY COALESCE(NULLIF(activity_category, ''), 'Other'), activity
            ORDER BY LOWER(COALESCE(NULLIF(activity_category, ''), 'Other')) ASC, active_days DESC, LOWER(activity) ASC
        """
        consistent_rows = conn.execute(consistent_sql, consistent_params).fetchall()

        consistent_by_category: Dict[str, list[dict]] = defaultdict(list)
        for row in consistent_rows:
            days_present = int(row["active_days"] or 0)
            percent = round((days_present / 30) * 100, 1) if days_present else 0.0
            category_name = row["category"] or "Other"
            categories_seen.add(category_name)
            consistent_by_category[category_name].append(
                {
                    "name": row["name"],
                    "consistency_percent": percent,
                }
            )

        top_consistent_activities_by_category = []
        for category_name in sorted(consistent_by_category.keys(), key=lambda value: value.lower()):
            activities = consistent_by_category[category_name][:3]
            top_consistent_activities_by_category.append(
                {
                    "category": category_name,
                    "activities": activities,
                }
            )

        avg_goal_fulfillment_by_category = []
        for category_name in sorted(categories_seen, key=lambda value: value.lower()):
            category_ratios = category_daily_completion.get(category_name, {})
            last_7_total = 0.0
            last_30_total = 0.0
            for offset in range(1, 8):
                key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
                last_7_total += category_ratios.get(key, 0.0)
            for offset in range(1, 31):
                key = (target_date - timedelta(days=offset)).strftime("%Y-%m-%d")
                last_30_total += category_ratios.get(key, 0.0)
            avg_goal_fulfillment_by_category.append(
                {
                    "category": category_name,
                    "last_7_days": round((last_7_total / 7) * 100, 1),
                    "last_30_days": round((last_30_total / 30) * 100, 1),
                }
            )

        payload = {
            "goal_completion_today": goal_completion_today,
            "streak_length": streak_length,
            "activity_distribution": activity_distribution,
            "avg_goal_fulfillment": avg_goal_fulfillment,
            "active_days_ratio": active_days_ratio,
            "positive_vs_negative": positive_vs_negative,
            "avg_goal_fulfillment_by_category": avg_goal_fulfillment_by_category,
            "top_consistent_activities_by_category": top_consistent_activities_by_category,
        }
        cache_set("stats", cache_key_parts, payload, STATS_CACHE_TTL, scope=cache_scope)
        return jsonify(payload)
    finally:
        conn.close()


@app.get("/today")
def get_today():
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    pagination = parse_pagination(default_limit=200)
    cache_scope = CacheScope(user_id, is_admin)
    cache_key_parts = (date, pagination["limit"], pagination["offset"])
    cached = cache_get("today", cache_key_parts, scope=cache_scope)
    if cached is not None:
        return jsonify(cached)
    conn = get_db_connection()
    try:
        join_clause = "LEFT JOIN entries e ON e.activity = a.name AND e.date = ?"
        join_params: list = [date]
        if user_id is not None:
            join_clause += f" AND {_user_scope_clause('e.user_id', include_unassigned=is_admin)}"
            join_params.append(user_id)

        where_conditions = [
            "(a.active = TRUE OR (a.deactivated_at IS NOT NULL AND ? < a.deactivated_at))"
        ]
        where_params: list = [date]
        if user_id is not None:
            where_conditions.append(_user_scope_clause("a.user_id", include_unassigned=is_admin))
            where_params.append(user_id)

        where_sql = "WHERE " + " AND ".join(where_conditions)

        query = f"""
            SELECT
                a.id AS activity_id,
                a.name,
                a.category,
                a.activity_type,
                a.description,
                a.active,
                a.deactivated_at,
                a.goal,
                e.id AS entry_id,
                e.value,
                e.note,
                e.activity_goal
            FROM activities a
            {join_clause}
            {where_sql}
            ORDER BY a.name ASC
            LIMIT ? OFFSET ?
        """
        params = join_params + where_params + [pagination["limit"], pagination["offset"]]
        rows = conn.execute(query, params)
        rows = rows.fetchall()
        data = []
        for r in rows:
            item = dict(r)
            if "active" in item:
                item["active"] = 1 if bool(item["active"]) else 0
            data.append(item)
    finally:
        conn.close()
    cache_set("today", cache_key_parts, data, TODAY_CACHE_TTL, scope=cache_scope)
    return jsonify(data)


@app.delete("/activities/<int:activity_id>")
def delete_activity(activity_id):
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["delete_activity"]
    limited = rate_limit("delete_activity", limits["limit"], limits["window"])
    if limited:
        return limited

    with db_transaction() as conn:
        select_query = "SELECT active FROM activities WHERE id = ?"
        select_params: list = [activity_id]
        if not is_admin:
            select_query += " AND user_id = ?"
            select_params.append(user_id)
        row = conn.execute(select_query, select_params).fetchone()
        if not row:
            return error_response("not_found", "Aktivita nenalezena", 404)
        if bool(row["active"]):
            return error_response("invalid_state", "Aktivitu nelze smazat, nejprve ji deaktivujte", 400)

        delete_query = "DELETE FROM activities WHERE id = ?"
        delete_params: list = [activity_id]
        if not is_admin:
            delete_query += " AND user_id = ?"
            delete_params.append(user_id)
        conn.execute(delete_query, delete_params)
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": "Aktivita smazána"}), 200


@app.post("/finalize_day")
def finalize_day():
    user_id = _current_user_id()
    is_admin = _is_admin_user()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"]["finalize_day"]
    limited = rate_limit("finalize_day", limits["limit"], limits["window"])
    if limited:
        return limited

    payload = validate_finalize_day_payload(request.get_json() or {})
    date = payload["date"]

    with db_transaction() as conn:
        # získej všechny aktivní aktivity
        active_query = """
            SELECT name, description, category, goal
            FROM activities
            WHERE active = TRUE
               OR (deactivated_at IS NOT NULL AND ? < deactivated_at)
        """
        active_params: list = [date]
        if user_id is not None:
            active_query += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            active_params.append(user_id)
        active_activities = conn.execute(active_query, active_params).fetchall()
        existing_query = "SELECT activity FROM entries WHERE date = ?"
        existing_params: list = [date]
        if user_id is not None:
            existing_query += f" AND {_user_scope_clause('user_id', include_unassigned=is_admin)}"
            existing_params.append(user_id)
        existing = conn.execute(existing_query, existing_params).fetchall()
        existing_names = {e["activity"] for e in existing}

        created = 0
        for a in active_activities:
            if a["name"] not in existing_names:
                conn.execute(
                    """
                    INSERT INTO entries (date, activity, description, value, note, activity_category, activity_goal, user_id)
                    VALUES (?, ?, ?, 0, '', ?, ?, ?)
                    """,
                    (date, a["name"], a["description"], a["category"], a["goal"], user_id),
                )
                created += 1
    invalidate_cache("today")
    invalidate_cache("stats")
    return jsonify({"message": f"{created} missing entries added for {date}"}), 200


@app.post("/ingest/wearable/batch")
def ingest_wearable_batch():
    user_id = _current_user_id()
    if user_id is None:
        return error_response("unauthorized", "Missing user context", 401)

    limits = app.config["RATE_LIMITS"].get("wearable_ingest", {"limit": 60, "window": 60})
    limited = rate_limit("wearable_ingest", limits["limit"], limits["window"])
    if limited:
        return limited

    payload = validate_wearable_batch_payload(request.get_json() or {})
    source_app = payload["source_app"]
    device_id = payload["device_id"]
    tz_name = payload["tz"]
    tzinfo = ZoneInfo(tz_name)
    records = payload["records"]

    accepted = 0
    duplicates = 0
    errors: list[dict] = []
    accepted_dedupes: list[str] = []
    now_iso = _utcnow().isoformat()
    source_key = f"{user_id}:{source_app.lower()}:{device_id}"
    sync_metadata = json.dumps({"tz": tz_name})

    with db_transaction() as conn:
        source_row = conn.execute(
            "SELECT id FROM wearable_sources WHERE dedupe_key = ?",
            (source_key,),
        ).fetchone()
        if source_row:
            source_id = source_row["id"]
            conn.execute(
                "UPDATE wearable_sources SET updated_at = ?, sync_metadata = ? WHERE id = ?",
                (now_iso, sync_metadata, source_id),
            )
        else:
            insert_result = conn.execute(
                """
                INSERT INTO wearable_sources (
                    user_id,
                    provider,
                    external_id,
                    display_name,
                    sync_metadata,
                    last_synced_at,
                    dedupe_key,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?)
                RETURNING id
                """,
                (
                    user_id,
                    source_app,
                    device_id,
                    source_app,
                    sync_metadata,
                    source_key,
                    now_iso,
                    now_iso,
                ),
            )
            new_row = insert_result.fetchone()
            source_id = new_row["id"] if new_row else None

        if source_id is None:
            return error_response("internal_error", "Unable to resolve wearable source", 500)

        insert_sql = """
            INSERT INTO wearable_raw (
                user_id,
                source_id,
                collected_at_utc,
                received_at_utc,
                payload,
                dedupe_key,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (dedupe_key) DO NOTHING
        """

        for index, record in enumerate(records):
            start_dt = record["start"]
            end_dt = record.get("end")
            try:
                collected_utc = _coerce_utc(start_dt, tzinfo)
                end_utc = _coerce_utc(end_dt, tzinfo) if end_dt else None
                if end_utc and end_utc < collected_utc:
                    raise ValueError("end cannot be before start")
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "dedupe_key": record["dedupe_key"],
                        "reason": str(exc),
                    }
                )
                continue

            record_payload = {
                "type": record["type"],
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat() if end_dt else None,
                "fields": record["fields"],
                "tz": tz_name,
                "source_app": source_app,
                "device_id": device_id,
            }
            try:
                payload_json = json.dumps(record_payload)
            except (TypeError, ValueError) as exc:
                errors.append(
                    {
                        "index": index,
                        "dedupe_key": record["dedupe_key"],
                        "reason": f"Invalid fields payload: {exc}",
                    }
                )
                continue

            result = conn.execute(
                insert_sql,
                (
                    user_id,
                    source_id,
                    collected_utc.isoformat(),
                    now_iso,
                    payload_json,
                    record["dedupe_key"],
                    now_iso,
                ),
            )
            if result.rowcount:
                accepted += 1
                accepted_dedupes.append(record["dedupe_key"])
            else:
                duplicates += 1

    logger.bind(
        user_id=user_id,
        source_app=source_app,
        device_id=device_id,
        records=len(records),
        accepted=accepted,
        duplicates=duplicates,
        errors=len(errors),
    ).info("wearable.ingest_batch")

    status_code = 201 if accepted > 0 else 200
    etl_summary = {"processed": 0, "skipped": 0, "errors": [], "aggregated": 0}
    try:
        etl_summary = process_wearable_raw_by_dedupe_keys(accepted_dedupes)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("wearable.ingest.etl_failed", error=str(exc))
        errors.append({"reason": f"ETL failure: {exc}"})
        status_code = 500

    response_payload = {
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
        "etl": etl_summary,
    }
    return jsonify(response_payload), status_code


@app.post("/import_csv")
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



if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug)
