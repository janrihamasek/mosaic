# Mosaic Project – Current State Report

## 1. Project Overview

### Purpose and Goals
Mosaic is a full-stack activity tracking platform that helps individuals log daily rituals, measure streaks, and analyze progress toward personal goals. Users capture activities with qualitative notes, review day-level summaries, and monitor long-term performance. The platform emphasises low-friction data entry, rich validation, and near-real-time feedback through aggregated statistics.

### Technology Stack
- **Frontend:** React 18 with modern hooks, React Router v6, Redux Toolkit for state management, Axios for HTTP, react-hook-form for form orchestration, and a custom dark-mode design system defined in `styles/common.js`.
- **Backend:** Flask 3 application organised in `app.py`, supported by Flask-CORS, Flask-SQLAlchemy, Flask-Migrate, PyJWT for authentication, and Pydantic for request validation.
- **Database:** PostgreSQL accessed via SQLAlchemy models. Schema evolution is handled through Flask-Migrate migrations; legacy SQLite bootstrap scripts remain only for historical reference.
- **Tooling & Infrastructure:** Jest is not yet configured, but backend tests run via Pytest with coverage reporting. GitHub Actions workflows (`.github/workflows/*.yml`) run backend unit tests, provide coverage artifacts, and build the frontend bundle. The frontend build relies on Create React App, with TypeScript configured in `allowJs` mode and `noEmit` to keep the workspace lint-only.

### Development History and Direction
Recent development (see `docs/changelog/2025-10-29_backend_frontend_summary.md`) delivered:
- A Pydantic-backed validation layer replacing ad-hoc JSON checks.
- Transactional guards for all mutating endpoints with consistent error envelopes.
- Full JWT + CSRF authentication, frontend token storage, and CSRF-aware Axios interceptors.
- Unified dashboard statistics pipeline (`/stats/progress`) consolidating 30-day metrics with cache-aware invalidation.
- React forms migrated to react-hook-form for richer validation.
- New reusable loading and error states plus centralized toast notifications.

The current trajectory focuses on resilience, consistency across form UX, cache-aware analytics, and preparing for broader integrations (CSV import pipelines, future wearable device hooks).

## 2. System Architecture

### Repository Layout
```
mosaic_prototype/
├── backend/                # Flask application, domain models, validation, CLI tools
│   ├── app.py              # Route definitions, caching, authentication, rate limiting
│   ├── security.py         # Validation helpers, error wrappers, rate limiter
│   ├── schemas.py          # Pydantic models per payload
│   ├── models.py           # SQLAlchemy models (Activity, Entry, User)
│   ├── extensions.py       # SQLAlchemy & migration factories
│   ├── import_data.py      # CSV import routine
│   ├── tests/              # Pytest suites for API, auth, validation, transactions
│   └── requirements.txt    # Python dependency lock
├── frontend/               # React SPA
│   ├── src/
│   │   ├── App.jsx         # Dashboard shell, routes, notification handling
│   │   ├── apiClient.js    # Axios instance with auth headers & error interceptor
│   │   ├── api.js          # Declarative API wrappers
│   │   ├── components/     # UI building blocks (forms, tables, loaders)
│   │   ├── store/          # Redux Toolkit slices (auth, activities, entries)
│   │   ├── services/       # Auth persistence, friendly messages
│   │   ├── styles/         # Dark mode palette, spacing tokens
│   │   └── utils/          # Animation helpers, utilities
│   ├── public/             # CRA static assets
│   └── package.json        # Frontend dependencies and scripts
├── backend/migrations/     # Alembic migrations (Flask-Migrate)
├── docs/                   # API documentation, changelog entries
└── mosaic_project_current_state.md
```

### Layer Interactions
- **React ⇄ Flask:** The frontend uses `apiClient.js` (Axios) to call Flask endpoints. The request interceptor injects `Authorization` and CSRF headers via `authService`. Responses feed Redux thunks; errors funnel through a global event (`mosaic-api-error`) consumed by the dashboard to display toasts.
- **Redux as integration layer:** Redux thunks (e.g., `loadEntries`, `createActivity`) coordinate async calls and trigger secondary effects such as cache invalidations (by refetch). Components subscribe via selectors to minimise re-rendering.
- **Persistent state:** Auth tokens and expiry metadata live in localStorage through `authService`. Redux initialises slices by hydrating persistent auth and filter preferences (e.g., `entries.filters`).
- **Database access:** Flask routes use SQLAlchemy with PostgreSQL via lightweight wrappers in `db_utils.py`. The helper preserves the existing positional-parameter SQL while routing through the SQLAlchemy engine; `db_transaction()` manages commit/rollback boundaries.

