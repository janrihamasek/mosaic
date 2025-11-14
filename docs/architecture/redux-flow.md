# Mosaic Redux Flow Map

Redux Toolkit drives every Mosaic screen. Each slice owns a portion of the UI state, exposes async thunks that hit Flask endpoints through `frontend/src/api.js`, and then cascades follow-up actions to keep other slices in sync. This guide lists every thunk, the API it calls, and the downstream refreshes or invalidations it triggers.

## Legend
- **Endpoint** – HTTP method + path the thunk hits (via `apiClient`).
- **Downstream cascades** – Other slices or thunks dispatched after success (e.g., refresh Today/Stats) plus notable storage/cache side effects.

## `authSlice`

| Thunk | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `login` | `POST /login` (via `services/authService`) | Persists tokens to `localStorage` and dispatches `setAuthState`; `Dashboard`’s bootstrap effect reacts to `isAuthenticated` and replays `loadActivities`, `loadEntries`, `loadToday`, `loadStats`. |
| `register` | `POST /register` | No immediate cascades; UI typically navigates to login. |
| `logout` | _Clears storage only_ | Resets auth state and fires the `subscribeAuthChanges` listener registered in `store/index.ts`, which pushes the logged-out state to every tab and slice. Components detect the change and stop polling protected endpoints. |
| `hydrateAuthFromStorage` | _Reads `localStorage`_ | Ensures freshly mounted tabs see the persisted tokens before any other slice dispatches its loaders. |
| `fetchCurrentUserProfile` | `GET /user` | Updates `auth.displayName`/`isAdmin`. Admin-only components watch these flags to show/hide tabs. |
| `updateCurrentUserProfile` | `PATCH /user` | Writes profile fields and refreshes persisted auth snapshot so other tabs update via storage events. |
| `deleteAccount` | `DELETE /user` | Clears auth state (same cascade as `logout`). `Dashboard` detects the missing auth context and stops dispatching Today/Stats loaders. |

**Implicit dependency:** `store/index.ts` subscribes to `authService.subscribe`, so any mutation of `localStorage` (even outside Redux) dispatches `setAuthState`, ensuring other slices always see the latest credentials.

## `activitiesSlice`

| Thunk | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `loadActivities` | `GET /activities` (two calls: active subset + `?all=true`) | Hydrates in-memory + offline snapshots used by Today when offline. |
| `createActivity` | `POST /add_activity` (idempotent, supports offline queue) | After success it dispatches `loadActivities()`, `loadToday(date)`, and `loadEntries(current filters)` to guarantee new activities appear in Today lists and affect stats immediately. |
| `updateActivityDetails` | `PUT /activities/:id` | Same cascade as `createActivity` so category/goal updates propagate; backend also updates entries in-place. |
| `activateActivity` | `PATCH /activities/:id/activate` | Dispatches `loadActivities`, `loadToday`, `loadEntries` so reactivated activities rejoin Today and analytics snapshots. |
| `deactivateActivity` | `PATCH /activities/:id/deactivate` | Same cascade but ensures Today drops the activity after the next refresh. |
| `removeActivity` | `DELETE /activities/:id` | Same cascade; additionally clears `selectedActivityId` if it pointed at the removed record. |

**Bidirectional dependency:** `createActivity` and friends read `entries.filters` from `getState()` so they can call `loadEntries` with the user’s active filters. This keeps the Entries table consistent but means entries/activities slices are interdependent.

## `entriesSlice` (Entries + Today + Stats)

| Thunk | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `loadEntries` | `GET /entries` with filters from state (start/end dates, activity/category, limit/offset) | Pure fetch; populates `entries.items`. |
| `loadToday` | `GET /today?date=YYYY-MM-DD` | Writes to `today.rows` and `today.date`. Falls back to offline snapshots if the request fails. |
| `loadStats` | `GET /stats/progress?date=YYYY-MM-DD` | Updates `stats.snapshot`. Because the backend caches responses per user/date, this thunk is also called whenever activities or entries mutate. |
| `saveDirtyTodayRows` | Multiple `POST /add_entry` calls (one per dirty row) through the offline queue | On success it saves the latest Today snapshot, then dispatches `loadToday(date)`, `loadEntries(filters)`, and `loadStats({ date: stats.date })` to force cache invalidation and UI refresh. |
| `deleteEntry` | `DELETE /entries/:id` | After success dispatches `loadStats` (same date) and `loadToday(today.date)` so both the daily sheet and dashboard recalc. |
| `importEntries` | `POST /import_csv` | Re-fetches `loadEntries`, `loadStats`, and `loadToday` to reflect the batch import. |
| `finalizeToday` | `POST /finalize_day` | Returns the affected date, after which components commonly refresh Today manually; no automatic cascade inside the thunk. |

