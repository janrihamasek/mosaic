# Mosaic AI Coding Agent Instructions

## Project Overview

Mosaic is a multi-tenant activity tracking platform with a React/TypeScript frontend, Flask backend, and PostgreSQL database. Users log daily activities with qualitative scores (0-5), track streaks, and review analytics. Admins have observability tools for backups, metrics, and health monitoring.

## Critical Architecture Rules

### Layering (ENFORCED BY CI)

**Dependency Direction:** UI → Redux → API Layer → Controllers → Services → Models → Database

**Core Rules:**
- Components dispatch Redux actions/thunks only—never call `fetch`/`axios` directly (except NightMotion stream proxy, a documented exception)
- Redux slices **never import other slices**—use listeners middleware (`dailyTrackingListeners.ts`) for cross-slice coordination
- All API calls go through `frontend/src/api.js` helpers that wrap `apiClient.js`
- Backend controllers call service modules; services return data structures (never Flask `Response` objects)
- Models contain only SQLAlchemy definitions—no business logic

**Verification:** Run `python scripts/check-layering.py` before commits. CI enforces this.

### Redux Data Flow Pattern

After mutations (create/update/delete activities/entries), refresh dependent slices via listeners:
```typescript
// listeners/dailyTrackingListeners.ts orchestrates cascades:
createActivity → loadActivities() + loadToday() + loadEntries() + loadStats()
saveDirtyTodayRows → loadToday() + loadEntries() + loadStats()
```
**Never dispatch other slices' thunks directly from a slice**—use the event bus (`services/mutations/events.ts`).

### Authentication & Multi-Tenancy

- JWT tokens in `localStorage` with `user_id`, `display_name`, `is_admin` claims
- Every backend query automatically filters by `current_user_id()` from JWT unless admin
- Admin endpoints require `@require_admin` decorator plus optional `require_api_key()`
- Cross-tab auth sync via `authService.subscribe()` in `store/index.ts`

## Essential Commands

### Backend Development
```bash
# Start Docker Compose stack (dev + prod backends, postgres)
docker compose up -d

# Apply migrations (inside container)
docker compose exec mosaic_backend_dev flask db upgrade

# Run tests with isolated test database
./scripts/run_pytest.sh

# Generate new migration
cd backend && python manage.py migrate -m "description"

# CLI user data management
docker compose exec mosaic_backend_dev python manage.py assign-user-data <username>
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies to backend on :5000)
npm start

# Run tests (Jest + React Testing Library)
npm test

# Linting (enforces --max-warnings=0 in CI)
npm run lint

# Build for production
npm run build
```

### Database Access
- PostgreSQL exposed on `localhost:5433`
- Dev DB: `mosaic_dev` / `mosaic:mosaic_password`
- Schema defined in `backend/database/schema.sql`, managed by Flask-Migrate

## Key Patterns & Conventions

### Backend

**Validation:** Use Pydantic schemas in `schemas.py` and `schemas_wearable.py`. All controller endpoints validate with `validate_*` helpers before processing.

**Error Responses:** Return standardized JSON via `error_response(message, code, status_code)` from `security.py`. Never return bare `abort()`.

**Transactions:** Wrap writes in `db_utils.transactional_connection()`. Services in `services/common.py` use `with_write_db_transaction` decorator.

**Caching:** Use `cache_get(key, ttl)` / `cache_set(key, value, ttl)` / `invalidate_cache(pattern)` from `cache_manager.py`. Controllers invalidate after mutations. **WARNING:** Cache keys don't namespace by `user_id` yet—multi-tenant leakage risk.

**Observability:**
- Structured logging via `structlog` (JSON to stdout)
- Request metrics in-memory at `/metrics` (text or `?format=json`)
- Health checks at `/healthz` and `flask health` CLI command
- All documented in `docs/LOGGING.md` and `docs/METRICS.md`

**Rate Limiting:** Applied via `limit_request(key, limit, window)` from `rate_limiter.py`. Check `PUBLIC_ENDPOINTS` list in `app.py` for exemptions.

### Frontend

**Component Structure:**
- Pages in `src/pages/` (Today, Activities, Stats, Entries, Admin)
- Shared components in `src/components/`
- Forms use `react-hook-form` with validation in form components

**State Management:**
- Slices: `authSlice`, `entriesSlice`, `activitiesSlice`, `backupSlice`, `adminSlice`, `nightMotionSlice`, `wearableSlice`
- Selectors co-located with slices
- Async thunks for all API calls
- Listeners middleware in `store/listeners/` handles refresh cascades

**Styling:** Shared design system in `src/styles/common.js`. Dark mode baseline. Use `useBreakpoints` hook for responsive layouts.

**Offline Support:** Managed by `offline/syncManager.ts` and `offlineSlice`. Today data cached in IndexedDB via `offline/todayStorage.ts`.

**TypeScript Migration:** Core slices and types in TypeScript (`.ts`, `.tsx`). Legacy components still JSX. Prefer TypeScript for new code.

## Testing Strategy

### Backend Tests (Pytest)
- Location: `backend/tests/`
- Run via: `./scripts/run_pytest.sh` (provisions isolated `mosaic_test` DB)
- Key test files:
  - `test_api.py` - endpoint integration tests
  - `test_auth.py` - JWT, profile, multi-tenant isolation
  - `test_transactions.py` - rollback semantics
  - `test_cache_namespace.py` - cache isolation verification
  - `test_metrics.py`, `test_health.py` - observability

