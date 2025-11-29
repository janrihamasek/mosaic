# Daily Log – 2024-11-11

- Date: 2024-11-11
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 11_11_mosaic.md

## Notes (raw import)

251111_backend_wearable_models
Goal: Create initial wearable data schema for ingestion and analytics.  
DONE
**Wearable Models**
- Added end-to-end wearable data models covering source metadata, raw payloads, canonical steps/HR/sleep entities, and daily aggregates with UTC timestamps, cascade-friendly FKs, dedupe keys, and (user_id, time) indexes to support ingestion through analytics (mosaic_prototype/backend/models.py (lines 123-366)).
- Exported the new classes via __all__ so downstream imports and migrations can easily reference the wearable schema objects (mosaic_prototype/backend/models.py (lines 369-382)).
**Migration**
- Introduced Alembic revision 20241201_000006 that builds all wearable tables with the same constraints/indexes defined in the ORM, ensuring Postgres stays in sync with the SQLAlchemy schema (mosaic_prototype/backend/migrations/versions/20241201_000006_add_wearable_tables.py (lines 1-211)).

251111_backend_wearable_ingest_api
Goal: Implement secure batch ingestion endpoint for wearable data.  

- Added strongly typed ingest payload models and validators so requests must include a valid TZ, dedupe key, and at least one record before they ever hit the DB (backend/schemas.py (lines 452-526), backend/security.py (lines 174-214)).
- Introduced a reusable _coerce_utc helper plus a dedicated rate-limit bucket for wearable ingestion to keep batch writes normalized to UTC and throttled independently (backend/app.py (lines 155-171), backend/app.py (lines 618-622)).
- Implemented POST /ingest/wearable/batch with JWT + API-key enforcement, Pydantic validation, source auto-provisioning, ON CONFLICT dedupe handling, structured error collection, and structlog metrics so clients get {accepted, duplicates, errors} while the server stores normalized payload snapshots in wearable_raw (backend/app.py (lines 2596-2813)).

251111_backend_wearable_etl_service
Goal: Build normalization and aggregation service for wearable ingestion pipeline.  

- Added a full wearable ETL layer (backend/wearable_service.py (lines 1-377)) that normalizes newly ingested raw payloads into the canonical steps/HR/sleep tables with strong validation, ensures idempotent upserts via Postgres ON CONFLICT, and captures affected day scopes so a companion WearableAggregator can upsert or prune wearable_daily_agg rows per (user, source, day). The aggregator exposes range rebuild helpers for scheduled jobs and emits structured logs for observability.
- Introduced orchestration helpers: backend/ingest.py (lines 1-27) lets the API trigger the ETL pipeline just by passing dedupe keys or raw IDs, and backend/agg_jobs.py (lines 1-27) provides simple entry points for cron/scheduled tasks to rebuild aggregates for a user/date range.
- Tightened the ingestion endpoint so any newly accepted raw dedupe keys immediately flow through the ETL service, with the endpoint now returning the ETL summary and logging failures (backend/app.py (lines 35-284)). This keeps the API idempotent while guaranteeing canonical/aggregate tables stay current after each batch.
- Hardened CSV import handling by scoping activity lookups to the unique name, surfacing cross-user conflicts, and making validation/detail payloads JSON-safe to avoid the previous TypeError during jsonify (backend/import_data.py (lines 1-157)).

251111_backend_wearable_daily_agg_job
Goal: Provide scheduled or manual job for rebuilding wearable daily aggregates.  

Implemented the wearable ETL stack so the ingestion path now normalizes raw payloads, aggregates canonical tables, and exposes a rebuild job:

- Created backend/wearable_service.py with the normalization logic for steps/HR/sleep, day-scoped aggregation, and idempotent wearable_daily_agg upserts plus logging.
- Added orchestration helpers in backend/ingest.py/backend/agg_jobs.py so respiratory batch ingestion can trigger the service by dedupe keys or IDs and scheduled jobs can rebuild specific date ranges.
- Wired the ingest endpoint to call the ETL helper after successful writes and return the ETL summary, while updating logging for those runs (backend/app.py).
- Extended manage.py with rebuild-wearable-agg, allowing cron/CLI runs to recompute daily aggregates for one or all users over a date span, logging metrics and returning {rows_updated, steps_total, sleep_minutes_total, avg_heart_rate, duration_s} after summing the canonical tables.

251111_frontend_wearables_page
Goal: Add a new Wearables page to visualize aggregated wearable metrics.  

