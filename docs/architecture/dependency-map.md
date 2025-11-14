# Mosaic Dependency Map

This map traces how Mosaic’s React/Redux frontend talks to the Flask backend, how API calls fan out into service modules and SQLAlchemy models, and where caches, storage, and events sit in between. Use it to reason about ownership of data, find where to plug new features, or understand which subsystems must be updated together.

## Frontend Dependency Flows

React components interact with Redux Toolkit slices, which expose thunks that call strongly typed helpers in `frontend/src/api.js`. Those helpers wrap `apiClient.js` (Axios with API key/JWT/CSRF headers and global error events) before reaching Flask endpoints. Offline helpers (`offline/queue`, `offline/snapshots`) and services (`services/authService.js`, `services/userService.js`) bridge to browser storage.

### Component → Redux → API pipeline

| Flow | Direction | Dependency type | Notes |
| --- | --- | --- | --- |
| Dashboard bootstrap | `Dashboard.jsx` → dispatches `loadActivities`, `loadEntries`, `loadToday`, `loadStats`, `fetchCurrentUserProfile` → thunks in `store/activitiesSlice.ts` + `store/entriesSlice.ts` + `store/authSlice.ts` → `api.js` (`fetchActivities`, `fetchEntries`, `fetchToday`, `fetchProgressStats`, `fetchCurrentUser`) → `apiClient` → `GET /activities`, `/entries`, `/today`, `/stats/progress`, `/user` | sync API | Ensures every tab has populated state once a user logs in; responses hydrate `activities`, `entries`, `stats`, and `auth` slices simultaneously. |
| Today editing & autosave | Today/Entries components → `entriesSlice.updateTodayRow` (local state) then `saveDirtyTodayRows` → `submitOfflineMutation` queue → POST `/add_entry` via Axios (`apiClient` attaches auth headers) → Flask `add_entry` controller → `entries` + `activities` tables | sync API + storage + cache | UI edits persist previews to `offline/snapshots` (`readTodaySnapshot`/`saveTodaySnapshot`). Backend invalidates `today` (60 s TTL) and `stats` (300 s TTL) cache buckets after every write. |
| Entries history & filters | `Entries.jsx` → `entriesSlice.loadEntries` → `fetchEntries` (URLSearchParams for filters) → `apiClient` → `GET /entries` | sync API | Uses pagination params resolved in `api.js`. Results stay in `entries.items` for filtering or exporting. |
| Stats dashboard | `Stats.jsx` → `entriesSlice.loadStats` → `fetchProgressStats` → `apiClient` → `GET /stats/progress` | sync API + cache | Flask caches stats per `(user_id,is_admin,date)` scope (`CacheScope`), so the slice only re-fetches when date filters change or other thunks manually refresh. |
| Activities management | `Activities` tab + dialogs → thunks in `activitiesSlice.ts` (`loadActivities`, `createActivity`, `updateActivityDetails`, `activateActivity`, `deactivateActivity`, `removeActivity`) → `fetchActivities` / mutation endpoints via `submitOfflineMutation` → `/activities`, `/add_activity`, `/activities/<id>` verbs | sync API + storage | Local optimistic state lives in `saveActivitiesSnapshot`, letting offline mutations queue via `offline/queue`; completed mutations dispatch reverse refreshes (see table below). |
| Admin health & metrics | `AdminHealth.jsx` → `adminSlice.loadHealth`/`loadMetrics` → `fetchHealth` + `fetchMetrics` (`?format=json`) → `/healthz`, `/metrics` | sync API | The health panel polls both endpoints; `/metrics` returns JSON snapshots derived from server request counters. |
| Logs inspector | `AdminLogs` views → `adminSlice.loadActivityLogs`/`loadRuntimeLogs` → `fetchActivityLogs` + `fetchRuntimeLogs` → `/logs/activity`, `/logs/runtime` | sync API | Log endpoints stream audit and runtime data maintained in back-end `audit.py`/`routes/logs.py`. |
| Backup tooling | `BackupPanel.jsx` (Admin → Settings) → `backupSlice` thunks (`loadBackupStatus`, `toggleBackup`, `runBackupNow`) → `fetchBackupStatus`, `toggleBackupSettings`, `runBackup` (plus `downloadBackupFile` for manual fetch) → `/backup/status`, `/backup/toggle`, `/backup/run`, `/backup/download/<file>` → `BackupManager` | sync API + storage | Results surface scheduler state, latest ZIP artefacts, and drive notifications. See the dedicated BackupManager section for the backend flow. |
| NightMotion stream | `AdminNightMotion.jsx` → `NightMotion.tsx` component → `nightMotionSlice` actions (`setField`, `startStream`) and direct `fetch` to `getStreamProxyUrl()` → `/api/stream-proxy` → `stream_rtsp` helper (ffmpeg) → camera RTSP feed | sync API (stream) + storage | Credentials + stream URL persist in `localStorage` (`STORAGE_KEY`). Stream responses are MJPEG frames; the slice only tracks status, while the component decodes boundaries and emits frames. |
| Authentication & profile | Login/Register forms → `authSlice.login`/`register` → `services/authService` (Axios client) → `/login`, `/register`; profile drawer → `authSlice.updateCurrentUserProfile`, `deleteAccount` → `userService` (`apiClient.patch/delete /user`) → Flask profile endpoints | sync API + storage | `authService` persists tokens in `localStorage` (`mosaic.auth`) and broadcasts changes via `subscribeAuthChanges`, which the store listens to so every tab stays in sync. |
| Wearable inspector | Admin wearable tab → `adminSlice.loadWearableSummary` → parallel `fetchWearableSummary` + `fetchWearableRaw` → `/wearable/summary`, `/wearable/raw` | sync API | Surfaces aggregated ETL output generated by backend `WearableETLService`. |

