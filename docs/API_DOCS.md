# Mosaic API Documentation

Comprehensive reference for the Mosaic backend REST API. The service powers the activity-tracking dashboard, the admin surface, and NightMotion tooling.

---

## Base URL
- Development: `http://localhost:5000`
- Docker/Compose production: `http://localhost:5001`

Configure `REACT_APP_API_URL` (frontend) or `DATABASE_URL`/`POSTGRES_*` (backend) to target other environments. All URLs in this document are relative to the backend base.

---

## Authentication & Security
- **JWT access token**: Call `POST /login` to obtain a token. Send `Authorization: Bearer <token>` on every request.
- **CSRF token**: `POST /login` also returns `csrf_token`. Include `X-CSRF-Token: <csrf>` on mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- **API Key (optional)**: When `MOSAIC_API_KEY` is set, include `X-API-Key` on all non-public endpoints in addition to JWT+CSRF headers.
- **Tenant scoping**: Every data endpoint automatically scopes rows to the authenticated `user_id`. Admins (`is_admin = true`) can see all data but still inherit rate limits.
- **Rate limits**: In-memory per-user/IP throttling protects sensitive endpoints (see below).

### Rate Limits
| Endpoint | Limit | Window (s) |
| --- | --- | --- |
| `/add_entry` | 60 | 60 |
| `/add_activity` | 30 | 60 |
| `/activities/<id>/activate` | 60 | 60 |
| `/activities/<id>/deactivate` | 60 | 60 |
| `/activities/<id>` (PUT) | 60 | 60 |
| `/activities/<id>` (DELETE) | 30 | 60 |
| `/entries/<id>` (DELETE) | 90 | 60 |
| `/finalize_day` | 10 | 60 |
| `/import_csv` | 5 | 300 |
| `/login` | 10 | 60 |
| `/register` | 5 | 3600 |
| `/api/stream-proxy` | 2 | 60 |

---

## Endpoints

### Home
- **`GET /`** — Health probe that returns:
  ```json
  {
    "message": "Backend běží!",
    "database": "postgresql+psycopg2://mosaic:***@postgres:5432/mosaic_dev"
  }
  ```

### Authentication
#### Register — `POST /register`
```json
{
  "username": "alice",
  "password": "changeMe123",
  "display_name": "Alice"
}
```
- `username`: 3–80 chars, no spaces.
- `password`: ≥ 8 chars.
- `display_name`: optional, trimmed, ≤ 120 chars.
- **Response** `201 Created` → `{ "message": "User registered" }`

#### Login — `POST /login`
```json
{
  "username": "alice",
  "password": "changeMe123"
}
```
- **Response** `200 OK`:
  ```json
  {
    "access_token": "<JWT>",
    "csrf_token": "<csrf>",
    "token_type": "Bearer",
    "expires_in": 3600,
    "display_name": "Alice",
    "is_admin": false
  }
  ```

### Current User Profile
| Endpoint | Description |
| --- | --- |
| **`GET /user`** | Returns the authenticated user (id, username, display_name, is_admin, created_at). |
| **`PATCH /user`** | Update `display_name` and/or `password`. Example body: `{ "display_name": "Ops", "password": "NewPass123" }`. Absent fields remain unchanged. |
| **`DELETE /user`** | Permanently deletes the signed-in account along with owned activities/entries; caches are invalidated. |

### Admin User Management *(requires `is_admin`)*
| Endpoint | Description |
| --- | --- |
| **`GET /users`** | Lists every user ordered by username. Useful for audits and the Admin tab’s people list. |
| **`DELETE /users/<id>`** | Deletes a specific account. Safeguard prevents admins from deleting themselves. |

---

### Activities
- **List** — `GET /activities?all=true|false&limit=&offset=`
  - Returns active activities (or all when `all=true`). Response includes id, name, category, goal, description, cadence, activation state.
- **Create** — `POST /add_activity`
  ```json
  {
    "name": "Reading",
    "category": "Learning",
    "description": "Read 30 minutes",
    "frequency_per_day": 1,
    "frequency_per_week": 7,
    "activity_type": "positive"
  }
  ```
  Backend derives `goal = (frequency_per_day * frequency_per_week) / 7` (unless `activity_type = "negative"`, in which case the goal is always stored as `0`). Activities default to `positive` when the field is omitted.
- **Update** — `PUT /activities/<id>` accepts the same shape as create. When toggling cadence, include both `frequency_per_day` and `frequency_per_week` so the server can recompute goals.
- **Activate / Deactivate** — `PATCH /activities/<id>/activate` or `/deactivate` flips state. Both endpoints invalidate `/today` + `/stats` caches.
- **Delete** — `DELETE /activities/<id>` removes an inactive activity.

