# Mosaic Project – Current State Report

## 1. Project Overview

### Purpose and Goals
Mosaic is a multi-tenant activity tracking platform that helps individuals capture daily rituals, measure streaks, and review long-term progress while giving administrators observability into system health. Users log activities with qualitative notes, compare day-level summaries, and monitor rolling analytics. The platform emphasises low-friction data entry, strong validation, and near-real-time feedback, while the new Admin area surfaces backups, NightMotion tools, and uptime metrics for operators.

### Technology Stack
- **Frontend:** React 18 with React Router v6, Redux Toolkit, react-hook-form, and Axios layered behind `apiClient.js`. The UI is gradually migrating to TypeScript (`tsconfig.json`, typed slices, and `types/` utilities) while retaining JSX components. A custom dark-mode design system in `styles/common.js` plus hooks such as `useBreakpoints` keep Admin, Health, and NightMotion views consistent. Jest 29 + React Testing Library (configured via `jest.config.js`, `jest.setup.ts`, and `setupTests.ts`) and ESLint (`npm run lint`) gate pull requests alongside TextEncoder/TextDecoder polyfills so NightMotion tests execute under Node 18.
- **Backend:** A Flask 3 service (`backend/app.py`) with SQLAlchemy, Flask-Migrate, Pydantic-based validation helpers, PyJWT authentication, and Structlog 24.1 JSON logging. Request hooks attach `request_id`, user context, and feed a custom in-memory metrics registry surfaced through `/metrics` (text or JSON) and `/healthz`. Supporting modules include `backup_manager.py`, a NightMotion MJPEG proxy, and `manage.py` CLI commands (migrations plus `assign-user-data`).
- **Database:** PostgreSQL powers Activity, Entry, User, and BackupSettings models with `user_id` foreign keys and cascading deletes to guarantee data isolation. `.env.dev`, `.env.prod`, `.env.staging`, and `.env.test` describe connection strings. `scripts/run_pytest.sh` provisions and tears down a disposable `mosaic_test` database inside Docker for reproducible integration tests.
- **Tooling & Infrastructure:** Docker Compose spins up backend, frontend, and Postgres containers for dev, prod, test, and staging parity. GitHub Actions workflows (`ci.yml`, `tests.yml`, `backend-tests.yml`, `staging.yml`) install dependencies, run Pytest/Jest/ESLint, upload coverage and frontend build artifacts, and smoke-test `/metrics` in a staging-like environment. Operational references live in `docs/LOGGING.md`, `docs/METRICS.md`, and page-specs under `docs/frontend_pages/`.

### Development History and Direction
Recent development (see `docs/changelog/2025-11-03-07_backend_frontend_admin_health_metrics.md`) delivered:
- Structured logging with Structlog, an in-memory metrics store + `/metrics` endpoint, `/healthz` + `flask health`, and a comprehensive `docs/LOGGING.md` guide.
- Unified CI plus a staging workflow that provisions dedicated `.env.staging`, runs migrations/tests against PostgreSQL 15, smoke-tests `/metrics`, and builds the frontend with staging API URLs.
- Analytics refactors that add category baselines (`R₍d,c₎`), active-day flags, seven/thirty-day averages, and synchronized documentation in `docs/METRICS.md`.
- Frontend documentation for Today/Activities/Stats/Entries/NightMotion pages, alongside Admin navigation rework that relocates backups/import/export and lazily loads NightMotion tooling.
- Multi-tenant hardening: `user_id` columns on activities/entries, JWTs carrying `display_name`/`is_admin`, `/user` profile endpoints, admin `/users` management, CLI data-assignment, and frontend profile management.
- Observability-focused UI: Admin → Health queries `/healthz` and `/metrics`, Admin → Settings manages backups/import/export, and Admin → NightMotion isolates stream-proxy tools.

The current trajectory prioritises tenant isolation, production-grade observability, typed/shared UI specs, and preparing the analytics layer for richer integrations (CSV import pipelines, wearable devices, and live monitoring dashboards).

