# Layering Checklist for PR Reviews

Use this list to flag violations before merging. If any item fails, request changes or add a CI lint rule.

1. **Components never perform network calls.** All HTTP traffic goes through Redux thunks / `api.js` helpers (NightMotion MJPEG stream is the only exception).
2. **Components do not touch `localStorage`/`sessionStorage` directly.** Use the existing services (`authService`, snapshots) or Redux state.
3. **Components do not import services, controllers, or the global store.** Only `useSelector`/`useDispatch` are allowed.
4. **Redux slices never import other slices or components.** Cross-slice coordination occurs via dispatched actions/thunks only.
5. **Thunks only call helpers wired to `apiClient`.** No hard-coded URLs or stray `fetch`/`axios` calls.
6. **Auth logic stays in `authService`/`apiClient`.** No new modules should reimplement header injection or token parsing.
7. **Flask controllers do not embed business logic.** They validate, enforce rate limits, call services/db helpers, invalidate caches, and build responses—nothing more.
8. **Controllers avoid raw SQL when a service already handles it.** Prefer calling `backup_manager`, ETL helpers, or `db_utils` wrappers rather than duplicating queries.
9. **Services never import Flask `request`, `Response`, or blueprints.** They return plain Python data and raise domain errors only.
10. **Models remain pure.** No business rules, logging, or dependency on controllers/services.
11. **Infrastructure utilities (cache, metrics, rate limits) are only used server-side.** No client imports.
12. **NightMotion exception stays isolated.** Any new direct `fetch` must be justified and documented like the existing stream proxy.
13. **No circular imports across layers.** CI should run `pydeps`/`madge` (or equivalent) to detect cycles.
14. **Tests mock at layer boundaries.** Frontend tests mock API helpers; backend tests mock services instead of hitting real DB/network.
15. **Documentation updated when exceptions occur.** Any intentional rule break must be recorded in `layering-rules.md` and cross-referenced.
