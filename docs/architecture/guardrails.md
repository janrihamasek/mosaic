# Layering Guardrails

Layering rules only work when CI enforces them. This document describes the linting and tooling configuration required to keep Mosaic’s frontend and backend within their allowed dependency directions.

## Allowed Dependency Directions

| From \ To | UI Components | Redux Slices | Thunks/Services | API Layer (`api.js`, `apiClient.js`) | Controllers | Services/Repos | Models | Infra (cache, metrics, auth) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UI Components | — | ✔ | ✔ (dispatch only) | ✖ | ✖ | ✖ | ✖ | ✖ |
| Redux Slices | ✖ | — | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ |
| Thunks/Frontend Services | ✖ | ✖ | — | ✔ | ✖ | ✖ | ✖ | ✖ |
| API Layer | ✖ | ✖ | ✖ | — | ✔ | ✖ | ✖ | ✖ |
| Controllers | ✖ | ✖ | ✖ | ✖ | — | ✔ | ✔ | ✔ |
| Services/Repos | ✖ | ✖ | ✖ | ✖ | ✖ | — | ✔ | ✔ |
| Models | ✖ | ✖ | ✖ | ✖ | ✖ | ✖ | — | ✖ |
| Infra | ✖ | ✖ | ✖ | ✖ | ✖ | ✔ | ✔ | — |

## Frontend Guardrails (ESLint)

1. **Import path groups** – configure `eslint-plugin-boundaries` or `eslint-plugin-import` with the following zones:
   - `ui` (components/pages) may only import from `ui`, `utils`, or `store` entry points.
   - `store` (slices) may import from `store`, `services`, `utils` but never from `ui` or other slices.
   - `services` may import from `services` and `utils` only.
2. **No direct `apiClient` usage** – rule: files under `components/` or `store/slices/` cannot import `services/api/apiClient`. Only helpers in `services/api/` can import it.
3. **No cross-slice imports** – forbid patterns like `import { loadEntries } from "../entriesSlice"` inside another slice. Instead, dispatch actions via listeners.
4. **NightMotion exception** – allow `services/nightMotion/streamService.ts` to import `getStreamProxyUrl` directly but ensure ESLint rule ignores only that folder.
5. **Ban `localStorage`/`sessionStorage` in components** – use ESLint no-restricted-globals to restrict storage access to service modules.
6. **Circular dependency check** – add `madge --circular` (or `depcruise`) in CI to ensure new imports do not introduce cycles across layers.

## Backend Guardrails (Flake8 / Custom Checks)

1. **Module boundaries** – use `flake8-import-order` or `flake8-bugbear` with custom plugin to assert:
   - Files under `controllers/` must not import from `repositories/` or `models/` directly—only from `services/` or `infra/`.
   - Files under `services/` may import `repositories/`, `models/`, and `infra/` but never `controllers/`.
   - `models/` and `infra/` never import from `controllers/` or `services/`.
2. **Custom checker** – implement a simple script (`scripts/check_layering.py`) that walks Python files and enforces the above rules using AST or regex. Run it in CI after flake8.
3. **No Flask objects in services** – add flake8 plugin rule to flag `from flask import request, Response` within `services/` directory.
4. **Cache access** – only `services/` and `infra/` can import `cache_manager`; controllers should call services instead. Enforce via the custom script.
5. **DB access** – if controllers import `db_utils` or SQLAlchemy models directly, the checker should fail unless the module is explicitly whitelisted.

## CI Integration

- **Frontend**: extend `npm run lint` to include `eslint --max-warnings=0` and a `madge src --circular --extensions ts,tsx,js,jsx`. Block merges if either fails.
- **Backend**: update `scripts/run_pytest.sh` (or GitHub Actions workflow) to run `flake8` + `python scripts/check_layering.py` before tests.
- **Documentation**: require that any deliberate exception (e.g., new service needing direct fetch) updates `layering-rules.md` and `dependency-matrix.md`.

Together, these guardrails provide automated feedback whenever new code violates the architecture boundaries established in the layering rules.
