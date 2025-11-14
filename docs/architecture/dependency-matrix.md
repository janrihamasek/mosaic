# Mosaic Dependency Matrix

This matrix tracks direct dependencies between the major Mosaic subsystems so we can spot tight coupling or forbidden cross-layer imports. Rows indicate the caller/owner; columns indicate the dependency. Cells use `✔` for direct imports/calls and `⚠` to highlight hotspots (e.g., every request funneling through the same module). Use it alongside the [Dependency Map](dependency-map.md), [Dependency Graph](dependency-graph.md), and [Redux Flow map](redux-flow.md) when auditing architecture changes.

| Layer / Module | Components (React) | Redux Slices | Async Thunks | `apiClient.js` | Flask Endpoints | Service Modules (BackupManager, Wearable ETL, stream proxy, import_csv) | SQLAlchemy Models | Cache Layer (`CacheScope`, `cache_*`) | Metrics/Audit (`structlog`, `/metrics`) | NightMotion Proxy | BackupManager | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Components (Today, Stats, Admin, NightMotion, BackupPanel, etc.) | — | ✔ (use `useSelector`/`dispatch`) | ✔ (dispatch thunks) | — | — | — | — | — | — | ✔ (NightMotion only) | ✔ (BackupPanel UI) | Components should only touch Redux and local helpers. NightMotion + BackupPanel indirectly drive infra modules via slices. |
| Redux Slices (`activitiesSlice`, `entriesSlice`, `authSlice`, `adminSlice`, `backupSlice`, `nightMotionSlice`, `wearableSlice`) | — | — | ✔ (createAsyncThunk) | ✔ (thunks call API helpers using `apiClient`) | — | — | — | — | — | ✔ (nightMotion slice orchestrates stream fetch) | ✔ (backup slice dispatches BackupManager endpoints) | Slices centralize mutations; only thunks interact with IO. |
| Async Thunks (generated inside slices) | — | — | — | ✔ | ✔ | ✔ (call BackupManager endpoints, wearable ETL, stream proxy) | — | — | — | ✔ (NightMotion `startStream` uses fetch + proxy) | ✔ | High coupling: all network IO passes through this row. |
| `apiClient.js` | — | — | — | — | ✔ | — | — | — | — | — | — | Wraps Axios with auth headers; injects API key/JWT/CSRF and emits `mosaic-api-error`. |
| Flask Endpoints (`app.py`) | — | — | — | — | — | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | Endpoints orchestrate validators, rate limits, services, models, caches, metrics/logging. ⚠ High fan-in. |
| Service Modules (`backup_manager.py`, `wearable_service.py`, `import_data.py`, stream proxy helpers) | — | — | — | — | — | — | ✔ | ✔ (BackupManager updates cache indirectly via endpoints) | ✔ (wearable + backups log) | ✔ (stream_rtsp) | ✔ | Services encapsulate long-running jobs and DB access; avoid importing React/Redux. |
| SQLAlchemy Models (`models.py`) | — | — | — | — | — | — | — | — | — | — | — | Used only by Flask/services for persistence; no upstream dependencies. |
| Cache Layer (`cache_get/set`, `invalidate_cache`) | — | — | — | — | — | — | — | — | ✔ (metrics log cache health) | — | — | Only endpoints should touch cache helpers to avoid stale data. |
| Metrics & Audit (`structlog`, `/metrics`, `/healthz`, `audit.py`) | — | — | — | — | ✔ | ✔ | — | ✔ (healthz checks cache/db) | — | — | — | Logs & metrics observe every endpoint; no business logic flows back. |
| NightMotion Proxy (`stream_rtsp`, `/api/stream-proxy`) | — | — | — | — | ✔ | ✔ | — | — | ✔ (logs errors) | — | — | Dedicated path for MJPEG relays; front-end uses `fetch` directly (no `apiClient`). |
| BackupManager | — | — | — | — | ✔ | — | ✔ | — | ✔ | — | — | Provides scheduler state, backup runs, and download paths. |

## High-Coupling & Cycles
- **`apiClient` ↔ Flask Endpoints:** Every thunk hits `apiClient`, which funnels into Flask controllers. The combination is a deliberate choke point but also a hotspot—changes to headers, error handling, or controller auth impact the entire system (`⚠`).
- **Activities & Entries slices:** Activity thunks read from `entries.filters` to replay `loadEntries`, and entry thunks re-dispatch `loadActivities`/`loadStats`. This cross-slice dependency is acceptable but should be the ceiling; avoid adding component-level fetches that bypass these cascades.
- **Backup flows:** `BackupPanel` → `backupSlice` → async thunks → `/backup/*` endpoints → `BackupManager` (service + filesystem). Any schema change in `backup_settings` or the backup directory structure touches every layer.
- **NightMotion stream:** `NightMotion.tsx` bypasses `apiClient` because the MJPEG stream uses `fetch` directly; it still depends on `nightMotionSlice` for UI state and relies on `/api/stream-proxy`. Keep this isolated to avoid leaking stream logic elsewhere.
- **Metrics & cache:** `/healthz` and `/metrics` depend on `_metrics_state`, DB connectivity, and cache locks. Failing to update cache invalidations in endpoints has downstream impact on both administrative dashboards and health checks.

## Guidelines
1. **Keep Components → Redux-only:** UI layers must not import service modules or hit `fetch` except for the NightMotion stream (a conscious exception). All data mutations should go through thunks so cascades fire consistently.
2. **Do not import Redux from Flask/services:** Backend modules stay pure Python; cross-layer imports would break bundling and are disallowed.
3. **Centralise IO in thunks:** If a new feature needs to talk to an endpoint, add a thunk (or reuse an existing one) rather than issuing raw `apiClient` calls from components.
4. **Cache touches stay in controllers:** Only Flask endpoints may call `cache_get/set/invalidate`. Client code should trigger refreshes by invoking existing loaders.
5. **Document exceptions:** NightMotion’s fetch pipeline and BackupManager’s filesystem access are intentional cross-layer bridges. Highlight any new exception in this matrix before merging.