### Entries
- **List** — `GET /entries`
  - Query params: `start_date`, `end_date` (`YYYY-MM-DD`), `activity`, `category`, `limit`, `offset`.
  - Special filter values (`all`, `all activities`, `all categories`) remove that filter.
  - Non-admins only see their own entries; admins see all data.
  - Response example:
    ```json
    [
      {
        "id": 1,
        "date": "2025-11-03",
        "activity": "Reading",
        "value": 0.8,
        "note": "Evening session",
        "category": "Learning",
        "goal": 1.0,
        "activity_description": "Read 30 minutes",
        "activity_type": "positive"
      }
    ]
    ```
- **Upsert** — `POST /add_entry`
  ```json
  {
    "date": "2025-11-03",
    "activity": "Reading",
    "value": 0.8,
    "note": "Evening session"
  }
  ```
  - If `(date, activity)` already exists it is updated; otherwise inserted.
  - Response `201 Created` (new) or `200 OK` (updated). Validation errors return `400`.
- **Delete** — `DELETE /entries/<id>` removes an entry. Admins may delete any record; users can only delete their own.

### Today
- **`GET /today`** — Returns the per-activity grid for a selected date (default today).
  - Query: `date`, `limit` (default 200), `offset`.
  - Returns `activity` metadata plus the day’s entry (`value`, `note`, `activity_goal`, `activity_type`). Cached for ~60s. Client surfaces the `activity_type` to tint “negative” activities red and “positive” activities green when they have logged value.

### Finalize Day
- **`POST /finalize_day`**
  ```json
  { "date": "2025-11-03" }
  ```
  Adds missing entries with value `0` for every active activity on the given day. Omitting `date` finalizes the current day.

### Progress Stats (Dashboard Snapshot)
- **`GET /stats/progress`** — Optional `date=YYYY-MM-DD` (defaults to server today).
- Response mirrors the UI widget model:
  ```json
  {
    "goal_completion_today": 82.5,
    "streak_length": 4,
    "activity_distribution": [{"category":"Health","count":12,"percent":36.4}],
    "avg_goal_fulfillment": {"last_7_days": 75.1, "last_30_days": 63.4},
    "avg_goal_fulfillment_by_category": [
      {"category":"Health","last_7_days":80.0,"last_30_days":65.3}
    ],
    "active_days_ratio": {"active_days": 18, "total_days": 30, "percent": 60.0},
    "positive_vs_negative": {"positive": 52, "negative": 6, "ratio": 8.7},
    "top_consistent_activities_by_category": [
      {
        "category": "Health",
        "activities": [
          {"name": "Walking", "consistency_percent": 96.7}
        ]
      }
    ]
  }
  ```
- Calculations follow `docs/METRICS.md` (category ratios `R₍d,c₎`, active-day threshold 0.5, seven/thirty-day averages excluding the current day for category breakdowns). Cached for ~5 minutes per user/date.
  - Negative activities are ignored across every metric (goal sums, per-category splits, “positive vs negative” counts, streak tracking).

### Backups
| Endpoint | Description |
| --- | --- |
| **`GET /backup/status`** | Returns scheduler state: `{ "enabled": true, "interval_minutes": 60, "last_run": "2025-11-02T21:40:40Z", "backups": [{"filename": "backup-20251102-214040.zip", "size_bytes": 53248, "created_at": "2025-11-02T21:40:40Z"}] }`. |
| **`POST /backup/run`** | Triggers an on-demand ZIP. Response: `{ "message": "Backup completed", "backup": { "timestamp": "20251103-071200", "zip": "backup-20251103-071200.zip", "json": "backup-20251103-071200.json", "csv": "backup-20251103-071200.csv", "generated_at": "2025-11-03T07:12:05Z" } }`. |
| **`POST /backup/toggle`** | Enables/disables automation and/or updates `interval_minutes` (min 5). Body `{ "enabled": true, "interval_minutes": 90 }`. Response includes updated `status`. |
| **`GET /backup/download/<filename>`** | Streams a ZIP archive (`Content-Disposition: attachment`). Rejects invalid filenames and missing files. |

### Data Export & Import
- **`GET /export/json`** — Returns `{ "entries": [...], "activities": [...], "meta": { ... } }` with pagination (`limit` default 500, max 2000).
- **`GET /export/csv`** — Streams a CSV attachment covering activities and entries.
- **`POST /import_csv`** — Multipart upload (`file=@entries.csv`). Response summarises `{ "created": 5, "updated": 2, "skipped": 0 }`. CSV must include headers `date,activity,value,note,description,category,goal`.

### Wearable Ingestion
- **`POST /ingest/wearable/batch`**
  ```json
  {
    "source_app": "Fitbit",
    "device_id": "FA-123",
    "tz": "Europe/Prague",
    "records": [
      {
        "type": "steps",
        "start": "2025-11-02T06:00:00+01:00",
        "end": "2025-11-02T06:15:00+01:00",
        "fields": { "steps": 880, "distance_m": 650 }
      }
    ]
  }
  ```
  - Validates payload via `validate_wearable_batch_payload`.
  - Deduplicates via `dedupe_key`, persists to `wearable_raw`, and kicks off ETL (`process_wearable_raw_by_dedupe_keys`) to normalize into canonical tables.
  - Response contains `{ "accepted": N, "duplicates": M, "errors": [], "etl": { ... } }`.