### Redux Store Structure
- **`authSlice`**: Tracks authentication status, tokens, and async lifecycle states (`login`, `register`, `logout`). Thunks wrap `authService` calls and propagate friendly error messages.
- **`activitiesSlice`**: Maintains active/all activity lists, mutation status, and selectors for detail modals. Thunks wrap `fetchActivities`, `addActivity`, etc., and coordinate refreshes of related slices (`loadToday`, `loadEntries`).
- **`entriesSlice`**: Holds paginated entry lists, filters, `/today` data (rows, dirty cache, auto-save state), the stats dashboard snapshot (single payload + anchor date), and import status. Thunks orchestrate entries, stats, and today pipelines, ensuring caches stay in sync.
- Store composition occurs in `store/index.js` which configures Redux Toolkit with serialisation-aware middleware (defaults) and exports typed hooks.

### Primary Data Flows
1. **User Authentication:** `LoginForm` validates credentials client-side, dispatches `auth/login`, receives JWT + CSRF, persists tokens, and updates headers. Private routes in `App.jsx` guard dashboard access.
2. **Daily Tracking:** `Today.jsx` fetches `/today` via `loadToday`, renders entries, and schedules auto-saves through `saveDirtyTodayRows` (posting to `/add_entry`). Mutations invalidate caches in Flask, prompting Redux to refresh.
3. **Activity Management:** `ActivityForm` collects metadata, dispatches `createActivity` (`POST /add_activity`), and reloads activities/entries/today slices. `ActivityTable` toggles activation/deletion via RESTful endpoints.
4. **Statistics:** `Stats.jsx` dispatches `loadStats` to `/stats/progress`, receiving a unified snapshot (goal completion, streak, distribution, fulfilment, polarity, consistency) that powers the refreshed dashboard widgets.
5. **CSV Import:** `CsvImportButton` validates files client-side, dispatches `importEntries`, and shows toast results summarising create/update/skip counts.

## 3. Data Model and API

### Database Schema
- **`activities`**: `id`, `name`, `category`, `goal`, `description`, `active`, `frequency_per_day`, `frequency_per_week`, `deactivated_at`. Indices on `category`.
- **`entries`**: `id`, `date`, `activity`, `description`, `value`, `note`, denormalised `activity_category` and `activity_goal`. Indices across `date`, `activity`, and `activity_category`.
- **`users`**: `id`, `username`, `password_hash`, `created_at`.

Schema management: database changes are captured via Flask-Migrate/Alembic migrations in `backend/migrations`; runtime schema patching logic has been removed in favour of explicit upgrades.

### API Surface
- **Authentication:** `POST /register`, `POST /login` yield JWT + CSRF tokens. Tokens include per-session CSRF embedded in payload; CSRF enforcement occurs on all unsafe methods.
- **Entries:** `GET /entries` (paginated & filterable), `POST /add_entry` (upsert by `(date, activity)`), `DELETE /entries/<id>`. `POST /finalize_day` marks a day as locked and clears caches.
- **Activities:** `GET /activities` (with `?all=true` handles archived items), `POST /add_activity`, `PUT /activities/<id>`, `PATCH /activities/<id>/activate|deactivate`, `DELETE /activities/<id>`.
- **Analytics:** `GET /today` returns denormalised daily rows, `GET /stats/progress` delivers the 30-day dashboard snapshot (goal completion, streaks, distribution, fulfilment), `/import_csv` handles bulk ingestion.
- **Infrastructure:** `GET /healthz` (if present) & root route verifying DB path.