### Frontend services, storage, and events

- `apiClient.js` injects API key, JWT, and CSRF headers using `getAuthHeaders()`. Responses propagate friendly errors (from backend error codes) and emit a `mosaic-api-error` `CustomEvent` so `Dashboard.jsx` can show toast notifications — an event-style dependency that decouples error UI from every call site.
- `services/authService.js` provides login/register/logout helpers, centralises auth storage (`localStorage`), and exposes `subscribe` so `store/index.ts` can dispatch `setAuthState` whenever another browser tab modifies credentials. It also exposes token accessors for NightMotion streaming.
- Offline helpers (`offline/queue`, `offline/snapshots`) give `activitiesSlice` and `entriesSlice` a storage dependency: optimistic updates are written to disk and replayed when `initOfflineSync(store)` is called during bootstrap.
- `NightMotion.tsx` stores stream credentials (`nightMotionSlice` + `localStorage`), builds signed stream proxies with `getStreamProxyUrl`, fetches the MJPEG stream manually (so it can parse frames), and dispatches Redux status updates.

### Cross-slice reverse dependencies

Many thunks dispatch other slice thunks to keep the UI in sync after mutations. These reverse edges are intentionally explicit so selectors always see fresh data, even while backend caches are still warm.

| Triggering thunk(s) | Downstream refresh dispatches | Dependency type | Purpose |
| --- | --- | --- | --- |
| `activitiesSlice.createActivity`, `updateActivityDetails`, `activateActivity`, `deactivateActivity`, `removeActivity` | `loadActivities()` (self), `loadToday(date)`, `loadEntries(filters)` | Redux event chain + sync API | Newly created or reclassified activities must appear immediately in Today and Entries tables; the extra fetches also bust any stale offline snapshots. |
| `entriesSlice.saveDirtyTodayRows` | `loadToday(date)`, `loadEntries(filters)`, `loadStats({ date })` | Redux event chain + sync API + cache refresh | After batching POST `/add_entry` calls, re-fetches ensure Today rows clear their dirty flags, the history list matches the saved data, and `/stats/progress` reflects backend cache invalidations. |
| `entriesSlice.deleteEntry` | `loadStats({ date })`, `loadToday(date)` | Redux event chain + sync API | Deleting affects both Today view (if the date matches) and dashboards. |
| `entriesSlice.importEntries` | `loadEntries(filters)`, `loadStats({ date })`, `loadToday(date)` | Redux event chain + sync API | CSV imports may backfill historical rows, so all slices reload to reflect the import summary. |
| `authSlice.logout`, `deleteAccount` | `setAuthState(DEFAULT_STATE)` (reducers) + store-wide `subscribeAuthChanges` broadcast | storage + event | Clearing local storage triggers a storage event; the store’s subscriber dispatches `setAuthState` in every tab to drop protected screens. |

## Backend Dependency Flows

All HTTP controllers live in `mosaic_prototype/backend/app.py`. Each endpoint validates input (`security.py`), enforces API keys/JWTs and admin roles (`@before_request`, `@require_admin`), records metrics, and delegates to either inline SQL helpers (`db_utils.transactional_connection`) or dedicated service modules (`backup_manager.py`, `wearable_service.py`, `import_data.py`). SQLAlchemy models in `models.py` define tables (`activities`, `entries`, `users`, `backup_settings`, wearable tables, etc.), but controllers mostly run raw SQL for predictability.

