# Mosaic

Mosaic is a small full-stack prototype for keeping track of daily activities and their qualitative scores. The project consists of a React front-end, a Flask API, and a PostgreSQL database that stores activities and day-to-day entries.

## Features
- Activity catalogue with activation/deactivation, monthly goal targeting, and detail overview.
- Activity categories for thematic grouping and richer analytics down the road.
- Daily sheet (`Today` tab) for quick scoring of all active activities, including debounced auto-save.
- Entry history with sorting, pagination, and inline delete.
- CSV import helper (UI button + backend endpoint) for bootstrapping historical data.
- JSON/CSV export endpoints for offline analysis with pagination controls.
- Backup manager with manual runs, scheduled automation, and downloadable archives.
- Optional API key protection with basic rate limiting on mutating endpoints.
- Response caching for frequently accessed reads (`/today`, `/stats/progress`) with short time-to-live to reduce database load.

### Activity Scoring
- Every activity captures a monthly goal (desired number of points/occurrences) and belongs to a broader category for trend analysis.
- Entries are scored 0–5 (0 = not performed, 1–5 = qualitative measure such as effort, quality, or repetitions).
- Tracking actual vs. target points per activity or category gives a quick percentage success metric for the month.

## Architecture
- **Frontend**: React 18 with Create React App, component-driven UI, shared inline style system in `frontend/src/styles/common.js`.
- **Backend**: Flask + PostgreSQL with Pydantic validation, standardized error responses, and explicit transactions in `backend/app.py`.
- **Database**: PostgreSQL schema managed by Flask-Migrate (`backend/manage.py`) with generated revisions in `backend/migrations/`.
- **DevOps**: Docker Compose stack (`Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`) running dev and prod backends side by side against a shared PostgreSQL 15 container with persistent volumes.

## Getting Started

### Quick start (Docker Compose)
1. Install Docker Engine (24+) and Docker Compose v2.
2. Review `.env.dev` and `.env.prod` in the repo root. Update secrets (API key, JWT secret, Postgres credentials) before first run.
3. Start the stack (dev + prod backends, frontend, postgres):
   ```bash
   docker compose up -d
   ```
4. Apply database migrations inside each backend container:
   ```bash
   docker compose exec mosaic_backend_dev flask db upgrade
   docker compose exec mosaic_backend_prod flask db upgrade
   ```
5. Access the services:
   - Frontend (serving the dev backend by default): http://localhost:3000
   - Dev API: http://localhost:5000
   - Prod API: http://localhost:5001
   - PostgreSQL (for GUI clients like DBeaver): host `localhost`, port `5433`, user `mosaic`, password `mosaic_password`, DB `mosaic_dev` or `mosaic_prod`.
6. To point the frontend at the prod API, rebuild with prod args:
   ```bash
   FRONTEND_API_URL=http://localhost:5001 \
   FRONTEND_API_KEY=prod-api-key \
   FRONTEND_BACKEND_LABEL="Production API" \
   docker compose up -d --build mosaic_frontend
   ```
   Switching back to dev just swaps the environment values.
7. Stop the stack with `docker compose down`. Add `-v` if you want to discard the Postgres volume.

### Manual setup (Python + Node)

#### Prerequisites
- Node.js 18+ and npm.
- Python 3.10+ with `pip`.
- PostgreSQL 13+ (local installation or container).

#### 1. Configure PostgreSQL
1. Ensure a PostgreSQL 13+ server is running locally (or expose one via Docker Compose/cloud).
2. Create a dedicated database and user (example):
   ```bash
   createuser --interactive --pwprompt mosaic
   createdb -O mosaic mosaic
   ```
3. Copy the backend environment template and adjust credentials as needed:
   ```bash
   cd mosaic_prototype/backend
   cp .env.example .env
  ```
  Configure at least `DATABASE_URL` (or the individual `POSTGRES_*` variables) along with `MOSAIC_API_KEY` and `MOSAIC_JWT_SECRET`. The backend otherwise falls back to
  `postgresql+psycopg2://postgres:postgres@localhost:5432/mosaic` for local development.

