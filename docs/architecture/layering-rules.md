# Mosaic Layering Rules

Mosaic’s architecture follows a strict layered structure to keep the React frontend, Redux state management, HTTP client, Flask controllers, service modules, SQLAlchemy models, and infrastructure utilities decoupled. This document defines each layer, allowed dependency directions, and forbidden shortcuts.

## Layer Overview

| Layer | Scope & Examples | Responsibilities |
| --- | --- | --- |
| **UI (React components)** | `Dashboard.jsx`, Today/Stats/Entries pages, Admin panels, NightMotion | Render views, dispatch Redux actions, subscribe to slice state. No direct network or business logic. |
| **State (Redux slices & thunks)** | `activitiesSlice`, `entriesSlice`, `authSlice`, `backupSlice`, `adminSlice`, `nightMotionSlice`, `wearableSlice` | Hold client state, expose reducers, define async thunks that orchestrate API calls and cross-slice refreshes. |
| **API Layer (Axios helpers)** | `frontend/src/api.js`, `apiClient.js`, `services/authService.js`, `services/userService.js` | Encapsulate REST calls, inject auth headers/API keys, parse responses/errors. No UI logic. |
| **Controller Layer (Flask endpoints)** | `backend/app.py`, blueprints in `routes/` | Validate payloads, enforce auth/rate limits, call services, manage cache invalidations, build responses. |
| **Service Layer (domain logic)** | `backup_manager.py`, `wearable_service.py`, `import_data.py`, stream proxy helpers | Implement long-running jobs, data transforms, external integrations (FFmpeg, filesystem). Return Python objects/data only. |
| **Model Layer (SQLAlchemy models)** | `models.py`, Alembic migrations | Define persistence schema, relationships, and DB-level rules. No business logic or HTTP awareness. |
| **Infrastructure / Utilities** | Cache (`cache_get/set`), metrics (`structlog`, `/metrics`), rate limiting, auth helpers, BackupManager scheduler thread | Cross-cutting concerns shared by controllers/services; must not leak into UI/Redux. |

## Allowed Dependency Directions

```
UI → Redux State → API Layer → Controller Layer → Service Layer → Model Layer → Database
                                           ↘ Infrastructure utilities (cache, metrics, rate limits)
```

- **UI → Redux:** Components may dispatch actions/thunks and read selectors. They should not import other components’ state or global stores outside `useDispatch`/`useSelector`.
- **Redux → API:** Thunks call `api.js` helpers (which use `apiClient`). Reducers stay pure and never import other slices directly; cross-slice coordination happens via dispatched actions.
- **API → Controllers:** `apiClient` constructs HTTP requests; no component or slice should use `fetch`/`axios` directly except the NightMotion stream (documented exception).
- **Controllers → Services/Infra:** Endpoints orchestrate validation, rate-limits, cache, and then call service modules. Controllers may touch SQL directly via `db_utils` or delegate to services, but they must not embed long-running business logic.
- **Services → Models:** Services can run SQLAlchemy queries, file I/O, or external processes but never import Flask request/response objects.
- **Models → DB:** Models only interact with the database layer—no awareness of controllers, services, or UI.

## Forbidden Dependencies & Constraints

| Rule | Rationale |
| --- | --- |
| Components must not call `fetch`/`axios` directly (NightMotion stream is the only exception). | Keeps all IO inside thunks for caching and error handling. |
| Components must not import service modules, controllers, or `apiClient`. | Prevents business logic in the view layer. |
| Redux slices must not import other slices/reducers. Inter-slice coordination happens via dispatched thunks/actions only. | Avoids tangled state graphs and circular imports. |
| Thunks must go through `api.js` helpers; no raw URL strings in slices. | Centralises base URLs, headers, and error events in `apiClient`. |
| Flask controllers must not call React/Redux code. | Backend stays standalone and testable. |
| Service modules return data structures only; they do not create Flask responses or touch `request`/`Response`. | Controllers remain the only layer that knows about HTTP. |
| Controllers invalidate caches via `invalidate_cache`—UI/Redux must not attempt cache management. | Prevents stale or inconsistent server caches. |
| Models never import controllers/services. | Maintains clean ORM definitions. |
| Infrastructure utilities (cache, metrics, rate limits) are only consumed by controllers/services. UI/Redux must not touch them. | Keeps cross-cutting concerns server-side.

## Examples

- **Valid:** `Activities.jsx` dispatches `createActivity` → thunk calls `api.addActivity()` → Axios sends `POST /add_activity` → controller validates, updates DB, invalidates cache, responds → thunk dispatches `loadActivities`, `loadToday`, `loadEntries`.
- **Invalid:** `Today.jsx` calling `apiClient.get("/today")` directly. Should dispatch `loadToday` instead so offline snapshots and cascades run.
- **Valid:** `NightMotion.tsx` dispatches `startStream` (sets slice state) then runs a manual `fetch` to `/api/stream-proxy` because MJPEG streaming needs a raw stream. This exception is documented and isolated.
- **Invalid:** `BackupManager` returning `Response` objects or reading `flask.request`. It must return Python dicts so `/backup/*` controllers can serialize them.
- **Valid:** `BackupPanel.jsx` uses `backupSlice` thunks to toggle backups; the thunks call `/backup/toggle` through `api.js`, keeping UI free of HTTP code.
- **Invalid:** `wearable_service.py` importing `NightMotionSlice` or any frontend code.

By enforcing these rules, refactors stay localized, CI can detect illegal imports, and each layer remains testable in isolation.