| Area | Endpoint(s) | Service / helper path | Model / storage | Dependency type | Notes |
| --- | --- | --- | --- | --- | --- |
| Auth & profiles | `POST /register`, `POST /login`, `GET/PATCH/DELETE /user`, `GET /users`, `DELETE /users/<id>` | Inline logic inside `app.py` + validators (`validate_register_payload`, `validate_login_payload`, etc.) | `users` (SQLAlchemy), `activity_logs` (for audit) | sync API + storage | Register/login hash passwords (`werkzeug.security`), mint JWTs (`PyJWT`), and persist display names/admin flags. Profile updates and deletions invalidate caches so Today/Stats can no longer read orphaned data. |
| Entries & Today writes | `POST /add_entry`, `DELETE /entries/<id>`, `POST /finalize_day` | Inline SQL via `db_transaction`; idempotency helpers `_idempotency_lookup/_store` | `entries`, `activities` (goal metadata) | sync API + cache | Each mutation invalidates `today` & `stats` caches, emits audit logs, and (for add) auto-creates missing activities to keep `/today` joins complete. |
| Activities | `GET /activities`, `POST /add_activity`, `PUT /activities/<id>`, `PATCH /activities/<id>/(activate|deactivate)`, `DELETE /activities/<id>` | Inline SQL; reuse `_user_scope_clause` to enforce tenancy | `activities`, `entries` (bulk updates propagate new category/goal) | sync API + cache | CRUD is scoped per-user (admins can include unassigned rows). Mutations invalidate caches and, when updating, cascade new metadata into associated entries. |
| Stats & Today reads | `GET /stats/progress`, `GET /today` | Cache helpers (`cache_get`, `cache_set`, `CacheScope`), `parse_pagination` | `entries`, `activities` | cache + sync API | Both endpoints build per-user/per-role cache keys. Stats composes daily windows, category aggregates, and consistent-activity tables; Today joins activities with the day’s entries. |
| Import/export | `POST /import_csv`, `GET /export/csv`, `GET /export/json` | `import_data.run_import_csv`, `send_file` streaming helpers | `entries`, `activities` | sync API + storage + cache | Imports persist uploaded files temporarily, run validation via Pydantic helpers, and invalidate caches on success. Exports read directly from the DB and stream CSV/JSON blobs back to the frontend. |
| Backups | `GET /backup/status`, `POST /backup/run`, `POST /backup/toggle`, `GET /backup/download/<file>` | `backup_manager.BackupManager` | `backup_settings` table + filesystem ZIP/CSV/JSON artefacts | sync API + storage + scheduler | BackupManager ensures tables exist, tracks `last_run`, and manages a daemon thread that runs scheduled backups. Files live under `backend/backups/`. |
| NightMotion stream proxy | `GET /api/stream-proxy` | `stream_rtsp` helper (spawns `ffmpeg`), `limit_request("stream_proxy")` | No DB; proxies RTSP frames | sync API (stream) + event/log | Requires JWT + optional API key, rewrites RTSP URL with provided credentials, rate limits to 2/minute, and streams MJPEG frames back to the browser. Errors bubble as structured responses. |
| Wearable ingestion & ETL | `POST /ingest/wearable/batch` + `/wearable/*` read endpoints | `process_wearable_raw_by_dedupe_keys` from `ingest.py`, ETL pipeline in `wearable_service.py` | `wearable_raw`, `wearable_sources`, `wearable_canonical_*`, `wearable_daily_agg` | sync API + service module | Batch ingestion validates payloads, writes raw rows, and then invokes `WearableETLService` to normalise steps/HR/sleep before exposing summaries via the admin slice. |
| Observability & logs | `GET /metrics`, `GET /healthz`, `/logs/activity`, `/logs/runtime` | Metrics registry (`_record_request_metrics`, `_ensure_metrics_logger_started`), audit logger (`audit.py`, `routes/logs.py`) | In-memory metrics store, `activity_logs` | event/log + sync API | Every request binds `structlog` context, records duration/status, and contributes to the JSON/Prometheus-style `/metrics` output. `/healthz` pings DB + cache, `/logs/*` stream structured audit/runtime events. |

### Cache architecture

- `CacheScope` couples each in-memory cache entry to `(user_id, is_admin)`, preventing cross-tenant leaks. Keys are namespaced as `prefix::scope::params`.
- `TODAY_CACHE_TTL = 60` seconds and `STATS_CACHE_TTL = 300` seconds; both caches live in `_cache_storage` protected by `_cache_lock`.
- `cache_get` deep-copies cached payloads to avoid accidental mutation. `cache_set` stores `(expires_at, payload, scope)`. `invalidate_cache(prefix)` scans keys by prefix and eagerly evicts matches.