**Fixtures:** `conftest.py` provides `client`, `auth_headers`, `admin_headers`

### Frontend Tests (Jest + RTL)
- Location: `frontend/src/__tests__/`
- Config: `jest.config.js`, `jest.setup.ts`
- Run: `npm test`
- Coverage: Login forms, slice logic, utility functions
- **Gaps:** Admin/Backup/NightMotion components lack coverage

### CI/CD
- Workflows in `.github/workflows/`: `ci.yml`, `tests.yml`, `backend-tests.yml`, `staging.yml`
- Enforces: ESLint (`--max-warnings=0`), Jest, Pytest, frontend build
- Staging workflow runs against `.env.staging` with PostgreSQL 15 service

## Analytics Formulas

Stats calculations defined in `docs/METRICS.md`. Key concepts:
- **Completion ratio:** `R_d = min(V_d / G_total, 1)` where `V_d` = sum of values, `G_total` = sum of goals
- **Active day:** Day where `R_d ≥ 0.5`
- **Streaks:** Consecutive active days
- **Category baselines:** Per-category rolling averages over 7/30 days

Backend endpoint: `GET /stats/progress` returns pre-calculated metrics matching formulas exactly.

## Common Gotchas

1. **Cache Contamination:** `/today` and `/stats` cache keys omit `user_id`. Risk of cross-tenant leakage in multi-user deployments. Workaround: namespace keys or use single-user-per-process.

2. **Redux Circular Imports:** Never import slice reducers/thunks across slices. Use listeners middleware or dispatch via `store.dispatch` from event handlers.

3. **Backend SQL in Services:** Services should call repository functions, not use raw `conn.execute`. Check `scripts/check-layering.py` allowlist if needed.

4. **Rate Limit State:** In-memory rate limiter resets on process restart. No distributed rate limiting yet.

5. **Metrics Persistence:** `/metrics` counters are per-process in-memory. Resets erase history. No Prometheus scraper configured.

6. **TypeScript/JS Mix:** When editing existing JS files that have TypeScript equivalents, consider migrating or maintaining consistency with typed interfaces in `src/types/`.

## File Navigation

**Entry Points:**
- Backend: `backend/app.py`
- Frontend: `frontend/src/index.tsx` → `App.jsx` → `Dashboard.jsx`
- Redux store: `frontend/src/store/index.ts`

**Key Backend Modules:**
- Controllers: `backend/controllers/` (handle HTTP requests)
- Services: `backend/services/` (business logic)
- Repositories: `backend/repositories/` (data access)
- Models: `backend/models.py`
- Validation: `backend/security.py`, `backend/schemas.py`
- Infrastructure: `backend/infra/` (cache, metrics, rate limiting)

**Key Frontend Modules:**
- Pages: `frontend/src/pages/`
- Store slices: `frontend/src/store/`
- API layer: `frontend/src/api.js`, `frontend/src/apiClient.js`
- Auth: `frontend/src/services/authService.js`
- Offline: `frontend/src/offline/`

**Documentation:**
- Architecture rules: `docs/architecture/layering-rules.md`, `redux-flow.md`
- API reference: `docs/API_DOCS.md`
- Observability: `docs/LOGGING.md`, `docs/METRICS.md`
- Frontend specs: `docs/frontend_pages/` (Today.md, Stats.md, etc.)
- Current state: `mosaic_project_current_state.md`

## Admin Tooling

Admin UI (Admin tab):
- **User:** Profile management, account deletion
- **Settings:** Backup automation, CSV import/export
- **Health:** `/healthz` + `/metrics` dashboard with auto-refresh
- **NightMotion:** MJPEG stream proxy tools (admin-only)

CLI Commands (`backend/manage.py`):
- `assign-user-data <username>` - reassign orphaned activities/entries and optionally grant admin
- `ingest-wearable <user> <file>` - batch import wearable data
- `agg-rebuild <user>` - recalculate daily aggregates

## Current Development Focus

**In Progress:**
- T1 Daily Loop UX (see `scripts/251127_frontend_T1-daily-loop-ux.md`)
- TypeScript migration for remaining JS components
- Test coverage expansion for Admin/Backup/NightMotion

**Known Issues:**
- Cache namespace missing `user_id` (tenant isolation risk)
- Metrics state is transient (no long-term retention)
- Admin audit logging not implemented
- Mobile responsive layouts incomplete for Admin views

**Next Steps:**
- Namespace caches by `user_id`
- Add Prometheus exporter for persistent metrics
- Complete TypeScript migration
- Expand Jest/RTL coverage to >80%

## When Making Changes

1. **Check layering rules first:** Does this violate UI → Redux → API → Controllers → Services?
2. **Update listeners:** If adding a mutation, add refresh logic to `dailyTrackingListeners.ts`
3. **Invalidate caches:** Call `invalidate_cache()` in controllers after mutations
4. **Update docs:** Modify `docs/METRICS.md` if changing analytics formulas, `docs/API_DOCS.md` for new endpoints
5. **Add tests:** Backend tests in `backend/tests/`, frontend in `frontend/src/__tests__/`
6. **Run CI locally:** `./scripts/run_pytest.sh` and `npm run lint && npm test` before pushing

## Getting Help

- Architecture questions: See `docs/architecture/`
- API contracts: `docs/API_DOCS.md`
- Metrics formulas: `docs/METRICS.md`
- Redux flow: `docs/architecture/redux-flow.md`
- Frontend UX specs: `docs/frontend_pages/`
