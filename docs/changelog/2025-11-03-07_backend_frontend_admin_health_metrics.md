### 251103_devops_github_actions_ci_build

Unified GitHub Actions workflows were added to automatically test and build both the Flask backend and React frontend.
Each job sets up its environment, installs dependencies, runs migrations and tests, and uploads build artifacts.
The backend job uses PostgreSQL 15 and pytest coverage; the frontend job runs ESLint, Jest, and npm build.
Both jobs execute concurrently to provide faster CI feedback and ready-to-download bundles for staging deployment.

### 251103_backend_monitoring_logging

Structured logging using **Structlog 24.1.0** was integrated into the backend.
All request handlers now emit JSON logs with contextual fields (user id, latency, status code, etc.).
An in-memory metrics registry aggregates request totals, errors, and per-status counters, exposed through a new `/metrics` endpoint.
Error handling and backup scheduler logging were unified under the same structured format.

### 251103_docs_logging_guide

A new developer reference **`docs/LOGGING.md`** was created.
It documents the log structure, severity levels, Docker and CI usage tips, and examples for filtering structured logs via `jq` or `grep`.
The guide also explains how to interpret `/metrics` output and how to extend observability for future modules.

### 251103_devops_staging_postgres_ci

A complete staging environment was introduced with dedicated `.env.staging`, Docker services, and CI pipeline **`staging.yml`**.
It launches PostgreSQL, performs migrations, runs backend tests, smoke-tests `/metrics`, and rebuilds the frontend with staging API URLs.
The staging setup mirrors production closely, ensuring parity between developer tests and deployed builds.

### 251104_backend_metrics_calculation

The backend analytics layer was refactored for transparent and reproducible metric computation.
Category-specific daily ratios (R₍d,c₎) and an `active_day ≥ 0.5` flag were added as shared baselines.
Seven-day and thirty-day averages are now computed per category, excluding the current day.
Positive/negative activity logic was redefined, top-consistency outputs grouped by category, and tests/documentation synchronized with the new formulas.

### 251105_frontend_page_specs

Structured design specifications were added for all key frontend cards: **Today, Activities, Stats, Entries, NightMotion**.
Each `.md` file under `frontend/docs/frontend_pages/` outlines purpose, layout, core components, and expected backend data.
The set provides a consistent blueprint for implementing UI changes or refactors later.

### 251106_frontend_admin_dashboard_menu

A new **Admin** tab was added to the dashboard with sub-sections **User**, **Settings**, and **NightMotion**.
Existing backup/import panels were moved under Admin → Settings, and NightMotion tools are now loaded only within the admin area.
Navigation and routes were simplified—non-admin users no longer see or access admin-only features.

### 251106_backend_userid_schema_migration

User ownership was introduced into the core data tables.
`user_id` foreign keys were added to **activities** and **entries**, linked with cascading deletes for referential integrity.
An Alembic migration ensures clean schema upgrades and reversibility.
This change enables full data isolation per user account.

### 251106_backend_user_scope_filters

All API queries and mutations were scoped to the authenticated user.
JWT tokens now include the `is_admin` flag, and endpoints filter or stamp records by `user_id`.
Admins retain the ability to view or export other users’ data.
A CLI command **`assign-user-data`** allows reassignment of legacy records to specific users.
The application now supports simultaneous sessions for multiple logged-in users securely.

### 251106_backend_user_admin_endpoints

User profile and admin-management endpoints were added.
Users can fetch, update, or delete their own profiles (`/user`), while admins can list or delete any account (`/users`, `/users/<id>`).
A `display_name` field was introduced in the `User` model and included in JWTs.
Validation and access control helpers (`require_admin`, `validate_user_update_payload`) strengthen input safety and role enforcement.

### 251106_frontend_user_profile_ui

Frontend UI was extended to support profile management directly from the dashboard.
Users can edit their display name, update password, or delete their account through a new **ProfileModal** component.
Redux auth state was enhanced with async thunks for update/delete operations, and the dashboard header now displays the user’s name and admin status.

### 251107_backend_request_metrics

Lightweight **Prometheus-like** request metrics were implemented in the Flask backend.
A thread-safe store records per-endpoint totals, latency, and 4xx/5xx counters, exported in both JSON and text format via `/metrics`.
Comprehensive pytest coverage validates metrics accuracy across normal and error paths.
This forms the backend foundation for health monitoring and observability dashboards.

### 251107_backend_health_dashboard

A new `/healthz` endpoint and `flask health` CLI command summarize system health.
They report uptime, database/cache connectivity, and metrics freshness in JSON or terminal-table form.
Unit tests verify correct behavior under healthy and simulated failure conditions.
This provides quick diagnostics for admins and CI environments.

### 251107_backend_testdb_isolation

Automated tests now run against a dedicated **mosaic_test** PostgreSQL database.
`.env.test` defines connection parameters, and `scripts/run_pytest.sh` orchestrates database lifecycle (create → migrate → test → drop).
CI workflow **`tests.yml`** executes the same script, ensuring local and CI consistency with full isolation between test runs.

### 251107_frontend_admin_health_section

A **Health** section was added inside the Admin dashboard, visible only to administrators.
It fetches `/healthz` and `/metrics?format=json` via new API clients and displays summary cards, endpoint tables, and refresh controls.
A dedicated Redux slice handles loading, errors, and periodic updates.
This completes the UI layer for system observability, aligning frontend and backend monitoring.
