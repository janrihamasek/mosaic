import app as app_module
from app import app, reset_metrics_state


def _assert_health_payload(payload: dict) -> None:
    for key in ("uptime_s", "db_ok", "cache_ok", "req_per_min", "error_rate", "last_metrics_update"):
        assert key in payload


def test_health_endpoint_ok(client):
    reset_metrics_state()
    assert client.get("/").status_code == 200

    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.get_json()
    _assert_health_payload(payload)
    assert payload["db_ok"] is True
    assert payload["cache_ok"] is True
    assert payload["last_metrics_update"] is not None
    assert payload["error_rate"] == 0


def test_health_endpoint_unhealthy_on_db_failure(client, monkeypatch):
    reset_metrics_state()
    client.get("/")
    monkeypatch.setattr(app_module, "_check_db_connection", lambda: False)

    response = client.get("/healthz")
    assert response.status_code == 503
    payload = response.get_json()
    _assert_health_payload(payload)
    assert payload["db_ok"] is False
    assert payload["cache_ok"] is True


def test_health_cli_output(client):
    reset_metrics_state()
    client.get("/")
    runner = app.test_cli_runner()
    result = runner.invoke(args=["health"])
    assert result.exit_code == 0
    assert "Metric" in result.output
    assert "Status: HEALTHY" in result.output