- Extended the frontend API surface with fetchWearableDay/fetchWearableTrends so the new Redux slice can hit /wearable/day and /wearable/trends (frontend/src/api.js (lines 33-53)).
- Added wearableSlice (and Redux store wiring) that keeps day/trend caches, tracks loading/error states, and exposes thunks loadWearableDay/loadWearableTrends; included Jest coverage covering pending/fulfilled/rejected flows plus reset behavior (frontend/src/store/wearableSlice.ts, frontend/src/store/index.ts, frontend/src/__tests__/wearableSlice.test.ts).
- Created the Wearables dashboard view: three summary cards plus 7/30-day bar widgets for steps, heart rate, and sleep that react to the slice state (frontend/src/components/Wearables.jsx), and registered the page/tab inside Dashboard so it shows up next to Stats and re-triggers the thunks when refreshed (frontend/src/Dashboard.jsx).

251111_frontend_admin_healthconnect_inspector
Goal: Implement admin-only HealthConnect Inspector panel to audit wearable ingestion.  

- Added HealthConnect diagnostic calls to the API layer and admin store (frontend/src/api.js (lines 1-60), frontend/src/store/adminSlice.js (lines 1-120)), including the loadWearableSummary thunk that fetches /wearable/summary and /wearable/raw and tracks inspector state.
- Built AdminHealthConnectInspector UI that lets admins filter by type/date, shows ingestion totals, and lists recent raw records, then wired it into the admin panel’s nav so the new “Inspector” section appears alongside Health/NightMotion (frontend/src/components/Admin.jsx (lines 1-60), frontend/src/components/AdminHealthConnectInspector.jsx (lines 1-180)).
- No automated tests were run locally (node/npm environment not available here). Please run npm test -- wearableSlice.test.ts or your Jest suite to ensure the new slice logic behaves as expected.

251111_mobile_healthconnect_agent
Goal: Implement the Android HealthConnect Agent as a Capacitor plugin that reads wearable metrics (steps, heart rate, sleep sessions/stages), maintains a local delta-sync queue, and posts data to the Mosaic backend ingest API.  

**HealthConnect Agent**
- Android’s HealthConnectAgentPlugin now queries Health Connect for steps, heart rate, and sleep, then normalizes each record (including start/end timestamps and dedupe keys) before resolving the Capacitor bridge so the JS side gets canonical payloads (mobile/plugins/healthconnect-agent/android/src/main/java/com/mosaic/healthconnectagent/HealthConnectAgentPlugin.java (line 25)).
- The TypeScript bridge queues deltas in IndexedDB, checkpoints the latest timestamp per type, and drains the pending batch through an exponential-backoff POST with JWT + X-Device-Id, while also wiring online/auto-sync hooks for Connectivity events (mobile/plugins/healthconnect-agent/src/index.ts (line 1)), persisting in pending_readings (mobile/plugins/healthconnect-agent/src/storage.ts (line 3)), and handling retry/backoff for /ingest/wearable/batch (mobile/plugins/healthconnect-agent/src/sync.ts (line 1)).
- Added onboarding documentation with installation, initialization, usage samples, and notes about the canonical data shape so integrators can wire the plugin into Mosaic’s backend flow (mobile/plugins/healthconnect-agent/README.md (line 1)).

251111_frontend_pwa_versioning

Goal:  
Implement persistent PWA build versioning and cache management in the Mosaic frontend. Each build must generate a unique version tag (e.g., `mosaic-vYYYYMMDD`), display it in the UI, and use it as the cache version identifier in the service worker. Old caches must be automatically purged upon new activation, and the client should detect when a new version becomes available (silent “update available” event).

- Added an automated build-version generator (mosaic_prototype/frontend/scripts/generate-build-version.js (lines 1-13)) that writes src/buildVersion.js (mosaic_prototype/frontend/src/buildVersion.js (lines 1-6)) so __BUILD_VERSION__/BUILD_VERSION is available to both the app and service worker, and invoke it before start/build via the new prestart/prebuild hooks (mosaic_prototype/frontend/package.json (lines 21-28)).
- Reworked the service worker to derive CACHE_VERSION = __BUILD_VERSION__ and use versioned cache names for precaching, static, image, and API routes, while purging everything else inside the activate handler (mosaic_prototype/frontend/src/sw.js (lines 14-111)), and enhanced registerServiceWorker with updatefound/statechange logging plus an updatePWA() helper that forces an update+reload (mosaic_prototype/frontend/src/registerServiceWorker.ts (lines 15-69)).
- Surface the build tag in the UI via the new AppVersion component, which also exposes a “Check for update” button tied to updatePWA(), and render it beneath the dashboard header so users can see and proactively refresh to the latest build (mosaic_prototype/frontend/src/components/AppVersion.jsx (lines 1-34), mosaic_prototype/frontend/src/Dashboard.jsx (lines 431-474)).