## 2. System Architecture

### Repository Layout
```
.
├── backend/                # Flask app (app.py), services, migrations, tests, backup + wearable modules
│   ├── database/           # init-mosaic.sql mounted by docker-compose for Postgres bootstrap
│   ├── routes/, security.py, backup_manager.py, ingest.py, wearable_service.py, etc.
│   └── requirements.txt    # pip deps used by Docker + GitHub Actions
├── frontend/               # React 18 + Redux Toolkit codebase (single canonical UI)
│   ├── src/                # components, slices, pages, services, utils, tests, types
│   ├── public/             # CRA assets
│   └── Caddyfile           # served by Dockerfile.frontend runner
├── docs/                   # merged architecture + product docs (API_DOCS, LOGGING, METRICS, frontend_pages, changelog)
├── mobile/                 # Capacitor/Android client (ignored build artifacts)
├── scripts/                # automation helpers (run_pytest.sh)
└── docker-compose.yml      # backend/frontend/postgres stack for dev+staging
```

### Layer Interactions
- **React ⇄ Flask:** `apiClient.js` injects JWT/CSRF headers, optional `X-API-Key`, and dispatches global `mosaic-api-error` events consumed by `Dashboard`. Every request is scoped server-side by `user_id`, while admin-only endpoints additionally require `require_admin`. NightMotion tooling calls `/api/stream-proxy`, and the Admin health view polls `/healthz` + `/metrics?format=json`.
- **Redux as Integration Layer:** Redux Toolkit thunks orchestrate multi-step workflows (`entries`, `activities`, `backup`, `admin`, `nightMotion`). Completed thunks cascade into secondary refreshes (e.g., activating an activity invalidates `today`/`stats`; running a backup refreshes status and download lists).
- **Persistent & Cross-Tab State:** `authService` keeps tokens, `displayName`, `isAdmin`, and expiry metadata in `localStorage` and broadcasts changes between tabs. Filters, selected tabs, and NightMotion credentials live in slice state so Admin tools remember operator preferences.
- **Database Access & Transactions:** SQLAlchemy sessions (via `db_utils.transactional_connection`) wrap writes to enforce commit/rollback semantics. Query builders append `user_id` filters unless the caller is admin. The CLI command `assign-user-data` re-owns orphaned records and can grant admin rights atomically.
- **Observability Instrumentation:** Request hooks bind `request_id`, duration, route, and `user_id` into structlog context vars. The in-memory metrics store tallies per-endpoint counts, latency, status codes, and 4xx/5xx totals, exposed to Prometheus via text/plain and to the Admin UI via JSON.

### Redux Store Structure
- **`authSlice` (`frontend/src/store/authSlice.ts`)** keeps authentication state plus statuses for login/register/logout/profile/update/delete flows. Thunks talk to `/login`, `/register`, `/user`, and persist refreshed claims (username, displayName, isAdmin) to storage.
- **`activitiesSlice`** tracks lists, mutation flags, and triggers refetches of `entries`/`today` when activities change or are de/activated.
- **`entriesSlice`** manages paginated `/entries`, `/today` tables, stats snapshots, CSV import status, and debounced auto-save queues.
- **`backupSlice`** drives `/backup/status|run|toggle` plus download helpers, exposing latest backups, interval settings, and UI state (toggling/running/downloading).
- **`adminSlice`** polls `/healthz` and `/metrics`, storing last fetch timestamps/errors for the Health panel.
- **`nightMotionSlice`** stores credentials, stream URL, and playback status for NightMotion; actions drive UI-only state so credentials never leave the browser unless proxied.
- `store/index.ts` wires slices together, hydrates auth from storage on boot, and subscribes to broadcast changes.