### Validation, Auth, and Rate Limiting
- **Validation:** `security.py` routes JSON to Pydantic schemas (`ActivityCreatePayload`, `EntryPayload`, etc.), normalises values (trimmed strings, numeric conversions), and attaches computed properties (`goal`).
- **Auth:** JWT signed with `MOSAIC_JWT_SECRET`, expiration controlled by `MOSAIC_JWT_EXP_MINUTES`. Tokens validated per request; expired tokens trigger refresh workflows in frontend and backend.
- **Rate Limiting:** Memory-based limiter keyed by route and user/IP, configured via `app.config["RATE_LIMITS"]`. Responses provide `too_many_requests`.
- **CSRF:** Each token issues a `csrf_token`; Flask checks request headers for `X-CSRF-Token` matching payload.

### Caching and Invalidation
- `_cache_storage` in `app.py` stores TTL-bound results keyed by prefix (e.g., `"today::2025-10-29::100::0"`). `/today` cache TTL = 60 seconds; `/stats` TTL = 300 seconds. Mutations call `invalidate_cache("today")` or `invalidate_cache("stats")` to ensure coherency post-write.

## 4. Frontend (React)

### Component Landscape
- **`App.jsx`**: Routes login/register vs. authenticated dashboard; listens for global API error events to trigger toasts.
- **`Dashboard` (within `App.jsx`)**: Controls tabbed navigation (`Today`, `Activities`, `Stats`, `Entries`), orchestrates data bootstrapping, and hosts `Notification` toasts, `LogoutButton`, and detail modals.
- **Input Forms**: `LoginForm`, `RegisterForm`, `ActivityForm`, `EntryForm` all migrate to react-hook-form with inline validation, accessibility attributes, and disabled submit states until valid.
- **Visualisation Components**: `Today` handles daily entry grids with autosave; `Stats` now renders a dashboard of meters, charts, and consistency bars fed by the unified snapshot; `ActivityTable`/`EntryTable` present sortable lists augmented with new `Loading` and `ErrorState` wrappers.
- **Utility Components**: `CsvImportButton` (file picker with validation), `Notification` (toast styling), `Loading` (spinner with fade-in), `ErrorState` (retry banner).

### State and Validation Patterns
- Redux thunks orchestrate server calls and cache invalidations. React-hook-form enforces client-side trimming, regex validation (email), numeric ranges, and cross-field checks (confirm password, date ranges).
- The dark theme is consistent: `styles/common.js` centralises card, input, and button styling. `Loading`/`ErrorState` reuse animation keyframes injected once via `utils/animations.js`.
- Navigation persists active tab in `localStorage` to provide continuity across reloads.

### Daily Summaries & Activities
- `Today` fetches the user’s focus day, calculates progress ratios, and animates bar charts. Auto-save triggers `saveDirtyTodayRows` after debounce, giving user feedback (`Changes auto-saved`).
- `ActivityForm` computes average daily goal server-side but also derives preview `avgGoalPerDay` for UI display. `ActivityTable` handles activation toggles and detail viewing (tied into `ActivityDetail`).
- `Stats` surfaces the snapshot metrics (today’s completion, streak badge, pie distribution, 7/30-day trend line, polarity split, consistency bars) with shared `Loading`/`ErrorState` states and a refresh action.

## 5. Testing and Quality

### Backend Test Coverage
- **`test_auth.py`**: Registration/login lifecycle, invalid credentials, expired tokens, cache helper behaviour.
- **`test_api.py`**: End-to-end activity CRUD, entry creation/deletion, pagination, CSV import scenarios, finalise-day flows, rate limits.
- **`test_validation.py`**: Verifies Pydantic schema enforcement (frequency ranges, required fields, CSV presence).
- **`test_transactions.py`**: Ensures transaction rollback semantics and atomic operations when errors occur mid-batch.
- Tests run under Pytest with coverage (`pytest --cov=app --cov-report=xml`) in CI.

### Frontend Quality Practices
- Frontend currently relies on manual testing and the CRA build as a smoke check (`npm run build --if-present`). React component tests are not yet introduced; however, form validation is deterministic via react-hook-form.
- Manual test plans accompany recent features (e.g., react-hook-form integration, loading/error states) outlining behaviour to confirm before release.

### Continuous Integration
- **`tests.yml`**: Dual job workflow running backend pytest and frontend build on pushes/PRs to `main`.
- **`backend-tests.yml`**: Narrow workflow re-running backend tests when backend files change, capturing coverage reports.
- CI ensures dependencies install cleanly on Python 3.11/3.12 and Node 18, acting as regression safety net.

