import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from extensions import db
from models import ActivityLog

_RUNTIME_LOG_LIMIT = 500
_runtime_log_buffer = deque(maxlen=_RUNTIME_LOG_LIMIT)
_runtime_log_lock = Lock()


class _StructlogBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": message,
        }
        with _runtime_log_lock:
            _runtime_log_buffer.append(payload)


_runtime_log_handler = _StructlogBufferHandler()
_runtime_log_handler.setLevel(logging.INFO)


def install_runtime_log_handler() -> None:
    """Attach a handler that keeps a rolling buffer of structlog output."""
    root_logger = logging.getLogger()
    if any(isinstance(handler, _StructlogBufferHandler) for handler in root_logger.handlers):
        return
    root_logger.addHandler(_runtime_log_handler)


audit_logger = structlog.get_logger("mosaic.audit")


def _normalize_level(level: str) -> str:
    return (level or "info").strip().lower() or "info"


def _safe_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {}
    safe: Dict[str, Any] = {}
    for key, value in context.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, dict):
            safe[key] = _safe_context(value)
        else:
            safe[key] = str(value)
    return safe


def _persist_log(
    *,
    timestamp: datetime,
    user_id: Optional[int],
    event_type: str,
    message: str,
    level: str,
    context: Dict[str, Any],
) -> None:
    session = db.session
    try:
        session.add(
            ActivityLog(
                timestamp=timestamp,
                user_id=user_id,
                event_type=event_type,
                message=message,
                context=context,
                level=level,
            )
        )
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        if is_activity_log_table_missing_error(exc):
            audit_logger.warning(
                "activity_log.table_missing",
                event_type=event_type,
                user_id=user_id,
                message=message,
                details="Activity log table missing. Apply latest migrations.",
            )
        else:
            audit_logger.error(
                "activity_log.persist_failed",
                event_type=event_type,
                user_id=user_id,
                error=str(exc),
            )


def log_event(
    event_type: str,
    message: str,
    *,
    user_id: Optional[int] = None,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist the event and mirror it to structlog."""
    normalized_level = _normalize_level(level)
    normalized_context = _safe_context(context)
    timestamp = datetime.now(timezone.utc)

    log_method = getattr(audit_logger, normalized_level, audit_logger.info)
    log_method(
        "activity_event",
        event_type=event_type,
        user_id=user_id,
        message=message,
        context=normalized_context,
    )

    _persist_log(
        timestamp=timestamp,
        user_id=user_id,
        event_type=event_type,
        message=message,
        level=normalized_level,
        context=normalized_context,
    )


def get_runtime_logs(limit: Optional[int] = None) -> list[Dict[str, Any]]:
    with _runtime_log_lock:
        items = list(_runtime_log_buffer)
    if limit is not None:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = None
    if limit is None or limit >= len(items):
        return items
    return items[-limit:]


def _extract_error_message(exc: SQLAlchemyError) -> str:
    if isinstance(exc, (ProgrammingError, OperationalError)) and getattr(exc, "orig", None):
        return str(exc.orig).lower()
    return str(exc).lower()


def is_activity_log_table_missing_error(exc: SQLAlchemyError) -> bool:
    message = _extract_error_message(exc)
    if "activity_logs" not in message:
        return False
    indicators = (
        "does not exist",
        "no such table",
        "undefined table",
        "relation 'activity_logs' does not exist",
        "relation \"activity_logs\" does not exist",
    )
    return any(indicator in message for indicator in indicators)
