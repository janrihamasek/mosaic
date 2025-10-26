# Mosaic

Mosaic is a small full-stack prototype for keeping track of daily activities and their qualitative scores. The project consists of a React front-end, a Flask API, and a SQLite database that stores activities and day-to-day entries.

## Features
- Activity catalogue with activation/deactivation and detail overview.
- Daily sheet (`Today` tab) for quick scoring of all active activities, including debounced auto-save.
- Entry history with sorting, pagination, and inline delete.
- CSV import helper for bootstrapping historical data.

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

## Recommended Next Steps
1. Introduce error handling and loading states around network calls in the React components.
2. Cover the Flask API with unit tests (e.g., pytest + Flask test client) and add backend dependency tracking (`requirements.txt`).
3. Consider authentication/authorization if the app moves beyond personal use.
4. Prepare production-ready build/deployment docs (Dockerfile or hosting instructions).

## License
TBD – choose and document an open-source or proprietary license before publishing.