## 6. Current Development Status

### Latest Enhancements
- **Form UX Modernisation:** All primary forms now use react-hook-form with inline messages, accessible aria attributes, and disabled submit buttons until valid.
- **Unified Loading/Error Handling:** New `Loading` and `ErrorState` components provide animated feedback and retry affordances, adopted across `/today`, `/entries`, and `/activities`.
- **Global Error Notifications:** Axios response interceptor emits `mosaic-api-error`; `Dashboard` listens and surfaces toasts, consolidating error UX.
- **CSV Import Hardening:** Client-side validation prevents accidental uploads (extension/size checks) before dispatching `importEntries`.
- **Caching & Invalidation:** Backend caches (`today`, `stats`) tied to state invalidation, improving responsiveness while avoiding stale reads.

### Open Work and TODOs
- **Frontend Automated Tests:** No unit/integration tests yet; high-value targets include form validation, Redux thunks, and component rendering.
- **Stats Snapshot Testing:** The refreshed `Stats.jsx` surface lacks automated tests (visual or snapshot) to guard the new charts and ratios.
- **Type Safety:** The project is JavaScript-only; adopting TypeScript or PropTypes would reduce regressions.
- **Mobile Responsiveness:** Current layout is desktop centric; responsive breakpoints and mobile gestures remain unimplemented.
- **Advanced Analytics:** Present stats focus on goal ratios; product roadmap mentions richer analytics and wearable integrations but no code yet.

### Planned/Proposed Directions
- Stabilise API contracts and add migration tooling before scaling beyond SQLite (e.g., to PostgreSQL).
- Extend CI to include frontend lint/test suites and deploy previews.
- Implement server-side pagination for tables within UI (currently limited to backend defaults).
- Explore WebSocket or SSE for live-tracking scenarios once multi-device sync becomes necessary.

## 7. Summary and Recommendations

### Strengths
- **Robust Validation & Security:** Pydantic schemas, JWT + CSRF, structured error envelopes, and rate limiting provide a safe API surface.
- **Consistent UX:** React-hook-form, shared styling, and global notifications ensure uniform behaviour across forms and tables.
- **Caching & Performance:** TTL caches on heavy read endpoints plus targeted invalidation deliver quick responses without stale data risks.
- **Automated Testing & CI:** Backend tests cover core flows with coverage reporting; GitHub Actions ensure regressions are caught early.

### Weaknesses
- **Limited Frontend Test Coverage:** Reliance on manual testing increases regression risk, especially with the growing component surface.
- **SQLite Concurrency Constraints:** The single-file database works for prototypes but will bottleneck under higher concurrency without migration planning.
- **Analytics Accessibility Gaps:** The new stats widgets lack dedicated accessible descriptions and keyboard interactions for charts, leaving screen-reader support incomplete.
- **Documentation Duplication:** API docs live in Markdown, but there is no generated schema or OpenAPI spec to keep backend and frontend fully synchronised.

### Recommendations
1. **Testing Investment:** Introduce Jest + React Testing Library to cover form validation, global error handling, and Redux thunks. Pair with Cypress (or Playwright) smoke tests for mission-critical flows.
2. **Database Evolution:** Prepare a migration plan (Flask-Migrate scripts, staging environment) for moving to PostgreSQL as data volume grows. Define archival strategies for `entries`.
3. **Analytics Expansion:** Layer accessibility metadata onto the new widgets, explore predictive/compare-to-target metrics, and consider chart libraries for maintainable rendering and tooltips.
4. **Mobile & Accessibility Enhancements:** Introduce responsive breakpoints, keyboard shortcuts, and screen reader audits to broaden usability.
5. **DevEx Improvements:** Add linting (ESLint, Prettier) and TypeScript migration roadmap to improve developer ergonomics and catch issues earlier.
6. **Integration Roadmap:** Design interfaces for wearable or external data ingestion, potentially via scheduled imports plus extended CSV schema support.

---

This document summarises Mosaic’s current capabilities and technical posture. The project is production-ready for small teams, with strong backend validation and coherent frontend UX. Addressing the outlined gaps—particularly automated frontend testing, database scalability, and richer analytics—will position Mosaic for broader adoption and future integrations.