With the virtual environment activated (see the next section), run the initial migration to create tables:
```bash
python -m flask db upgrade
```
You can also seed historical data from CSV once the schema exists:
```bash
python import_data.py path/to/activities.csv
```

#### Database migrations
The backend ships with Flask-Migrate helpers in `backend/manage.py`:

```bash
cd backend
python3 manage.py migrate -m "describe change"  # autogenerate revision
python3 manage.py upgrade                      # apply to the current database
```

Generated scripts live under `backend/migrations/versions`.

#### 2. Run the backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
By default the API listens on `http://127.0.0.1:5000`.
Environment variables are loaded from `.env`; override `DATABASE_URL` to point at another PostgreSQL instance when needed.
To secure the API, set `MOSAIC_API_KEY=<your-secret>` and include `X-API-Key` on requests. Rate limiting (configurable via `app.config["RATE_LIMITS"]`) guards mutating endpoints by default.

#### Authentication workflow
- Create a user: `POST /register` with `{"username": "alice", "password": "changeMe123"}`.
- Log in: `POST /login` with the same credentials. The response includes `access_token`, `csrf_token`, `token_type`, and `expires_in`.
- Authorise every subsequent request by sending `Authorization: Bearer <access_token>`.
- For mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) also send `X-CSRF-Token: <csrf_token>` alongside the bearer token.
- Configure the signing secret via `MOSAIC_JWT_SECRET` (fallback value is for development only). Token lifetime defaults to 60 minutes and can be overridden with `MOSAIC_JWT_EXP_MINUTES`.
- Pagination: list endpoints (`/entries`, `/activities`, `/stats/progress`, `/today`) accept optional `limit`/`offset` query params (defaults: limit=100, offset=0).
- Database indexes: frequently filtered columns (`entries.date`, `entries.activity`, `entries.activity_category`, `activities.category`) now have dedicated indexes verified via `EXPLAIN QUERY PLAN` to keep lookups fast.

To run the backend test suite:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

CI/CD: On every push or pull request the GitHub Actions workflow (`.github/workflows/tests.yml`) installs dependencies and runs the backend pytest suite plus a frontend build to catch regressions early.

#### 3. Run the frontend
Configure the API origin via environment variable (Create React App reads `REACT_APP_*` at build time):
```bash
cd frontend
cat <<'EOF' > .env.local
REACT_APP_API_URL=http://127.0.0.1:5000
REACT_APP_API_KEY=
EOF
```
Adjust values as needed (Create React App reads `REACT_APP_*` variables at build time).
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
| `/register` | POST | Create a user account |
| `/login` | POST | Exchange credentials for JWT + CSRF tokens |
| `/entries` | GET | List entries (most recent first) |
| `/add_entry` | POST | Upsert entry for given date/activity |
| `/entries/<id>` | DELETE | Remove entry |
| `/activities?all=true` | GET | List all activities (or only active) |
| `/add_activity` | POST | Create new activity |
| `/activities/<id>` | PUT | Update activity metadata/goals |
| `/activities/<id>/(activate|deactivate)` | PATCH | Toggle activity |
| `/activities/<id>` | DELETE | Delete inactive activity |
| `/today?date=YYYY-MM-DD` | GET | Daily sheet of active activities |
| `/finalize_day` | POST | Ensure daily entries exist for active activities |
| `/stats/progress` | GET | Return dashboard analytics snapshot |
| `/import_csv` | POST | Accept CSV upload and batch import/update entries |
| `/export/json` | GET | Download activities + entries as JSON |
| `/export/csv` | GET | Download activities + entries as CSV |
| `/backup/status` | GET | Inspect backup settings and history |
| `/backup/run` | POST | Trigger manual backup creation |
| `/backup/toggle` | POST | Enable/disable automatic backups or change interval |
| `/backup/download/<filename>` | GET | Download a generated backup archive |

## License
TBD – choose and document an open-source or proprietary license before publishing.