### Cache invalidation map

| Trigger | Cache(s) invalidated | Reason |
| --- | --- | --- |
| `DELETE /user` (self) & `DELETE /users/<id>` (admin) | `today`, `stats` | User removal should remove all per-user cached state. |
| `POST /add_entry` (including idempotent replays) | `today`, `stats` | Any new/updated entry affects Today rows and dashboard ratios. |
| `DELETE /entries/<id>` | `today`, `stats` | Removing an entry reopens activity slots and alters stats. |
| `POST /add_activity` (and idempotent overwrite path) | `today`, `stats` | Activities define Today’s checklist and goal baselines. |
| `PUT /activities/<id>` | `today`, `stats` | Changing category/goal/description alters Today rows and stats denominators. |
| `PATCH /activities/<id>/activate` & `/deactivate` | `today`, `stats` | Activation status controls Today visibility and completion metrics. |
| `DELETE /activities/<id>` | `today`, `stats` | Removing a deactivated activity shrinks the Today checklist and analytics. |
| `POST /finalize_day` | `today`, `stats` | Auto-generated zero-value entries must be reflected immediately. |
| `POST /import_csv` | `today`, `stats` | Bulk imports can rewrite arbitrary dates and activities. |

### NightMotion stream-proxy flow

1. Admin toggles the NightMotion form. `NightMotion.tsx` pulls saved credentials (`nightMotionSlice` + `localStorage`) and validates the RTSP URL locally.
2. On submit, it reads the current JWT/CSRF pair via `authService.getAccessToken()`/`getCsrfToken()`, dispatches `startStream`, and opens `fetch(getStreamProxyUrl(streamUrl, username, password))`.
3. The backend route `/api/stream-proxy` enforces JWT + API key, rate limits via `limit_request`, injects camera credentials into the RTSP URL if needed, then calls `stream_rtsp`. That helper spawns `ffmpeg` with `-f mjpeg`, continuously reads frames, and yields `multipart/x-mixed-replace` boundaries.
4. The component reads the `ReadableStream`, splits frames at boundary markers (`--frame`, CRLF headers), creates object URLs, and swaps the `<img>` `src`. Errors dispatch `setStatus("error")` and notify the Admin UI.
5. Stopping the stream aborts the fetch controller, revokes object URLs, and dispatches `stopStream`. Backend processes terminate gracefully thanks to the cleanup logic inside `stream_rtsp`.

### BackupManager flow

1. Admin navigates to Settings → Backups; `BackupPanel.jsx` dispatches `loadBackupStatus`, which hits `/backup/status`. The response includes `enabled`, `interval_minutes`, `last_run`, and a `backups` list generated by `BackupManager.list_backups()`.
2. Toggling automation or changing intervals triggers `backupSlice.toggleBackup` → `POST /backup/toggle`. `BackupManager.toggle` upserts a row in `backup_settings`, ensuring the scheduler thread sees the new interval on its next poll (minimum 5 min).
3. Manual runs call `backupSlice.runBackupNow` → `POST /backup/run`, which in turn calls `BackupManager.create_backup(initiated_by="api")`. The manager uses `transactional_connection` to read activities/entries, writes JSON + CSV snapshots, zips them, updates `last_run`, and returns filenames.
4. Downloading uses `downloadBackupFile` (`GET /backup/download/<filename>`); the backend validates filenames, streams the ZIP, and `BackupPanel` creates an object URL for download, then revokes it.
5. Independently, `_ensure_scheduler_loop` starts a daemon thread that checks `backup_settings`. If enabled and `last_run` exceeds the interval, it calls `create_backup(initiated_by="scheduler")`. Errors are logged through `structlog` but don’t crash the process.

### Metrics & health instrumentation

- `_start_request_timer` and `_log_request` (Flask hooks) bind request IDs, capture duration, and log `request.completed` events through Structlog. `_record_request_metrics` stores counts, latencies, and status tallies per `(method, endpoint)`.
- `_ensure_metrics_logger_started` spawns a periodic thread that logs a snapshot of `_metrics_state`. `/metrics` serialises the store either as JSON (used by the Admin Health view) or Prometheus plaintext. `/healthz` verifies DB connectivity (`_check_db_connection`) and cache health (`_check_cache_state`) to return a derived status code.
- Admin Health polls both endpoints via `adminSlice`, so regressions in metrics or cache state surface immediately in the UI, matching the backend’s dependency layout.

---

With these flows documented, you can trace any feature end-to-end: identify which Redux slice owns the UI state, which API helper and controller it hits, what service/module mutates data, and how caches or events propagate updates elsewhere.
