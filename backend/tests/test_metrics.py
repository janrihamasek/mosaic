import itertools
from typing import Any, Dict

import app as app_module
import pytest
from app import app, get_metrics_json, get_metrics_text, reset_metrics_state
from infra import metrics_manager


@app.get("/__metrics_test__/boom", endpoint="metrics_test_boom")
def metrics_test_boom():
    raise RuntimeError("boom")


app.config["PUBLIC_ENDPOINTS"].add("metrics_test_boom")


def _find_endpoint_metrics(snapshot: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    return next(
        entry for entry in snapshot["endpoints"] if entry["endpoint"] == endpoint
    )


def test_metrics_counts_and_latency(client, monkeypatch):
    reset_metrics_state()
    perf_values = itertools.chain([0.0, 0.05, 0.05, 0.25], itertools.repeat(0.25))

    def fake_perf_counter():
        return next(perf_values)

    monkeypatch.setattr(metrics_manager, "perf_counter", fake_perf_counter)

    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 200

    snapshot: Dict[str, Any] = get_metrics_json()
    assert snapshot["requests_total"] == 2
    home_metrics = _find_endpoint_metrics(snapshot, "home")
    assert home_metrics["count"] == 2
    assert home_metrics["total_latency_ms"] == pytest.approx(250.0, abs=0.01)
    assert home_metrics["avg_latency_ms"] == pytest.approx(125.0, abs=0.01)

    text_body = get_metrics_text()
    assert 'mosaic_requests_total{method="GET",endpoint="home"} 2' in text_body


def test_metrics_error_counters(client):
    reset_metrics_state()
    response = client.post("/register", json={})
    assert response.status_code == 400

    response = client.get("/__metrics_test__/boom")
    assert response.status_code == 500

    snapshot: Dict[str, Any] = get_metrics_json()
    assert snapshot["errors_total"]["4xx"] == 1
    assert snapshot["errors_total"]["5xx"] == 1
    register_metrics = _find_endpoint_metrics(snapshot, "register")
    assert register_metrics["errors_4xx"] == 1
    boom_metrics = _find_endpoint_metrics(snapshot, "metrics_test_boom")
    assert boom_metrics["errors_5xx"] == 1
