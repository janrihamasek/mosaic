# Layering Refactor Plan

Mosaic already enforces strict layering rules, but several legacy areas still blur the boundaries. This plan enumerates current violations, defines the desired target state, and proposes a phased migration roadmap suitable for incremental Codex tasks.

## Current Violations & Pain Points

| Area | Issue |
| --- | --- |
| **Redux orchestration inside slices** | `activitiesSlice` and `entriesSlice` thunks dispatch multiple other thunks (e.g., `createActivity` → `loadActivities` + `loadToday` + `loadEntries`). This couples slices tightly and makes it hard to reuse mutations from other contexts (CLI, background jobs). |
| **Controllers handling DB logic directly** | Several Flask endpoints (`/entries`, `/add_entry`, `/activities`, `/stats/progress`) build SQL queries inline instead of delegating to service modules or repositories. This mixes HTTP and persistence logic. |
| **Cache invalidations scattered** | Controllers call `invalidate_cache` manually, but there is no central cache manager. Some services (BackupManager) implicitly rely on controllers to clean caches, leading to missed invalidations when reused elsewhere. |
| **Infra logic mixed with controllers** | Rate limits, auth checks, and metrics hooks live in `app.py`, making tests heavy and preventing reuse in blueprints. |
| **NightMotion exception unmanaged** | The direct `fetch` in `NightMotion.tsx` bypasses the standard API layer; it is documented but lacks a dedicated service wrapper for future extensions. |
| **Cross-layer knowledge in services** | `backup_manager.py` knows about Flask config and writes responses the controllers expect. ETL services log via `structlog` but also handle HTTP-specific errors. |
| **Tests coupled to implementation details** | Jest and Pytest suites mock specific slices/controllers instead of layer contracts (e.g., mocking `apiClient` or service interfaces), making refactors risky.

## Target State

1. **Redux layer exposes mutation services**: Activity/entry mutations live in dedicated modules (e.g., `frontend/src/services/mutations.ts`) that return promises. Slices dispatch a single thunk per mutation, and components subscribe to lineage events (e.g., `mutationCompleted`) to decide which loaders to rerun.
2. **Controllers delegate to repositories/services**: Each endpoint calls a service function (e.g., `entries_service.list_entries(scope, filters)`) responsible for DB access, cache coordination, and domain logic. Controllers only validate, call the service, and stringify responses.
3. **Central cache manager**: Add `backend/cache_manager.py` with helpers for invalidating cache buckets (`today`, `stats`, etc.). Services call it directly, so cache invalidations occur even when services are reused outside HTTP.
4. **Shared infra utilities are modular**: Rate limiting, auth enforcement, and metrics become decorators/mixins importable by blueprints, reducing `app.py` weight.
5. **NightMotion service wrapper**: Introduce a frontend service (e.g., `nightMotionService`) that encapsulates the fetch/stream logic. Components call it through Redux actions, keeping the exception isolated yet structured.
6. **Service guardrails**: Backend services stop reading Flask config directly; instead controllers pass in needed settings (paths, TTLs). Services return typed objects (e.g., dataclasses) rather than raw dicts.
7. **Layer-focused tests**: Add test helpers so frontend tests mock the mutation service, backend controller tests mock repositories, and service tests interact with the DB/infrastructure in isolation.

## Phased Migration Plan

Each phase can be implemented as an independent Codex task to minimize risk.

### Phase 1 – Documentation & CI
1. Wire `layering-checklist.md` into PR templates and CI lint (e.g., run `madge` for frontend, `pydeps` for backend) to catch obvious violations.
2. Add TODO markers in slices/controllers highlighting upcoming refactors to align team expectations.

### Phase 2 – Redux Mutation Services
1. Create `frontend/src/services/mutations/activities.ts` and `entries.ts` exporting functions like `createActivity(payload): Promise`.
2. Update thunks to call these services and emit a generic `mutationCompleted({ resource: "activity", action: "create" })` action.
3. Replace hard-coded cross-slice refresh chains with middleware/listeners that react to `mutationCompleted` events (e.g., `entries/listeners.ts` triggers `loadEntries` when `resource === "entry"`).
4. Write Jest tests for the new services and listeners to ensure cascades stay intact.

### Phase 3 – Backend Service Layer Extraction
1. Create modules such as `services/activities.py`, `services/entries.py`, `services/stats.py`, each exposing read/write functions that accept `user_scope` data.
2. Move SQL queries from controllers into these services. Controllers now look like:
   ```python
   @app.post("/add_entry")
   def add_entry():
       payload = validate_entry_payload(request.get_json() or {})
       result = entries_service.add_entry(current_user, payload)
       return jsonify(result.payload), result.status
   ```
3. Ensure services call `cache_manager.invalidate("today")` rather than controllers.
4. Add unit tests for services (mocking `db_transaction`, etc.) and thin controller tests verifying that services receive the right arguments.

### Phase 4 – Cache & Infra Modules
1. Introduce `backend/cache_manager.py` wrapping `cache_get/set/invalidate`. Update services to use it; controllers stop touching cache directly.
2. Extract rate limiting/auth/metrics decorators into `infra/` modules; import them in `app.py` and blueprints.
3. Update `/healthz` and `/metrics` to use the new cache manager so infra checks remain consistent.

### Phase 5 – NightMotion & Backup Isolation
1. Add `frontend/src/services/nightMotionStream.ts` to encapsulate the `fetch(getStreamProxyUrl(...))` pipeline. Redux actions call this service, keeping component code minimal.
2. On the backend, move stream proxy helpers into `services/nightmotion.py` so controllers only handle HTTP wiring.
3. For `BackupManager`, extract response-friendly serializers (so controllers do not rely on dict shapes) and move config loading outside the class. Provide service functions like `get_backup_status()` and `run_backup(initiated_by)` returning typed objects.

### Phase 6 – Testing & Follow-up
1. Update Jest tests to mock mutation services and listen for `mutationCompleted` events instead of spying on slices.
2. Update Pytest suites to mock service modules when testing controllers, and to exercise cache manager behavior in isolation.
3. Run lint/dependency analyzers to confirm no forbidden imports remain. Document any exceptions in `layering-rules.md` and `dependency-matrix.md`.

## Considerations for Tests & Tooling
- **Frontend**: Provide a test utility for dispatching `mutationCompleted` and asserting listener behavior. Ensure integration tests still run actual thunks against mock API responses.
- **Backend**: Add fixtures for cache manager, rate limiter, and services so tests can assert they are invoked without hitting Postgres.
- **CI**: Gradually tighten lint rules (e.g., forbid components from importing `apiClient`, enforce `isort` sections) once the refactor phases land.

Following this phased plan keeps changes manageable, documents intentional exceptions, and ultimately aligns the codebase with the layering rules enforced by CI and human reviewers.