### NightMotion Stream Proxy
- **`GET /api/stream-proxy`** — Proxies MJPEG/RTSP streams through the backend so the browser never sees camera credentials.
  - Query params: `url=rtsp://host/stream`, `username`, `password`.
  - Requires JWT + API key (if enabled). Rate limited (`2/min`).
  - Response is `multipart/x-mixed-replace` MJPEG. Errors: `401` (invalid camera creds), `500` (FFmpeg failure), `400` (invalid URL).

### Logs & Observability
| Endpoint | Description |
| --- | --- |
| **`GET /logs/activity`** | Admin-only. Query params: `limit` (1–500, default 100), `offset`, `user_id`, `event_type`, `level`, `start`, `end` (ISO timestamps). Returns `{ items: [...], total, limit, offset }`. Errors when the `activity_logs` table is missing return `503 logs_unavailable`. |
| **`GET /logs/runtime`** | Admin-only. Optional `limit`. Returns live in-memory Structlog events captured by the runtime log handler. |
| **`GET /metrics`** | Public endpoint. `?format=json` returns structured counters (requests per endpoint, latency, errors, uptime). No query param returns Prometheus text format. |
| **`GET /healthz`** | Public health check summarising uptime, DB connectivity, cache state, error rate, and req/min. Returns `503` if DB or cache probes fail. |

---

All endpoints above share the same error contract: failures return
```json
{
  "error": {
    "code": "invalid_query",
    "message": "Human-friendly message",
    "details": { ... }
  }
}
```
Refer to `docs/LOGGING.md` and `docs/METRICS.md` for field-level audit and telemetry semantics.

### Health & Metrics
| Endpoint | Description |
| --- | --- |
| **`GET /healthz`** | Returns system health snapshot used by the Admin → Health panel. Example: `{ "uptime_s": 86400.0, "db_ok": true, "cache_ok": true, "req_per_min": 3.2, "error_rate": 0.001, "last_metrics_update": "2025-11-03T07:42:11Z" }`. HTTP 200 when healthy, 503 otherwise. |
| **`GET /metrics`** | Prometheus-compatible text by default; pass `?format=json` for the JSON representation. JSON payload:
  ```json
  {
    "requests_total": 1523,
    "total_latency_ms": 74230.11,
    "avg_latency_ms": 48.77,
    "errors_total": {"4xx": 12, "5xx": 2},
    "status_counts": {"200": 1475, "401": 18, "500": 2},
    "endpoints": [
      {
        "method": "GET",
        "endpoint": "today",
        "count": 320,
        "avg_latency_ms": 15.42,
        "total_latency_ms": 4934.4,
        "errors_4xx": 0,
        "errors_5xx": 0,
        "status_counts": {"200": 320}
      }
    ],
    "last_updated": "2025-11-03T07:42:11Z"
  }
  ```
  Text output exports the same counters using `mosaic_*` Prometheus metrics.

### NightMotion Stream Proxy
- **`GET /api/stream-proxy`** — MJPEG proxy for camera feeds.
  - Query params: `url` (RTSP URL, required), `username`, `password` (optional; injected into URL when provided).
  - Requires a valid Mosaic session (JWT + CSRF + API key if configured) and is rate-limited to 2 requests/minute per user/IP.
  - Response: `multipart/x-mixed-replace; boundary=frame` suitable for `<img>`/`<video>` tags. Errors return JSON envelopes with friendly messages.

---

## Validation & Error Envelope
- Payloads rely on **Pydantic 2** models (`backend/schemas.py`). Validation helpers in `backend/security.py` convert failures into a shared format.
- Error responses always follow:
  ```json
  {
    "error": {
      "code": "invalid_input",
      "message": "Human readable text",
      "details": {}
    }
  }
  ```
- Common codes: `invalid_input`, `invalid_query`, `invalid_credentials`, `token_expired`, `forbidden`, `not_found`, `conflict`, `too_many_requests`, `internal_error`.

---

## Database Index Reference
- `entries(date)`, `entries(activity)`, `entries(activity_category)` — support `/entries`, `/today`, and `/stats` queries.
- `activities(category)` — accelerates `/activities` and baseline lookups for `/stats/progress`.
- Foreign keys on `activities.user_id` and `entries.user_id` enforce tenant isolation with cascading deletes.

---

Additional references: `docs/LOGGING.md` (structured logging + `/metrics` workflow) and `docs/METRICS.md` (analytics formulas shared by backend/frontend).
