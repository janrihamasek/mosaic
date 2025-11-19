import logging
import os
import subprocess as _subprocess
import sys
import time as _time
from typing import Optional

import click
import jwt  # type: ignore[import]
import structlog
from flask import Flask, Response, g, jsonify, request
from flask.cli import with_appcontext
from flask_cors import CORS
from https_utils import resolve_ssl_context
from infra import health_service, metrics_manager
from infra.cache_manager import invalidate_cache, set_time_provider
from models import Activity, Entry  # noqa: F401 - ensure models registered
from services import nightmotion_service
from werkzeug.exceptions import HTTPException

# Expose streaming helper for legacy callers/tests
stream_rtsp = nightmotion_service.stream_rtsp
from extensions import db, migrate
from security import ValidationError, error_response, require_api_key


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

from audit import install_runtime_log_handler  # noqa: E402
from routes.logs import logs_bp  # noqa: E402
from wearable_read import wearable_read_bp  # noqa: E402

install_runtime_log_handler()

logger = structlog.get_logger("mosaic.backend")
SERVER_START_TIME = metrics_manager._SERVER_START_TIME

metrics_manager.ensure_metrics_logger_started()
get_metrics_json = metrics_manager.get_metrics_json
get_metrics_text = metrics_manager.get_metrics_text
reset_metrics_state = metrics_manager.reset_metrics_state

subprocess = _subprocess
# Re-export utilities referenced by tests; `time` is a callable so monkeypatching works.
time = lambda: _time.time()
# Ensure cache manager uses the current `app.time`, respecting monkeypatch changes.
set_time_provider(lambda: time())
backup_manager = None  # initialized after extensions setup


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
        super().run(
            host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options
        )


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
app.config.setdefault(
    "JWT_EXP_MINUTES", int(os.environ.get("MOSAIC_JWT_EXP_MINUTES", "60"))
)
app.config["PUBLIC_ENDPOINTS"].update(
    {"login", "register", "metrics", "health", "healthz"}
)

db.init_app(app)
migrate.init_app(app, db)
from backup_manager import BackupManager
backup_manager = BackupManager(app)
app.register_blueprint(logs_bp)
app.register_blueprint(wearable_read_bp)

# Simple home endpoint used by health checks/tests
@app.get("/")
def home():
    return jsonify({"status": "ok"}), 200

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
    endpoint = request.endpoint or (
        request.url_rule.rule if getattr(request, "url_rule", None) else request.path
    )
    if isinstance(endpoint, str) and "." in endpoint:
        endpoint = endpoint.split(".", 1)[1]
    g.metrics_endpoint = endpoint
    g.metrics_method = (request.method or "GET").upper()


@app.after_request
def _log_request(response: Response):
    try:
        start = getattr(g, "metrics_start_time", None)
        if start is not None:
            duration_ms = (metrics_manager.now_perf_counter() - start) * 1000
        else:
            duration_ms = 0.0
        metrics_manager.record_request_metrics(
            g.metrics_method, g.metrics_endpoint, response.status_code, duration_ms
        )
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
        duration_ms = (
            (metrics_manager.now_perf_counter() - start) * 1000 if start else 0.0
        )
        metrics_manager.record_request_metrics(
            getattr(g, "metrics_method", request.method or "GET"),
            getattr(g, "metrics_endpoint", request.endpoint or request.path or "<unknown>"),
            500,
            duration_ms,
            is_error=True,
        )
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


@app.errorhandler(Exception)
def handle_unexpected_exception(exc: Exception):
    logger.bind(status_code=500).exception(
        "request.unhandled_exception", error=str(exc)
    )
    return error_response("internal_error", "An unexpected error occurred", 500)


@app.cli.command("health")
@with_appcontext
def health_command():
    summary, healthy = health_service.build_health_summary(SERVER_START_TIME)
    status_label = "HEALTHY" if healthy else "UNHEALTHY"
    click.echo("Metrics:")
    for key, value in summary.items():
        click.echo(f"{key}: {value}")
    click.echo(f"Status: {status_label}")


from controllers import register_controllers

register_controllers(app)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug)
