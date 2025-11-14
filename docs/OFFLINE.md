# Offline Capture & Sync

Mosaic now supports offline-first workflows for the **Today** dashboard and **Activities** management screens. When the device loses connectivity, mutations are written to IndexedDB and replayed automatically once the app detects that the network is back.

## Storage Layout

- `pendingWrites` – FIFO queue of POST/PUT/PATCH/DELETE requests that could not be sent. Each record stores the endpoint, method, payload, and generated `X-Idempotency-Key`.
- `snapshots` – cached copies of `Today` rows per date plus the full Activities lists. Read thunks fall back to these snapshots whenever a fetch fails, so UI state persists across reloads while offline.

The IndexedDB wrapper (`src/offline/db.ts`) automatically degrades to an in-memory map when running unit tests or on browsers without IndexedDB support.

## Sync Loop

`initOfflineSync(store)` (started from `store/index.ts`) wires browser `online/offline` events, polls every 60 s, and drives `drainPendingWrites()` from `src/offline/queue.ts`. The queue:

1. Attempts to send the request immediately when online.
2. Queues the payload if `navigator.onLine === false` or Axios throws a network error.
3. Replays records sequentially, adding `X-Overwrite-Existing: 1` on 409/422 responses so local data wins.
4. Uses the stored `X-Idempotency-Key` for every retry so the backend can safely deduplicate.

The offline Redux slice (`offlineSlice.ts`) tracks `online`, `syncing`, and `pendingCount`. `Dashboard.jsx` shows these states (“Offline”, “Syncing…”, “Pending n”) to help users understand when queued writes are still waiting.

## Frontend Touchpoints

- `entriesSlice.ts`: `loadToday` saves/replays snapshots; `saveDirtyTodayRows` routes each entry update through the offline queue and updates the snapshot after local saves.
- `activitiesSlice.ts`: all mutations call `submitOfflineMutation`. When enqueued, the slice updates the local snapshot (and Redux state) immediately so Activities reflect offline edits. `loadActivities` stores and reuses snapshots automatically.
- `src/__tests__/offline_sync.test.ts`: Jest coverage for the queue, including conflict retries with the overwrite flag.

## Backend Idempotency

`/add_entry` and `/add_activity` now accept `X-Idempotency-Key` (cached for 10 minutes per user) and `X-Overwrite-Existing`. The Flask layer short-circuits exact replays and, for activities, allows forced updates instead of returning 409. See `tests/test_idempotent_writes.py` for coverage.

## Operational Notes

- Keep HTTPS enabled—service workers and IndexedDB require secure origins in modern browsers.
- To inspect queued operations, open DevTools → Application → IndexedDB → `mosaic_offline`.
- If you change the queue schema, bump the version number in `offline/db.ts` so upgrades run cleanly.