### Primary Data Flows
1. **Authentication & Profile Management:** `LoginForm`/`RegisterForm` validate credentials client-side, dispatch `auth/login|register`, and persist claims. `AdminUser` (User tab) calls `/user` via `updateCurrentUserProfile` to change display names/passwords and can delete the account. Admins see role badges in the header.
2. **Daily Tracking:** `Today.jsx` loads `/today`, renders per-activity rows with inline inputs, and calls `saveDirtyTodayRows` to debounce `/add_entry` writes while showing auto-save toasts. Cache invalidation on the backend refreshes `/today` and `/stats`.
3. **Activity Management:** `ActivityForm` creates or updates activities, `ActivityTable` toggles activation/deletion, and Redux thunks (`createActivity`, `updateActivity`, `activateActivity`, etc.) fan out to refresh dependent slices.
4. **Analytics Dashboard:** `Stats.jsx` calls `/stats/progress` to render completion gauges, streaks, category carousels (`avg_goal_fulfillment_by_category`), positive/negative ratios, and top-consistency tables, mirroring formulas from `docs/METRICS.md`.
5. **Import / Export:** `CsvImportButton`, `ImportExportPanel`, and backend `/import_csv`, `/entries/export.(csv|json)` endpoints validate payloads (extensions, size, schema) and surface friendly toast summaries.
6. **Backups & Admin Settings:** Admin → Settings hosts `BackupPanel` (automatic backup toggles, manual run, download) and `ImportExportPanel`. Redux `backupSlice` keeps track of intervals, last run, and download metadata aligned with `backup_manager.py`.
7. **Observability & NightMotion:** Admin → Health polls `/healthz` + `/metrics?format=json`, surfaces uptime/error summaries, and lists per-endpoint metrics with tone-aware cards and manual refresh. Admin → NightMotion gates stream proxy tools behind JWT/role checks while `NightMotion.tsx` manages the `nightMotionSlice` state machine.

## 3. Data Model and API

### Database Schema
- **`activities`**: `id`, `user_id` (FK → `users.id`, cascade on delete), `name`, `category`, `goal`, `description`, `active`, cadence fields, `deactivated_at`. Indices cover `user_id`, `name`, and `category`.
- **`entries`**: `id`, `user_id` FK, `date`, `activity`, `description`, `value`, `note`, denormalised `activity_category` and `activity_goal`. Composite lookups (date/activity/user) are enforced in queries.
- **`users`**: `id`, `username`, `password_hash`, `display_name`, `is_admin`, `created_at`. Back-populated relationships cascade deletions.
- **`backup_settings`**: scheduler configuration for the automatic ZIP backup process.
Schema changes run through Flask-Migrate; `manage.py` supplies `init`, `migrate`, `upgrade`, and `assign-user-data` commands to bootstrap or remediate environments.

### API Surface
- **Auth & Profile:** `POST /register`, `POST /login` issue JWTs with `is_admin` and `display_name` claims plus CSRF tokens. `GET /user`, `PATCH /user`, and `DELETE /user` let users maintain their profiles. Admins can `GET /users` (list) and `DELETE /users/<id>` to curate tenants.
- **Activities & Entries:** `GET /activities` (with `?all=true`), `POST /add_activity`, `PUT /activities/<id>`, `PATCH /activities/<id>/(activate|deactivate)`, `DELETE /activities/<id>`. Entries support `GET /entries` (pagination/filtering), `POST /add_entry`, `DELETE /entries/<id>`, and `POST /finalize_day`. All queries automatically scope to the authenticated `user_id` unless the caller is admin.
- **Analytics & Observability:** `GET /today`, `GET /stats/progress`, and CSV imports/exports share the recalibrated metrics definitions documented in `docs/METRICS.md`. `/metrics` returns Prometheus text by default or JSON when `?format=json`; `/healthz` (and `flask health`) reports DB/cache checks, uptime, request throughput, and error ratios.
- **Backups & Admin Tooling:** `GET /backup/status`, `POST /backup/run`, `POST /backup/toggle`, `GET /backup/download/<filename>` manage ZIP archives. `/api/stream-proxy` secures NightMotion MJPEG relays via per-minute rate limits. CSV/JSON exports stream via `send_file`, and all Admin routes require both valid JWT + API key when configured.

