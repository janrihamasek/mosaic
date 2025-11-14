# Mosaic Logging & Metrics Guide

The backend emits JSON-formatted logs via [structlog](https://www.structlog.org/) and exposes lightweight runtime counters through `GET /metrics`. This guide summarises field structure, log levels, and practical inspection workflows.

---

## Log Record Schema

Each log line is a single JSON object flushed to stdout. Common fields:

| Field | Description |
| --- | --- |
| `timestamp` | ISO 8601 timestamp (UTC) when the message was emitted. |
| `level` | Severity (`info`, `warning`, `error`). |
| `event` | Short action identifier (e.g. `request.completed`, `request.http_exception`). |
| `request_id` | 16-character hex identifier bound per request. |
| `route` / `path` / `method` | Flask endpoint name, raw path, and HTTP method. |
| `status_code` | HTTP status code for the response (if available). |
| `duration_ms` | Request latency in milliseconds. |
| `user_id` | Authenticated user id (when available). |
| `error` / `details` | Error message or structured metadata for failures. |

### Example

```json
{
  "timestamp": "2025-11-03T10:12:45.823Z",
  "level": "info",
  "event": "request.completed",
  "request_id": "7f0c1c9c2dd44a6e",
  "route": "today",
  "path": "/today",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 18.42,
  "user_id": 3
}
```

Errors include stack traces keyed under `exception` plus the textual `error`.

---

## Log Levels

| Level | Usage |
| --- | --- |
| `info` | Normal control flow: request completions, scheduled tasks, background operations. |
| `warning` | Client-induced issues: validation errors, rate limits, 4xx responses. |
| `error` | Server-side failures: unhandled exceptions, backup scheduler errors, unexpected 5xx responses. |

Choose the lowest level that communicates actionable context. The default filtering threshold is `INFO`.

---

## Accessing Logs

| Context | Command |
| --- | --- |
| Local dev server | `flask run` prints JSON logs directly to the terminal. |
| Docker containers | `docker compose logs -f mosaic_backend_dev` (swap service name as required). |
| CI (GitHub Actions) | Check the “backend” job logs in the Actions UI; they stream structlog output. |

### Filtering Examples

```bash
# Pretty-print logs from dev backend
docker compose logs mosaic_backend_dev | jq .

# Only show errors
docker compose logs mosaic_backend_dev | jq -c 'select(.level == "error")'

# Tail live logs and watch slow requests (latency > 500 ms)
docker compose logs -f mosaic_backend_dev \
  | jq -c 'select(.event == "request.completed" and (.duration_ms // 0) > 500)'

# Grep for a specific request id (if jq not available)
docker compose logs mosaic_backend_dev | grep 7f0c1c9c2dd44a6e
```

For lightweight visualization, forward logs through `jq` into tooling such as `lnav` or ship to an external stack (Elastic, Loki) using Docker log drivers.

---

## Runtime Metrics (`GET /metrics`)

The backend maintains in-memory counters updated via request hooks. Example response:

```json
{
  "requests_total": 1523,
  "errors_total": 12,
  "avg_latency_ms": 47.82,
  "status_counts": {
    "200": 1467,
    "400": 32,
    "401": 18,
    "500": 6
  }
}
```

Field descriptions:

- `requests_total`: Total number of HTTP responses emitted since process start.
- `errors_total`: Count of requests resulting in 5xx responses or teardown exceptions.
- `avg_latency_ms`: Mean latency across all tracked requests.
- `status_counts`: Per-status distributions (keys are stringified HTTP codes).

Retrieve metrics locally:

```bash
curl http://localhost:5000/metrics | jq .
# For prod container
curl http://localhost:5001/metrics | jq .
```

These counters reset when the process restarts. For longer retention integrate with Prometheus or another metrics sink.

---

## Tips

- Include `request_id` in bug reports so you can grep precise logs across containers.
- Use `jq -r '.event'` to quickly profile which actions spam logs.
- Combine `/metrics` sampling with `watch` (`watch -n 5 curl ...`) for quick local SLO checks.

Structured logs and lightweight metrics make it easier to triage production incidents and prepare for future observability tooling.
