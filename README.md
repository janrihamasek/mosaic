# Mosaic

Mosaic is a small full-stack prototype for keeping track of daily activities and their qualitative scores. The project consists of a React front-end, a Flask API, and a SQLite database that stores activities and day-to-day entries.

## Features
- Activity catalogue with activation/deactivation, monthly goal targeting, and detail overview.
- Activity categories for thematic grouping and richer analytics down the road.
- Daily sheet (`Today` tab) for quick scoring of all active activities, including debounced auto-save.
- Entry history with sorting, pagination, and inline delete.
- CSV import helper (UI button + backend endpoint) for bootstrapping historical data.
- Optional API key protection with basic rate limiting on mutating endpoints.

### Activity Scoring
- Every activity captures a monthly goal (desired number of points/occurrences) and belongs to a broader category for trend analysis.
- Entries are scored 0–5 (0 = not performed, 1–5 = qualitative measure such as effort, quality, or repetitions).
- Tracking actual vs. target points per activity or category gives a quick percentage success metric for the month.

## Architecture
- **Frontend**: React 18 with Create React App, component-driven UI, shared inline style system in `frontend/src/styles/common.js`.
- **Backend**: Flask + SQLite, simple REST API served from `backend/app.py`.
- **Database**: SQLite schema in `database/schema.sql`, migrated via `database/init_db.py`.

## Getting Started

### Prerequisites
- Node.js 18+ and npm.
- Python 3.10+ with `pip`.

### 1. Prepare the database
```bash
cd database
python3 init_db.py
```
This script recreates `database/mosaic.db` from `schema.sql`. Optionally seed historical data:
```bash
cd ../backend
python3 import_data.py  # reads data_for_mosaic - january.csv
```

### 2. Run the backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
By default the API listens on `http://127.0.0.1:5000`.
Set `MOSAIC_DB_PATH` to point the Flask app at a different SQLite file (useful for tests/CI).
To secure the API, set `MOSAIC_API_KEY=<your-secret>` and include `X-API-Key` on requests. Rate limiting (configurable via `app.config["RATE_LIMITS"]`) guards mutating endpoints by default.

To run the backend test suite:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

### 3. Run the frontend
Configure the API origin via environment variable (Create React App reads `REACT_APP_*` at build time):
```bash
cd frontend
cp .env.example .env.local  # adjust the URL if needed
```
Then install dependencies and start the dev server:
```bash
cd frontend
npm install
npm start
```
If no environment variable is set, the app falls back to `http://127.0.0.1:5000` (and the same for tests).
Use the `Import CSV` button on the **Entries** tab to upload data through the `/import_csv` endpoint (expects headers `date,activity,value,note,description,category,goal`). Values are merged/upserted; activities are auto-created/updated with category + goal metadata.

## API Surface
| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/entries` | GET | List entries (most recent first) |
| `/add_entry` | POST | Upsert entry for given date/activity |
| `/entries/<id>` | DELETE | Remove entry |
| `/activities?all=true` | GET | List all activities (or only active) |
| `/add_activity` | POST | Create new activity |
| `/activities/<id>/(activate|deactivate)` | PATCH | Toggle activity |
| `/activities/<id>` | DELETE | Delete inactive activity |
| `/today?date=YYYY-MM-DD` | GET | Daily sheet of active activities |
| `/finalize_day` | POST | Ensure daily entries exist for active activities |
| `/import_csv` | POST | Accept CSV upload and batch import/update entries |

## Recommended Next Steps
1. Introduce error handling and loading states around network calls in the React components.
2. Cover the Flask API with unit tests (e.g., pytest + Flask test client) and add backend dependency tracking (`requirements.txt`).
3. Consider authentication/authorization if the app moves beyond personal use.
4. Prepare production-ready build/deployment docs (Dockerfile or hosting instructions).

## License
TBD – choose and document an open-source or proprietary license before publishing.