### Validation, Auth, and Rate Limiting
- Pydantic schemas in `schemas.py` back every payload, including the new `UserUpdatePayload` for `/user` updates. `validate_*` helpers normalise values, enforce numeric bounds, and throw `ValidationError` with friendly codes.
- `require_api_key` enforces `MOSAIC_API_KEY` outside of designated `PUBLIC_ENDPOINTS`, and `require_admin` guards management endpoints. JWT middleware attaches `current_user` to `g`, supplies `is_admin`, and binds `user_id` to structlog context.
- In-memory rate limiting (`SimpleRateLimiter`) and helper `limit_request` cap login/register, activity mutations, imports, stream-proxy usage, etc. Responses include `too_many_requests` metadata so clients can back off.
- CLI `assign-user-data` (in `manage.py`) reassigns orphaned activities/entries to a chosen user and can promote that user to admin, easing migrations for legacy datasets.

### Caching and Invalidation
`cache_get`/`cache_set` apply TTL-based caching (60s for `/today`, 300s for `/stats`). Mutations call `invalidate_cache("today")` or `invalidate_cache("stats")` to drop derived payloads. The cache is in-memory per Flask process; keys currently incorporate request parameters (date, limit, offset) but not `user_id`, so cache correctness relies on single-tenant usage of a process.

## 4. Frontend (React)

### Component Landscape
- **Shell & Navigation:** `App.jsx` gates auth routes, `Dashboard.jsx` hosts tab navigation (`Today`, `Activities`, `Stats`, `Entries`, `Admin`) plus `Notification` toasts and the global error bus. Tabs persist in storage so the UI restores context after reloads.
- **Forms & Tables:** `LoginForm`, `RegisterForm`, `ActivityForm`, `EntryForm`, and `CsvImportButton` share react-hook-form validation, accessible error messaging, and disabled states until valid. `ActivityTable`/`EntryTable` render sortable lists with `Loading`/`ErrorState` wrappers and share empty-state messaging.
- **Admin:** `components/Admin.jsx` dynamically builds the menu (`User`, `Settings`, `Health`, `NightMotion`), restricting non-admin users to the profile view. `AdminUser` provides profile editing/password reset/delete flows. `AdminSettings` wraps `BackupPanel` + `ImportExportPanel`, and `AdminNightMotion` scopes NightMotion controls to the Admin tab.
- **Observability Widgets:** `HealthPanel` (Admin → Health) displays uptime, req/min, error rates, DB/cache status, and per-endpoint metrics with tone-aware cards and manual refresh. It auto-polls every 60 seconds and shares `Loading`/`ErrorState`.
- **NightMotion:** `NightMotion.tsx` plus `nightMotionSlice` manage credentials and stream status; MJPEG playback occurs only when the Admin tab toggles it on.
- **NightMotion & Stats Visuals:** `Stats.jsx` renders completion gauges, streak badges, distribution pies, ratio cards, and category carousels that align with `docs/frontend_pages/Stats.md`. Shared animation helpers come from `utils/animations.js`.

### State, Validation, and Typing Patterns
TypeScript now powers core slices (`authSlice.ts`, `entriesSlice.ts`, `activitiesSlice.ts`, `nightMotionSlice.ts`, `store/index.ts`) and shared types under `src/types`. React-hook-form enforces trimming, numeric ranges, and cross-field checks (e.g., password confirmation) before dispatching thunks. `useBreakpoints` keeps Admin/Settings layouts responsive, and `styles/common.js` centralises theming. Auth state synchronises across tabs via `authService.subscribe`, ensuring logout/login events propagate instantly.

### Daily Summaries, Analytics, and Activities
`Today` coordinates per-activity goal previews, entry editing, and auto-save feedback. `Stats` consumes the richer payload (category ratios, active-day counts, positive vs negative, top consistent activities) and now mirrors the formulas published in `docs/METRICS.md`. Redux selectors slice snapshots for quick comparisons, and the UI exposes refresh buttons to force cache refreshes after a burst of edits.

