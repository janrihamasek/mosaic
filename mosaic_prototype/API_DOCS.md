# Mosaic API Documentation

This document describes the REST API endpoints for the **Mosaic** project, a full-stack application for tracking daily activities and their qualitative scores.

---

## Base URL
`http://127.0.0.1:5000`

---

## Authentication
- **API Key**: Some endpoints require an API key to be sent in the `X-API-Key` header.
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

---

## Endpoints

### **Home**
- **Endpoint**: `GET /`
- **Description**: Check if the backend is running.
- **Response**:
  ```json
  {
    "message": "Backend běží!",
    "database": "path/to/database/mosaic.db"
  }
  ```

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

### **Progress Stats**
- **Endpoint**: `GET /stats/progress`
- **Description**: Retrieve progress statistics for activities or categories over a specified period.
- **Query Parameters**:
  - `group` (optional, string): Group by `activity` or `category` (default: `activity`).
  - `period` (optional, int): Number of days (30 or 90, default: 30).
  - `date` (optional, string): End date in `YYYY-MM-DD` format (defaults to today).
- **Response**:
  ```json
  {
    "group": "activity",
    "window": 30,
    "start_date": "2025-09-30",
    "end_date": "2025-10-29",
    "data": [
      {
        "name": "Reading",
        "category": "Learning",
        "goal_per_day": 1,
        "total_value": 25,
        "total_goal": 30,
        "progress": 0.83
      }
    ]
  }
  ```
- **Notes**:
  - The `data` array is sorted by `progress` in descending order.
  - `progress` is expressed as a float in the range 0–1. Multiply by 100 for a percentage.

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
- Every endpoint with a JSON or file payload delegates to the helpers in `backend/security.py`, which wrap the Pydantic models and convert validation issues into the standard error response: `{"error": "message"}` with HTTP 400.
- Existing schemas:
  | Endpoint / Use case | Helper | Schema |
  |---------------------|--------|--------|
  | `POST /add_entry` | `validate_entry_payload` | `EntryPayload` |
  | `POST /add_activity` | `validate_activity_create_payload` | `ActivityCreatePayload` |
  | `PUT /activities/<id>` | `validate_activity_update_payload` | `ActivityUpdatePayload` |
  | `POST /finalize_day` | `validate_finalize_day_payload` | `FinalizeDayPayload` |
  | `POST /import_csv` | `validate_csv_import_payload` | `CSVImportPayload` |
- Adding a new payload:
  1. Define a Pydantic model in `backend/schemas.py` with explicit field types, defaults, and `field_validator`/`model_validator` hooks for custom business rules.
  2. Expose a thin wrapper in `backend/security.py` that calls `.model_validate()` and raises `ValidationError` with the schema’s message.
  3. Use that wrapper inside the Flask endpoint. The shared error handler will take care of returning the JSON error response.
- Validation errors always contain actionable, single-sentence messages so they can be shown directly in the UI or CLI clients.

---

## Error Responses
- **400 Bad Request**: Invalid payload or parameters.
- **401 Unauthorized**: Missing or invalid API key.
- **404 Not Found**: Resource not found.
- **409 Conflict**: Resource already exists.
- **500 Internal Server Error**: Server error.

---
