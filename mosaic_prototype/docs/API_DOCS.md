# Mosaic API Documentation

This document describes the REST API endpoints for the **Mosaic** project, a full-stack application for tracking daily activities and their qualitative scores.

---

## Base URL
- Development backend: `http://localhost:5000`
- Production backend (Compose): `http://localhost:5001`

Set `REACT_APP_API_BASE_URL`/`REACT_APP_API_URL` (frontend) or `DATABASE_URL`/`POSTGRES_*` (backend) to target other environments.

---

## Authentication
- **JWT access token**: Obtain by calling `POST /login` (see [Authentication Endpoints](#authentication-endpoints)). Include it on subsequent requests as `Authorization: Bearer <token>`.
- **CSRF token**: Each login response also returns a `csrf_token`. Provide it as `X-CSRF-Token` on every mutating request (`POST`, `PUT`, `PATCH`, `DELETE`).
- **API Key** (optional): When `MOSAIC_API_KEY` is configured, include `X-API-Key` **together with** the JWT headers above.
- **Rate Limiting**: Mutating endpoints are rate-limited. See the [Rate Limits](#rate-limits) section for details.

---

## Rate Limits
| Endpoint               | Limit (requests) | Window (seconds) |
|------------------------|------------------|------------------|
| `/add_entry`           | 60               | 60               |
| `/add_activity`        | 30               | 60               |
| `/activities/*/activate` | 60            | 60               |
| `/activities/*/deactivate` | 60          | 60               |
| `/activities/*` (update) | 60            | 60               |
| `/activities/*` (delete) | 30            | 60               |
| `/entries/*` (delete)  | 90               | 60               |
| `/finalize_day`        | 10               | 60               |
| `/import_csv`          | 5                | 300              |
| `/login`               | 10               | 60               |
| `/register`            | 5                | 3600             |

---

## Endpoints

### **Home**
- **Endpoint**: `GET /`
- **Description**: Check if the backend is running.
- **Response**:
  ```json
  {
    "message": "Backend běží!",
    "database": "postgresql+psycopg2://mosaic:***@postgres:5432/mosaic_dev"
  }
  ```

---

### **Authentication**
#### **Register**
- **Endpoint**: `POST /register`
- **Description**: Create a new user account.
- **Request Body**:
  ```json
  {
    "username": "alice",
    "password": "changeMe123"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "message": "User registered"
  }
  ```
- **Notes**: Usernames must be unique, 3–80 characters, and without spaces. Passwords must be at least 8 characters.

#### **Login**
- **Endpoint**: `POST /login`
- **Description**: Exchange credentials for an access token.
- **Request Body**:
  ```json
  {
    "username": "alice",
    "password": "changeMe123"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "<JWT>",
    "csrf_token": "<csrf>",
    "token_type": "Bearer",
    "expires_in": 3600
  }
  ```
- **Usage**: Send `Authorization: Bearer <JWT>` on every request and `X-CSRF-Token: <csrf>` on every mutating request.

---

### **Entries**
#### **List Entries**
- **Endpoint**: `GET /entries`
- **Description**: Retrieve a list of activity entries, optionally filtered by date, activity, or category.
- **Query Parameters**:
  - `start_date` (optional, string): Start date in `YYYY-MM-DD` format.
  - `end_date` (optional, string): End date in `YYYY-MM-DD` format.
  - `activity` (optional, string): Filter by activity name.
  - `category` (optional, string): Filter by category name.
    - For `activity` and `category`, the special values `all`, `all activities`, or `all categories` (case‑insensitive) include everything.
  - `limit` (optional, int): Number of rows to return (default 100, max 500).
  - `offset` (optional, int): Number of rows to skip before returning results.
- **Response**:
  ```json
  [
    {
      "id": 1,
      "date": "2025-10-29",
      "activity": "Reading",
      "value": 5,
      "note": "Great session!",
      "category": "Learning",
      "goal": 30,
      "activity_description": "Read a book for 30 minutes."
    }
  ]
  ```
- **Notes**:
  - Results are ordered by `date` descending and then by `activity` name.
  - Fields `category` and `goal` are populated even if the originating activity has been deleted, thanks to the denormalised data stored in the `entries` table.

#### **Add/Update Entry**
- **Endpoint**: `POST /add_entry`
- **Description**: Add or update an activity entry for a specific date.
- **Request Body**:
  ```json
  {
    "date": "2025-10-29",
    "activity": "Reading",
    "value": 5,
    "note": "Great session!"
  }
  ```
- **Response**:
  - `201 Created`: Entry added.
  - `200 OK`: Entry updated.
  - `400 Bad Request`: Invalid payload.

#### **Delete Entry**
- **Endpoint**: `DELETE /entries/<int:entry_id>`
- **Description**: Delete an activity entry by ID.
- **Response**:
  - `200 OK`: Entry deleted.
  - `404 Not Found`: Entry not found.

---

### **Activities**
#### **List Activities**
- **Endpoint**: `GET /activities`
- **Description**: Retrieve a list of activities. Use `?all=true` to include inactive activities.
- **Query Parameters**:
  - `all` (optional, boolean): Include inactive activities if `true`.
  - `limit` (optional, int): Maximum number of records (default 100, max 500).
  - `offset` (optional, int): Number of records to skip.
- **Response**:
  ```json
  [
    {
      "id": 1,
      "name": "Reading",
      "category": "Learning",
      "goal": 30,
      "description": "Read a book for 30 minutes.",
      "active": 1,
      "frequency_per_day": 1,
      "frequency_per_week": 7,
      "deactivated_at": null
    }
  ]
  ```

#### **Add Activity**
- **Endpoint**: `POST /add_activity`
- **Description**: Add a new activity.
- **Request Body**:
  ```json
  {
    "name": "Reading",
    "category": "Learning",
    "description": "Read a book for 30 minutes.",
    "frequency_per_day": 1,
    "frequency_per_week": 7
  }
  ```
- **Notes**:
  - The backend computes the average goal per day as `(frequency_per_day * frequency_per_week) / 7` and stores that value in the `goal` column.
  - If a client already calculates that value, it may send it as `goal`; otherwise the backend will derive it.
- **Response**:
  - `201 Created`: Activity added.
  - `409 Conflict`: Activity with this name already exists.

#### **Update Activity**
- **Endpoint**: `PUT /activities/<int:activity_id>`
- **Description**: Update an existing activity.
- **Request Body**:
  ```json
  {
    "category": "Education",
    "goal": 45,
    "description": "Read a book for 45 minutes.",
    "frequency_per_day": 1,
    "frequency_per_week": 7
  }
  ```
- **Notes**:
  - If you change `frequency_per_day`, you must also supply `frequency_per_week` (and vice versa) so the backend can recalculate the derived goal.
  - When the activity is updated, all historic entries for the same activity receive the new category, goal, and description values.
- **Response**:
  - `200 OK`: Activity updated.
  - `404 Not Found`: Activity not found.

#### **Activate/Deactivate Activity**
- **Endpoint**: `PATCH /activities/<int:activity_id>/activate`
- **Description**: Activate an activity.
- **Response**:
  - `200 OK`: Activity activated.
  - `404 Not Found`: Activity not found.

- **Endpoint**: `PATCH /activities/<int:activity_id>/deactivate`
- **Description**: Deactivate an activity.
- **Response**:
  - `200 OK`: Activity deactivated.
  - `404 Not Found`: Activity not found.

#### **Delete Activity**
- **Endpoint**: `DELETE /activities/<int:activity_id>`
- **Description**: Delete an **inactive** activity by ID.
- **Response**:
  - `200 OK`: Activity deleted.
  - `400 Bad Request`: Activity is active (deactivate first).
  - `404 Not Found`: Activity not found.

---

### **Today's Activities**
- **Endpoint**: `GET /today`
- **Description**: Retrieve all active activities for a specific date (defaults to today).
- **Query Parameters**:
  - `date` (optional, string): Date in `YYYY-MM-DD` format.
  - `limit` (optional, int): Number of activities to return (default 200, max 500).
  - `offset` (optional, int): Number of activities to skip before returning results.
- **Response**:
  ```json
  [
    {
      "activity_id": 1,
      "name": "Reading",
      "category": "Learning",
      "description": "Read a book for 30 minutes.",
      "active": 1,
      "deactivated_at": null,
      "goal": 30,
      "entry_id": 1,
      "value": 5,
      "note": "Great session!",
      "activity_goal": 30
    }
  ]
  ```
- **Notes**:
  - If `date` is omitted, the endpoint uses today’s date.
  - Activities deactivated after the selected date are still included.
  - The response is cached for roughly one minute to improve responsiveness; writes automatically invalidate the cache.

---

### **Finalize Day**
- **Endpoint**: `POST /finalize_day`
- **Description**: Ensure all active activities have an entry for the specified date.
- **Request Body**:
  ```json
  {
    "date": "2025-10-29"
  }
  ```
- **Notes**:
  - Omitting the `date` field finalizes the current day (in the server’s timezone).
- **Response**:
  ```json
  {
    "message": "X missing entries added for YYYY-MM-DD"
  }
  ```

---

### **Progress Stats (Dashboard Snapshot)**
- **Endpoint**: `GET /stats/progress`
- **Description**: Returns a consolidated snapshot of key metrics used by the dashboard. Values are calculated over the trailing 30 days ending on the requested date (inclusive).
- **Query Parameters**:
  - `date` (optional, string): Anchor date in `YYYY-MM-DD` format. Defaults to the current server date.
- **Response**:
  ```json
  {
    "goal_completion_today": 86.0,
    "streak_length": 5,
    "activity_distribution": [
      {"category": "Health", "count": 12, "percent": 30.0},
      {"category": "Work", "count": 8, "percent": 20.0}
    ],
    "avg_goal_fulfillment": {
      "last_7_days": 92.1,
      "last_30_days": 84.7
    },
    "avg_goal_fulfillment_by_category": [
      {"category": "Health", "last_7_days": 95.4, "last_30_days": 88.0},
      {"category": "Work", "last_7_days": 88.3, "last_30_days": 75.0}
    ],
    "active_days_ratio": {
      "active_days": 21,
      "total_days": 30,
      "percent": 70.0
    },
    "positive_vs_negative": {
      "positive": 52,
      "negative": 8,
      "ratio": 6.5
    },
    "top_consistent_activities_by_category": [
      {
        "category": "Health",
        "activities": [
          {"name": "Walking", "consistency_percent": 98.0},
          {"name": "Stretching", "consistency_percent": 76.7}
        ]
      },
      {
        "category": "Work",
        "activities": [
          {"name": "Deep work", "consistency_percent": 83.3},
          {"name": "Reading", "consistency_percent": 70.0}
        ]
      }
    ]
  }
  ```
- **Notes**:
  - Percentages are rounded to one decimal place.
  - Daily goal completion is computed against the sum of `avg_goal_per_day` for all currently active activities (capped at 100%).
  - `streak_length` counts consecutive days starting from the day before `date` where the overall ratio stays at or above 0.5.
  - Category averages exclude the current day; global averages still include it.
  - `positive_vs_negative` splits entries into `value > 0` (positive) and `value = 0` (negative), with the ratio dividing by at least one via `max(negative, 1)`.
  - Results are cached per-date for five minutes and invalidated automatically after any entry or activity mutation.

---

### **Backups**
#### **Status**
- **Endpoint**: `GET /backup/status`
- **Description**: Returns current backup settings and latest run metadata.
- **Response** (`200 OK`):
  ```json
  {
    "enabled": true,
    "interval_minutes": 60,
    "last_run": "2025-11-02T21:40:40.154123+00:00",
    "available_backups": [
      {
        "filename": "backup_2025-11-02T214040.zip",
        "created_at": "2025-11-02T21:40:40.154123+00:00",
        "size_bytes": 51234
      }
    ]
  }
  ```

#### **Run Backup**
- **Endpoint**: `POST /backup/run`
- **Description**: Trigger a manual backup run. Returns metadata for the generated archive.
- **Response** (`200 OK`):
  ```json
  {
    "message": "Backup completed",
    "backup": {
      "filename": "backup_2025-11-02T221000.zip",
      "created_at": "2025-11-02T22:10:00.512431+00:00",
      "size_bytes": 54321
    }
  }
  ```

#### **Toggle Automatic Backups**
- **Endpoint**: `POST /backup/toggle`
- **Description**: Enable/disable scheduled backups and/or update the interval.
- **Request Body**:
  ```json
  {
    "enabled": true,
    "interval_minutes": 90
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message": "Backup settings updated",
    "status": {
      "enabled": true,
      "interval_minutes": 90,
      "last_run": "2025-11-02T21:40:40.154123+00:00"
    }
  }
  ```
- **Validation**:
  - `enabled` must be a boolean (optional).
  - `interval_minutes` must be an integer ≥ 5 (optional).

#### **Download Backup**
- **Endpoint**: `GET /backup/download/<filename>`
- **Description**: Download a previously generated backup archive (ZIP).
- **Response**:
  - `200 OK`: Returns binary ZIP content with a `Content-Disposition` attachment header.
  - `400 Bad Request`: Invalid filename.
  - `404 Not Found`: Backup not found.

---

### **Data Export**
#### **JSON Export**
- **Endpoint**: `GET /export/json`
- **Description**: Returns activities and entries in a single JSON payload.
- **Query Parameters**: Supports `limit` and `offset` (defaults: 500, max limit: 2000).
- **Response** (`200 OK`):
  ```json
  {
    "entries": [...],
    "activities": [...],
    "meta": {
      "entries": {"limit": 500, "offset": 0, "total": 1234},
      "activities": {"limit": 500, "offset": 0, "total": 42}
    }
  }
  ```
- **Notes**: Response uses `application/json` with `Content-Disposition: attachment`.

#### **CSV Export**
- **Endpoint**: `GET /export/csv`
- **Description**: Streams a CSV file with two datasets: entries and activities.
- **Query Parameters**: Same pagination options as the JSON export.
- **Response**:
  - `200 OK`: `text/csv` attachment. CSV contains a header row per dataset and blank line separators.

---

### **CSV Import**
- **Endpoint**: `POST /import_csv`
- **Description**: Import activity entries from a CSV file.
- **Request**: Multipart form with a `file` field containing the CSV.
- **Response**:
  ```json
  {
    "message": "CSV import completed",
    "summary": {
      "created": 5,
      "updated": 2,
      "skipped": 0
    }
  }
  ```
- **Notes**:
  - The CSV must contain headers compatible with the import utility (`date,activity,value,note,description,category,goal`).
  - The derived goal per day is recalculated for each imported activity in the same way as for the REST endpoints.

---

## Input Validation
- All payloads are validated with **Pydantic 2** models defined in `backend/schemas.py`. Pydantic was chosen because it offers declarative schemas, high-performance parsing, and clean integration with type hints already used in the project.
- Every endpoint with a JSON or file payload delegates to the helpers in `backend/security.py`, which wrap the Pydantic models and convert validation issues into the standard error response: `{"error": {"code": "...", "message": "...", "details": {...}}}` with HTTP 400.
- Existing schemas:
  | Endpoint / Use case | Helper | Schema |
  |---------------------|--------|--------|
  | `POST /add_entry` | `validate_entry_payload` | `EntryPayload` |
  | `POST /add_activity` | `validate_activity_create_payload` | `ActivityCreatePayload` |
  | `PUT /activities/<id>` | `validate_activity_update_payload` | `ActivityUpdatePayload` |
  | `POST /finalize_day` | `validate_finalize_day_payload` | `FinalizeDayPayload` |
  | `POST /import_csv` | `validate_csv_import_payload` | `CSVImportPayload` |
  | `POST /register` | `validate_register_payload` | `RegisterPayload` |
  | `POST /login` | `validate_login_payload` | `LoginPayload` |
- Adding a new payload:
  1. Define a Pydantic model in `backend/schemas.py` with explicit field types, defaults, and `field_validator`/`model_validator` hooks for custom business rules.
  2. Expose a thin wrapper in `backend/security.py` that calls `.model_validate()` and raises `ValidationError` with the schema’s message.
  3. Use that wrapper inside the Flask endpoint. The shared error handler will take care of returning the JSON error response.
- Validation errors always contain actionable, single-sentence messages so they can be shown directly in the UI or CLI clients.

---

- **Error payload format**: Every error response returns `{"error": {"code": "string", "message": "string", "details": {}}}`. The `details` object is optional and omitted if empty.
- **400 Bad Request** (`code: invalid_input` or `invalid_query`): Invalid payload or parameters.
- **401 Unauthorized** (`code: unauthorized` or `invalid_credentials`): Missing/invalid token or wrong credentials.
- **403 Forbidden** (`code: invalid_csrf`): CSRF token missing or mismatched.
- **404 Not Found** (`code: not_found`): Resource not found.
- **409 Conflict** (`code: conflict`): Resource already exists.
- **429 Too Many Requests** (`code: too_many_requests`): Rate limit exceeded.
- **500 Internal Server Error** (`code: internal_error`): Server error.
- **Token expiry**: When the JWT expires the API responds with `401`/`token_expired`.

---

## Database Indexes
- `idx_entries_date`: created on `entries(date)` because `/entries`, `/today`, and `/stats/progress` aggregate by date ranges.
- `idx_entries_activity`: supports lookups by activity in `/entries`, `/today`, and streak/consistency calculations for `/stats/progress`.
- `idx_entries_activity_category`: speeds category filters in `/entries` and the distribution slice of `/stats/progress`.
- `idx_activities_category`: optimises category-based ordering and filtering in `/activities` and for active-goal lookups in `/stats/progress`.
- All indexes were validated with `EXPLAIN QUERY PLAN` to ensure the SQLite planner uses them for the slowest queries.

---