### Admin, Backups, and Observability
`BackupPanel` surfaces auto-backup toggles, interval controls, manual runs, and download buttons that stream ZIPs via `downloadBackupFile`. `ImportExportPanel` consolidates CSV import with CSV/JSON exports while providing inline success/error toasts. Admin-only sections lazy-load heavy components (NightMotion, Health) to keep the default dashboard light, and menu state collapses to single-row tabs on compact layouts.

## 5. Testing and Quality

### Backend Test Coverage
Pytest suites under `backend/tests/` cover:
- **Auth & Profiles (`test_auth.py`)** – registration/login, JWT expiry, profile fetch/update/delete, and cache invalidation.
- **API & Transactions (`test_api.py`, `test_transactions.py`)** – activity/entry CRUD, pagination, finalize-day flows, CSV import/export paths, and transactional rollback semantics.
- **Validation & Imports (`test_validation.py`, `test_import_validation.py`)** – Pydantic enforcement, CSV schema guardrails, payload normalisation.
- **Backups & NightMotion (`test_backup_manager.py`, `test_stream_proxy.py`)** – backup scheduling/run logic, download paths, and stream proxy constraints.
- **Observability (`test_metrics.py`, `test_health.py`)** – metrics counters, `/metrics` formats, `/healthz` and CLI health summaries, error-path coverage.
`scripts/run_pytest.sh` provisions a dedicated `mosaic_test` database via Docker Compose, applies migrations, runs the suites, and guarantees cleanup—this script runs locally and inside GitHub Actions to keep dev/CI parity.

### Frontend Quality Practices
Frontend CI now enforces:
- Jest + React Testing Library suites in `frontend/src/__tests__/` (LoginForm validation, toast helpers, entries/nightMotion slices/components). Snapshots live under `__tests__/__snapshots__`.
- ESLint with `--max-warnings=0`, covering `.js/.jsx/.ts/.tsx`.
- CRA build as an end-to-end smoke test.
Manual exploratory checklists remain for complex flows (Admin menu, Health panel, NightMotion streaming), and the `docs/frontend_pages/*.md` files act as canonical specs for designers/devs during refactors.

### Continuous Integration
- **`ci.yml`:** Parallel backend/frontend jobs with PostgreSQL 15 services, coverage upload, ESLint/Jest gates, and frontend build artifacts.
- **`tests.yml`:** Reuses `scripts/run_pytest.sh` for backend isolation and runs ESLint/Jest/build as a lighter smoke test per push/PR.
- **`backend-tests.yml`:** Focused backend-only workflow for backend-heavy PRs.
- **`staging.yml`:** Full staging verification that applies migrations using `.env.staging`, runs tests, boots Flask, curls `/metrics`, and builds the frontend with staging env vars (API URL, API key labels). All workflows archive logs/artifacts for triage.

## 6. Current Development Status

### Latest Enhancements
- **Observability Stack:** Structlog JSON logging, in-memory request metrics, `/metrics` (text + JSON), `/healthz`, and an Admin Health UI bring actionable telemetry plus documented playbooks (`docs/LOGGING.md`).
- **Analytics Accuracy:** `/stats/progress` now computes category baselines, active-day flags, seven/thirty-day averages, and top-consistency tables in lockstep with `docs/METRICS.md`, keeping the frontend and backend definitions aligned.
- **Admin & Multi-Tenancy:** `user_id` ownership on activities/entries, JWT claims with `display_name`/`is_admin`, `/user` self-service endpoints, `/users` admin APIs, `assign-user-data` CLI, and new Admin UI tabs enforce tenant isolation while exposing operator tooling.
- **DevOps & Staging Parity:** `.env.staging`, GitHub Actions `ci.yml` + `staging.yml`, and `scripts/run_pytest.sh` ensure migrations/tests run against PostgreSQL 15 with smoke tests for `/metrics`, and artifacts are ready for deployment.
- **Frontend Documentation & Tests:** Page specs under `docs/frontend_pages/` codify layout/UX, while Jest suites cover Login, NightMotion, slices, and shared utilities with TextEncoder polyfills baked into the Jest environment.

