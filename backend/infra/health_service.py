import time
from typing import Dict, Tuple

from infra import cache_manager, metrics_manager
from repositories import health_repo


def check_db_connection() -> bool:
    try:
        return health_repo.check_database_connection()
    except Exception as exc:
        metrics_manager.logger.warning("health.db_check_failed", error=str(exc))
        return False


def check_cache_state() -> bool:
    try:
        return cache_manager.cache_health()
    except Exception as exc:
        metrics_manager.logger.warning("health.cache_check_failed", error=str(exc))
        return False


def current_uptime_seconds(server_start_time: float) -> float:
    return max(0.0, time.time() - server_start_time)


def build_health_summary(server_start_time: float) -> Tuple[Dict[str, object], bool]:
    metrics_snapshot = metrics_manager.get_metrics_json()
    uptime_s = round(current_uptime_seconds(server_start_time), 2)
    requests_total = metrics_snapshot["requests_total"]
    uptime_minutes = uptime_s / 60 if uptime_s else 0.0
    if uptime_minutes <= 0:
        req_per_min = float(requests_total)
    else:
        req_per_min = requests_total / uptime_minutes
    error_total = (
        metrics_snapshot["errors_total"]["4xx"]
        + metrics_snapshot["errors_total"]["5xx"]
    )
    error_rate = error_total / requests_total if requests_total else 0.0
    db_ok = check_db_connection()
    cache_ok = check_cache_state()
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