**Implicit dependency:** `Dashboard.jsx` dispatches `loadActivities`, `loadEntries`, `loadToday`, and `loadStats` on mount (and when the active tab changes back to Today), so the entries slice constantly responds to auth or routing changes.

## `backupSlice`

| Thunk | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `loadBackupStatus` | `GET /backup/status` | Seeds scheduler info, last run timestamp, and the ZIP list. |
| `toggleBackup` | `POST /backup/toggle` with `{ enabled?, interval_minutes? }` | After a successful toggle the returned status replaces local state; Admin Settings reuses the slice so no additional dispatches are needed. |
| `runBackupNow` | `POST /backup/run` followed by `GET /backup/status` | Stores the created backup metadata (`lastBackup`) and refreshes the backup list; UI uses this to re-render download buttons. |

**Cascade reminder:** UI handlers (e.g., `BackupPanel`) call `loadBackupStatus()` when the slice status is `idle` so toggles/run actions always reflect the server’s latest scheduler row.

## `adminSlice`

| Thunk | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `loadHealth` | `GET /healthz` | Populates `admin.health` and records `lastFetched` for manual refresh buttons. |
| `loadMetrics` | `GET /metrics?format=json` | Similar to `loadHealth`; the Admin Health tab polls this periodically. |
| `loadActivityLogs` | `GET /logs/activity` (supports query params) | Pure fetch; no extra cascading. |
| `loadRuntimeLogs` | `GET /logs/runtime` | Pure fetch. |
| `loadWearableSummary` | Parallel `GET /wearable/summary` + `GET /wearable/raw` | Combines both payloads for the wearable inspector card. |

**Implicit dependency:** The Admin NightMotion view does **not** use `adminSlice`; it talks directly to `nightMotionSlice` (see below). Health + Metrics loaders are frequently fired right after `loadBackupStatus` so operators see both scheduler state and runtime state at once.

## `nightMotionSlice`

`nightMotionSlice` mostly manages local form/status state, but its helper thunks are worth noting:

| Thunk / action | Endpoint(s) | Downstream cascades / notes |
| --- | --- | --- |
| `startStream` (AppThunk) | _No direct API call_ | Sets status to `starting` and clears errors; the `NightMotion.tsx` component then executes a `fetch(getStreamProxyUrl(...))` call to `GET /api/stream-proxy`, piping JWT + CSRF headers from `authService`. Once frames arrive it dispatches `setStatus("active")`. |
| `stopStream` | _No direct API call_ | Resets status to `idle`; the component aborts the inflight fetch, revokes object URLs, and clears the MJPEG preview. |
| `setField`, `setStatus`, `setError`, `resetState` | _Local only_ | Used by the component + localStorage hydration to persist credentials. |

**Implicit dependency:** Because the component controls the actual fetch, NightMotion relies on `authSlice` for tokens and on `BackupSlice`/`AdminSlice` to keep admin-only routing accessible.

## Cross-slice Cascades Summary

- **Activity mutations → Today/Entries/Stats:** Every activity mutation thunk (`createActivity`, `updateActivityDetails`, `activateActivity`, `deactivateActivity`, `removeActivity`) dispatches `loadActivities`, `loadToday`, and `loadEntries`. This keeps stats denominators aligned with the new activity set.
- **Today edits/imports → Stats refresh:** `saveDirtyTodayRows`, `deleteEntry`, and `importEntries` all re-dispatch `loadStats` so the backend cache (`stats` bucket) invalidates quickly.
- **Backup actions → Scheduler refresh:** `runBackupNow` always follows up with `loadBackupStatus` to ensure the schedule + backup list match whatever `BackupManager` wrote.
- **Auth changes → global reload:** The `Dashboard` effect (listening to `authSlice`) is the source of truth for bootstrapping `loadActivities`/`loadEntries`/`loadToday`/`loadStats`. Clearing auth (logout/delete account) therefore halts all polling and wipes offline snapshots after the next `setAuthState` dispatch.

Understanding these dependencies is critical when adding new thunks: always review which slices need fresh data and piggyback on the existing cascades rather than issuing ad hoc fetches inside components.
