# Daily Log – 2024-11-07

- Date: 2024-11-07
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 7_11_mosaic.md

## Notes (raw import)

- [x]  Zavést **metriky requestů a chyb** (prometheus-like, log summary). 🟧 (~2 000 tok.)
- [x] Přidat **health dashboard** v admin zóně / CLI report. 🟩 (~800 tok.)
- [x] pytest chyby
- [x] jest chyby
- [x] stats zas to počítá nějak blbě
- [x] activity detail si musí pamatovat předtím zvolenou value, ne abych ji musel nastavovat vždycky
- [x]  Zavést **activity logging** (uživatelská a systémová událost, audit). 🟨 (~1 800 tok.)

---
251107_backend_request_metrics
Goal: Implement lightweight Prometheus-like request and error metrics in the Flask backend.  
DONE
- Thread-safe metrics store with per-endpoint buckets, JSON/text exporters, reset helper, and periodic structured logging now live (mosaic_prototype/backend/app.py (lines 146-334)). This captures totals, latency, and 4xx/5xx counters for each (method, endpoint) and exposes get_metrics_json() / get_metrics_text() for both API responses and logging.
- Request lifecycle instrumentation now records metrics via the new helper, including exception paths, so every request contributes consistent method/endpoint metadata; /metrics defaults to Prometheus-style text while still supporting ?format=json (mosaic_prototype/backend/app.py (lines 360-404), mosaic_prototype/backend/app.py (lines 802-812)).
- Added focused pytest coverage that simulates multiple requests with deterministic latency plus 4xx/5xx scenarios through a test-only endpoint (mosaic_prototype/backend/tests/test_metrics.py (lines 1-58)).

251107_backend_health_dashboard
Goal: Add a system health dashboard endpoint and CLI report summarizing backend status and metrics.  
DONE
**Backend Updates**
- Added server-uptime tracking, richer metrics snapshots (including last-updated timestamps), and reusable health helpers for DB/cache checks plus summary calculations feeding both HTTP and CLI consumers (mosaic_prototype/backend/app.py (lines 149-372)).
- Exposed /healthz as a public endpoint returning Prometheus-aware request stats, connectivity flags, and the latest metrics timestamp; mirrored the same data in a new flask health CLI command that prints a compact table plus overall status (mosaic_prototype/backend/app.py (lines 874-902)).
**Tests**
- python3 -m pytest tests/test_metrics.py tests/test_health.py (fails: No module named pytest; environment doesn’t have pytest installed).
- Added targeted health-endpoint and CLI coverage exercising both healthy and forced-unhealthy scenarios to assert JSON payloads and CLI formatting (mosaic_prototype/backend/tests/test_health.py (lines 1-44)).

251107_backend_testdb_isolation
Goal: Ensure pytest runs automatically against a clean isolated PostgreSQL test database.  
DONE
**Isolated Tests**
- .env.test (line 1) defines the dedicated mosaic_test connection info (Postgres host/user/pass, matching DATABASE_URL) so both Docker services and the backend share a consistent, staging-free test configuration.
- scripts/run_pytest.sh (lines 4-88) now drives the full lifecycle: it checks for Docker Compose, exports .env.test, starts the Compose postgres service, force-drops/recreates mosaic_test, runs python manage.py upgrade && pytest inside mosaic_backend_dev with --env-from-file, and drops the DB again on exit.
- .github/workflows/tests.yml (lines 45-47) switches the backend job to execute bash scripts/run_pytest.sh from the repo root, keeping CI aligned with the new local workflow while still benefiting from the existing setup steps.

