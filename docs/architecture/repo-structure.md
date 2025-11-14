# Proposed Repository Structure

To reinforce Mosaic’s layering rules and make navigation easier, reorganize the repo into clear frontend/backed layer folders with shared documentation. Each section below lists the proposed tree, highlighted responsibilities, and how current files map over.

## Backend (`backend/`)
```
backend/
  controllers/
    __init__.py
    auth_controller.py
    activities_controller.py
    entries_controller.py
    stats_controller.py
    admin_controller.py
    backup_controller.py
    nightmotion_controller.py
    wearable_controller.py
  services/
    __init__.py
    activities_service.py
    entries_service.py
    stats_service.py
    backup_service.py  # wraps BackupManager
    nightmotion_service.py
    wearable_service.py
    import_service.py
  repositories/
    __init__.py
    activities_repo.py
    entries_repo.py
    users_repo.py
    wearable_repo.py
  models/
    __init__.py
    models.py
    migrations/
  infra/
    cache_manager.py
    rate_limit.py
    auth.py
    metrics.py
    logging.py
  cli/
    manage.py
    scripts/
  tests/
    unit/
      controllers/
      services/
      infra/
    integration/
      api/
      db/
```
**Motivation**: Controllers stay HTTP-specific, services handle orchestration, repositories encapsulate SQL, and infra houses shared utilities (cache, metrics, auth). Tests mirror the folder structure.

**Mapping notes**:
- Existing `app.py` splits into controller modules + an `app_factory.py` wiring them together.
- `backup_manager.py` moves under `services/backup_service.py` plus `infra/cache_manager.py` for cache invalidations.
- `wearable_service.py` moves to `services/wearable_service.py`; ETL logic stays there while DB access moves to `repositories/wearable_repo.py`.
- Rate-limit/auth helpers from `security.py` migrate into `infra/`.
- Tests currently under `backend/tests/` split between `tests/unit` (mocking repos/services) and `tests/integration` (hitting the API or DB).

## Frontend (`frontend/src/`)
```
src/
  components/
    shared/
    dashboard/
    admin/
    nightMotion/
  pages/
    Today/
    Stats/
    Entries/
    Admin/
  store/
    slices/
      activitiesSlice.ts
      entriesSlice.ts
      authSlice.ts
      backupSlice.ts
      adminSlice.ts
      nightMotionSlice.ts
      wearableSlice.ts
    listeners/
    middleware/
    index.ts
  services/
    api/
      apiClient.js
      api.ts
    auth/
      authService.js
      userService.js
    mutations/
      activities.ts
      entries.ts
    nightMotion/
      streamService.ts
  utils/
    formatting/
    hooks/
    offline/
  styles/
  docs/
```
**Motivation**: Separates dumb components, routed pages, Redux state, and service modules. `services/mutations` will host the refactored orchestration helpers. `store/listeners` houses cross-slice refresh logic. Utilities (offline snapshots, hooks) sit under `utils/`.

**Mapping notes**:
- Current `frontend/src/components` content splits between `components` (pure UI) and `pages` (layout + routing). E.g., `Dashboard.jsx` → `pages/Dashboard/Dashboard.jsx`.
- Thunks remain in `store/slices`, but cross-slice listeners move to `store/listeners`.
- `api.js` and `apiClient.js` relocate under `services/api/`.
- `offline/queue` and `offline/snapshots` move under `utils/offline/` to keep services thin.

## Shared Docs & Tooling
```
docs/
  architecture/
    layering-rules.md
    layering-checklist.md
    layering-refactor-plan.md
    dependency-map.md
    dependency-graph.md
    dependency-matrix.md
    backend-call-tree.md
    repo-structure.md
```
**Motivation**: Centralize architecture docs so future changes update all references consistently. Link these files from README and PR templates.

## Benefits
- **Layer clarity**: File paths communicate ownership (e.g., `controllers/entries_controller.py` clearly belongs to the HTTP layer).
- **Focused tests**: Mirroring the structure under `tests/` encourages writing layer-specific suites.
- **Refactor-friendly**: Services/repositories encapsulate logic, making it easier to share mutations between web UI, CLI scripts, or future mobile clients.
- **CI enforcement**: Static analysis (madge/pydeps) can target directory boundaries and fail PRs that cross layers.

Adopting this structure can be done incrementally—start by introducing the new folders and migrating one controller/service pair at a time while updating imports.