### Open Work and TODOs
- **Cache Namespacing:** `/today` and `/stats` cache keys omit `user_id`, so multi-tenant deployments risk data leakage if a process serves multiple users simultaneously.
- **Metrics Persistence:** The `/metrics` store resets on process restarts and lacks long-term retention/export; no Prometheus scraper or alerting hooks exist yet.
- **TypeScript/Test Coverage Gaps:** Several slices/components (e.g., `adminSlice.js`, `BackupPanel.jsx`) remain JavaScript-only and untested, leaving the newly added Admin flows without automated regression coverage.
- **Admin & Audit Trail:** Admin UI can list/delete users but lacks audit logging, search, or granular role management; CLI (`assign-user-data`) is the only way to reassign ownership.
- **Responsive UX & Mobile:** Admin/Health/NightMotion layouts are desktop-first; mobile views lack gesture-friendly controls and stress-tested breakpoints.

### Planned / Proposed Directions
- Namespace cached payloads by `user_id` (and potentially `is_admin` scope) plus add regression tests to prevent cross-tenant leakage.
- Export metrics to a durable store (Prometheus, OTLP) with alerting/paging hooks, and add uptime dashboards for `/healthz`.
- Finish the TypeScript migration, extend Jest/RTL coverage to Admin/Health/Backup components, and add Cypress/Playwright smoke tests for mission-critical flows.
- Expand Admin capabilities (search, filter, invite flows, audit logging) so operators can manage users without touching the CLI.
- Deliver responsive layouts (CSS grid/breakpoints) and visual regression tests so Admin tools remain usable on tablets/phones.

## 7. Summary and Recommendations

### Strengths
- **Tenant Isolation & Security:** User-owned data, JWT claims, `/user` endpoints, `require_admin`, and CLI tooling provide a solid foundation for multi-user deployments.
- **Observability:** Structured logging, `/metrics`, `/healthz`, the Admin Health UI, and published `LOGGING.md` make diagnosing issues far easier than before.
- **DevOps Discipline:** Dockerized environments, scripted test databases, and layered GitHub Actions workflows (CI + staging + targeted suites) keep builds reproducible.
- **Data & Backup Tooling:** Automatic/manual backups, CSV/JSON import-export, and documented analytics formulas (`docs/METRICS.md`) reduce operational risk.

### Weaknesses
- **Non-Namespace Caches:** `/today` and `/stats` caches can cross-contaminate tenants because keys do not include `user_id`.
- **Transient Metrics:** Request metrics live only in memory, so restarts wipe history and no external monitoring or alerting exists.
- **Partial TypeScript/Testing:** Key Admin/Backup components remain untyped and lack Jest coverage, so regressions may slip through despite new flows.
- **Limited Admin Controls:** Beyond delete/list, there is no audit log, search, or UI for reassigning data—operators still need CLI access.

### Recommendations
1. **Namespace Cached Payloads:** Include `user_id`/role in cache keys (and tests) for `/today` + `/stats`, or move caches to a per-user store to guarantee tenant safety.
2. **Persist Metrics & Alerts:** Emit `/metrics` to Prometheus (or OTLP), add scraping configs, and wire alerts for error rates, latency, and health failures.
3. **Complete TypeScript & Test Coverage:** Convert remaining slices/components to TypeScript, add Jest/RTL suites for Admin/Health/Backup/NightMotion, and integrate component snapshot tests.
4. **Enhance Admin Tooling:** Build UI-driven user search, invite, and data-reassignment flows plus an audit log; surface backup/export history in the Admin tab.
5. **Responsive & Accessibility Push:** Add mobile breakpoints, keyboard navigation, and contrast audits to Admin/Health/NightMotion views, backed by automated visual tests.

---

This document captures Mosaic’s current capabilities, architecture, and risk profile. With tenant isolation, observability, and DevOps discipline in place, the next wave of work can tighten cache correctness, telemetry retention, and admin UX while finishing the TypeScript + automated testing rollout.