251107_frontend_admin_health_section
Goal: Add a Health section to the existing Admin card displaying system metrics and backend health status, visible only to admin users.  
DONE
- Admin navigation now exposes a “Health” tab for admins and loads the new panel component (frontend/src/components/Admin.jsx (lines 1-33)).
- Added a dedicated health/metrics Redux slice with async thunks, state, and selectors, plus wired it into the root store so UI can track refresh/error states (frontend/src/store/adminSlice.js (lines 1-70), frontend/src/store/index.ts (lines 7-24)).
- API client now exposes fetchHealth() and fetchMetrics() helpers that reach /healthz and /metrics?format=json (frontend/src/api.js (lines 182-190)).
- Implemented HealthPanel with summary cards, endpoint table, manual/automatic refresh, and integrated Loading/ErrorState feedback using the new slice data (frontend/src/components/HealthPanel.jsx (lines 1-279)).

251107_backend_activity_logging
Goal: Implement persistent audit trail for user and system events.  

**Audit Trail**

- Added a persistent ActivityLog ORM model plus serialization helper (backend/models.py (lines 1-120)) and an Alembic migration that creates the backing table with indexed filters (backend/migrations/versions/20241125_000005_add_activity_logs_table.py).
- Introduced backend/audit.py (lines 1-143), which wraps structlog with a runtime ring buffer, safely normalizes context, installs a shared handler, and persists every log_event() call through an isolated scoped session.

**App Integration**

- Wired the audit helper and logs blueprint into the Flask app, including handler installation and blueprint registration (backend/app.py (lines 78-135)).
- Instrumented the requested endpoints—register/login, add_activity, delete_entry, backup run/toggle/download, and CSV import—to emit success/failure audit events with useful context (backend/app.py (lines 916-1410), backend/app.py (lines 2419-2460)), ensuring both user and admin actions are now captured.

**Admin Log Access**

- Added an admin-only blueprint that serves paginated/filterable activity logs plus an optional runtime log snapshot sourced from the structlog buffer (backend/routes/logs.py (lines 1-89)), exposing /logs/activity and /logs/runtime.

251107_frontend_admin_logs_integration
Goal: Connect Admin UI to new ActivityLog and runtime log APIs.  
DONE
**UI Updates**
- Added typed API helpers for /logs/activity and /logs/runtime so the frontend can request both persistent and in-memory log feeds with auth headers (frontend/src/api.js (lines 182-201)).
- Extended the admin Redux slice with activityLogs / runtimeLogs state buckets and new loadActivityLogs / loadRuntimeLogs thunks, keeping their statuses, errors, and timestamps separate from health metrics (frontend/src/store/adminSlice.js (lines 1-123)).
- Built the new AdminLogs panel: dual-tab DataTable view with level badges, user resolution, and 60 s auto-refresh plus manual refresh + graceful error handling (frontend/src/components/AdminLogs.jsx (lines 1-303)), and wired it into the Admin navigation so only admins see the Logs section (frontend/src/components/Admin.jsx (lines 1-129)).
**Docs**
- Updated the Admin spec and README to cover the Logs section’s purpose, APIs, and behaviour, and added a dedicated AdminLogs spec detailing layout, columns, and refresh mechanics (docs/frontend_pages/Admin.md (lines 1-120), docs/frontend_pages/AdminLogs.md (lines 1-67), docs/frontend_pages/README.md (lines 1-11)).

251107_frontend_admin_logs_refinement
Goal: Align Admin Logs UI with backend semantics and improve clarity between runtime and activity logs.  

- AdminLogs.jsx now distinguishes the two data sources: timestamps render as YYYY-MM-DD HH:mm:ss, the header/subtitle call out whether you’re viewing persistent activity events or the in-memory buffer, and the timezone is noted alongside the refresh timestamp (frontend/src/components/AdminLogs.jsx (lines 14-345)). Runtime rows are enriched by parsing the JSON payload so the table shows Method/Route, Status, Duration, and User instead of a raw blob, while activity rows keep the user/event context but share the same level badge/timestamp styling for visual alignment (frontend/src/components/AdminLogs.jsx (lines 150-399)).
- The Admin Logs spec documents those UI behaviours, including the dynamic header copy, timestamp format, and the revised runtime column definitions so the docs stay in sync with the implementation (docs/frontend_pages/AdminLogs.md (lines 10-64)).