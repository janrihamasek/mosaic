import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock, Thread
from time import perf_counter, sleep, time
from typing import DefaultDict, Dict, List, Optional, Tuple, TypedDict

import structlog

logger = structlog.get_logger("mosaic.backend.metrics")


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


def initialize_metrics_state() -> MetricsState:
    return MetricsState(
        requests_total=0,
        latency_total_ms=0.0,
        errors_4xx=0,
        errors_5xx=0,
        status_counts=defaultdict(int),
        per_endpoint=defaultdict(_endpoint_bucket_factory),
        last_updated=None,
    )


_metrics_state: MetricsState = initialize_metrics_state()
_metrics_lock = Lock()
_metrics_logger_thread: Optional[Thread] = None
_SERVER_START_TIME = time()
_METRICS_LOG_INTERVAL_SECONDS = int(
    os.environ.get("METRICS_LOG_INTERVAL_SECONDS", "60")
)


def resolve_metrics_dimensions(method: str, endpoint: str) -> Tuple[str, str]:
    normalized_method = (method or "GET").upper()
    normalized_endpoint = endpoint or "<unmatched>"
    return normalized_method, normalized_endpoint


def record_request_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    *,
    is_error: bool = False,
) -> None:
    method, endpoint = resolve_metrics_dimensions(method, endpoint)
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


def now_perf_counter() -> float:
    """Indirection so tests can monkeypatch perf_counter reliably."""
    return getattr(sys.modules[__name__], "perf_counter")()


def reset_metrics_state() -> None:
    """Reset the in-memory metrics store. Intended for use in tests."""
    global _metrics_state
    with _metrics_lock:
        _metrics_state = initialize_metrics_state()


def format_timestamp(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


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
                        str(code): value
                        for code, value in bucket["status_counts"].items()
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
                str(code): value
                for code, value in _metrics_state["status_counts"].items()
            },
            endpoints=endpoints,
            last_updated=format_timestamp(last_updated),
        )


def get_metrics_text() -> str:
    snapshot = get_metrics_json()
    lines = [
        "# HELP mosaic_requests_total Total HTTP requests processed by the Mosaic backend",
        "# TYPE mosaic_requests_total counter",
    ]
    for entry in snapshot["endpoints"]:
        lines.append(
            f'mosaic_requests_total{{method="{entry["method"]}",endpoint="{entry["endpoint"]}"}} {entry["count"]}'
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
    lines.append(f'mosaic_request_latency_ms_average {snapshot["avg_latency_ms"]}')

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


def _metrics_logger_loop() -> None:
    while True:
        sleep(_METRICS_LOG_INTERVAL_SECONDS)
        snapshot = get_metrics_json()
        logger.info("metrics.snapshot", metrics=snapshot)


def ensure_metrics_logger_started() -> None:
    global _metrics_logger_thread
    if _metrics_logger_thread and _metrics_logger_thread.is_alive():
        return
    thread = Thread(target=_metrics_logger_loop, daemon=True, name="metrics-logger")
    thread.start()
    _metrics_logger_thread = thread
