# Daily Log – 2024-10-29

- Date: 2024-10-29
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 29_10_mosaic.md

## Notes (raw import)

1. Validace vstupů
Ruční kontroly vstupů byly nahrazeny vrstvou validace postavenou na Pydanticu, která je napojena na všechny Flask endpointy. V `security.py` vznikly pomocné validátory s jednotným formátem chyb a ochranami pro jednotlivé operace. Schémata v `schemas.py` pokrývají všechny typy vstupů – záznamy, aktivity, CSV import i uzavření dne – s vlastními kontrolami formátů, rozsahů a logiky cílů. Flask routy nyní používají tyto validátory místo ručních JSON kontrol. Testy ověřují správnost i chybové scénáře, dokumentace popisuje novou validační strategii a Pydantic je přidán mezi závislosti.

DONE by Codex

Replaced the ad‑hoc input checks with a Pydantic backed validation layer and wired it through the Flask endpoints.

- Validation helpers in mosaic_prototype/backend/security.py (lines 94-153) now wrap Pydantic models, reuse consistent error formatting, and expose new entry/activity/finalize/import guards.
- The concrete schemas live in mosaic_prototype/backend/schemas.py (lines 8-237), covering entries, activity create/update, CSV uploads, and finalize-day payloads with custom validators for formats, ranges, and derived goal logic.
- Flask routes delegate to the new helpers (mosaic_prototype/backend/app.py (lines 639-705)), removing manual JSON/file checks for /finalize_day and /import_csv.
- Added targeted unit coverage in mosaic_prototype/backend/tests/test_validation.py (lines 17-100) to exercise valid/invalid paths and computed-goal behaviour.
- Documented the validation strategy and rationale in mosaic_prototype/API_DOCS.md (lines 292-306), and pinned pydantic in mosaic_prototype/backend/requirements.txt (lines 1-5) for deployment.

2. Transakce v SQLite
Backend nyní používá jednotný transakční kontext pro SQLite, takže každý zápisový endpoint provádí změny atomicky – buď se celý commitne, nebo vrátí zpět. CSV import běží ve stejné transakci, takže při chybě nezmění databázi. Přidána byla podpora SQLAlchemy a Flask-Migrate s CLI nástroji pro inicializaci a migrace. Testy byly upraveny na konfigurovatelnou databázovou cestu a přibyl test ověřující rollback při chybě importu. Dokumentace a závislosti byly doplněny pro nový migrační systém.

DONE by Codex

- Introduced a shared SQLite transaction context and applied it across write endpoints so each route atomically commits or rolls back (mosaic_prototype/backend/app.py (line 189), mosaic_prototype/backend/app.py (line 300), mosaic_prototype/backend/app.py (line 436)).
- Wrapped the CSV importer in the same transactional guard and removed ad-hoc commits to make failed imports leave the database untouched (mosaic_prototype/backend/import_data.py (line 87), mosaic_prototype/backend/import_data.py (line 143)).
- Added SQLAlchemy/Flask-Migrate scaffolding with reusable extensions, model metadata, and a CLI helper for init/migrate/upgrade workflows (mosaic_prototype/backend/extensions.py (line 1), mosaic_prototype/backend/models.py (line 4), mosaic_prototype/backend/manage.py (line 24)).
- Aligned the test harness with the reconfigurable DB path and added a regression test that simulates an import failure to assert the rollback behaviour (mosaic_prototype/backend/tests/conftest.py (line 6), mosaic_prototype/backend/tests/test_transactions.py (line 10)).
- Documented the migration workflow and pinned the new dependencies required for transaction-aware migrations (README.md (line 20), mosaic_prototype/backend/requirements.txt (line 1)).

3. Standardizace chybových odpovědí
Backend má nyní jednotný systém chyb: všechny chyby vracejí stejný formát s kódem, zprávou a detaily. V `security.py` přibyl pomocný modul `error_response`, který rozšiřuje `ValidationError` o kód, stav a podrobnosti, a Pydantic validátory nyní vracejí strukturované informace. `app.py` obsahuje globální middleware pro všechny typy chyb, sjednocuje stavové kódy a nahrazuje jednotlivé větve `jsonify({"error": ...})` společným řešením. Testy byly upraveny, aby ověřovaly nový formát pro všechny druhy chyb, a dokumentace popisuje nový chybový kontrakt.

DONE by Codex

Standardized the backend’s error handling so every failure now returns the same structured envelope and consistent status codes.

- mosaic_prototype/backend/security.py (lines 41-198) introduces the shared error_response helper, enriches ValidationError with code/status/details, and teaches the Pydantic validators to surface structured detail data (e.g., missing field lists).
- mosaic_prototype/backend/app.py (lines 56-250) adds global error middleware for ValidationError, HTTPException, and unexpected exceptions, maps status codes to canonical error codes, and replaces all per-endpoint jsonify({"error": ...}) branches with the unified helper.
- mosaic_prototype/backend/tests/test_api.py (lines 48-227) and mosaic_prototype/backend/tests/test_validation.py (lines 33-101) update existing assertions and add new coverage to confirm the standardized payload (code, message, details) is emitted for validation, rate limit, not-found, and query errors.
- Docs now reflect the new contract so clients know what to expect (mosaic_prototype/API_DOCS.md (lines 291-316), README.md (lines 18-21)).

4. JWT autentizace a základní bezpečnostní vrstvy
Backend nyní plně používá JWT autentizaci a CSRF ochranu: nové endpointy `/register` a `/login` vydávají tokeny a middleware hlídá všechny chráněné cesty. Validace i rate limiting byly rozšířeny o podporu přihlášených uživatelů a vracejí strukturované chyby. Databáze získala tabulku `users`, přibyla knihovna PyJWT pro práci s tokeny. Testy nyní ověřují přihlášení, správnou reakci na chybějící/nesprávné tokeny a limity přihlášení. Dokumentace byla doplněna o popis nového autentizačního procesu, potřebné hlavičky a aktuální limity.

DONE by Codex

- Added JWT-based auth and CSRF enforcement: new /register + /login flows issue bearer/CSRF tokens and a global middleware now guards all non-public routes (mosaic_prototype/backend/app.py (line 288), mosaic_prototype/backend/app.py (line 312), mosaic_prototype/backend/app.py (line 352)).
- Extended validation/rate limiting helpers to cover auth payloads, surface structured error details, and prefer user-scoped limits when a token is present (mosaic_prototype/backend/security.py (line 43), mosaic_prototype/backend/security.py (line 79), mosaic_prototype/backend/security.py (line 207), mosaic_prototype/backend/schemas.py (line 206)).
- Persist users and bring in signing support: SQLite schema + models gained a users table, and PyJWT was added for token handling (mosaic_prototype/database/schema.sql (line 1), mosaic_prototype/backend/models.py (line 1), mosaic_prototype/backend/requirements.txt (line 1)).
- Updated the integration suite to authenticate every request, assert CSRF/401 behaviours, and verify login rate limiting (mosaic_prototype/backend/tests/test_api.py (line 8), mosaic_prototype/backend/tests/test_api.py (line 164), mosaic_prototype/backend/tests/test_validation.py (line 33)).
- Refreshed the docs with the new auth workflow, header requirements, and rate-limit entries (README.md (line 18), mosaic_prototype/API_DOCS.md (line 12)).

5. Enable full login workflow between frontend and backend according to the new API contract.
Codex doplnil kompletní přihlášení na frontend: přidal službu `authService` pro ukládání tokenů, odhlášení a zobrazení chyb, a upravil Axios klienta tak, aby automaticky přidával potřebné hlavičky a přesměrovával na `/login`, když vyprší relace. Aplikace je nyní obalená v `AuthProvider` s React Routerem – dashboard je dostupný jen po přihlášení přes `PrivateRoute`. Přibyly komponenty `LoginForm`, `RegisterForm` a `LogoutButton` s českými hláškami. `App.jsx` bylo přepracováno pro směrování a kontext, `api.js` používá nový Axios klient, všechny části UI (aktivity, záznamy, statistiky apod.) zobrazují chybová hlášení jednotně. Byly doplněny potřebné utility, balíčky (`axios`, `react-router-dom`) a dokumentace s testy. Výsledné chování: uživatel se přihlásí nebo zaregistruje, tokeny se uloží do localStorage, autentizované stránky fungují automaticky a při vypršení relace dojde k odhlášení a přesměrování s informací o důvodu.

DONE by Codex

- Added full JWT/CSRF-aware auth stack on the frontend: introduced authService for token storage, logout, and friendly error mapping, plus an Axios apiClient with interceptors that attach headers, surface backend errors, and kick users to /login when a session lapses.
- Wrapped the app in AuthProvider + React Router, gated the original dashboard behind a PrivateRoute, and created dedicated LoginForm, RegisterForm, and LogoutButton components with clear Czech error messaging.
- Reworked App.jsx to provide routing, reuse the existing dashboard within an authenticated shell, and surface logout; adjusted top-level entry to include router/context.
- Refactored api.js to use the shared Axios client, keeping all existing endpoint helpers intact while automatically carrying auth headers and parsing responses.
- Propagated user-friendly error formatting across UI components (activities, entries, stats, today view, CSV import) via a formatError utility so backend { error: { code, message } } responses show the right string.
- Added new config/util files, introduced storage-backed auth state notifications, and updated package.json with axios and react-router-dom.
- Extended docs/tests: new auth workflow documented in README/API docs, and existing frontend tests (after running in .venv) now pass with authentication enabled.

App behavior: users hit /login or /register, receive tokens stored in localStorage, and authenticated routes automatically keep headers in sync; logout clears everything and redirects to login, while unauthorized or expired tokens trigger a graceful redirect and message.

6. Optimalizace dotazů a paginace
Backend nyní podporuje stránkování pomocí `limit` a `offset` pro endpointy `/entries`, `/activities`, `/stats/progress` a `/today` (výchozí 100/0, maximum 500). Pro statistiky se SQL dotazy zkracují přímo a agregace kategorií se ořezávají po zpracování. Databázové schéma bylo rozšířeno o indexy na sloupcích `entries(date)`, `entries(activity)`, `entries(activity_category)` a `activities(category)` pro rychlejší dotazy. Dokumentace popisuje nové parametry i důvody indexace a testy ověřují správné fungování stránkování i reakce na chybné vstupy.

DONE by Codex

- Added a shared parse_pagination() helper and wired limit/offset support into /entries, /activities, /stats/progress, and /today (defaults 100/0; cap 500). For stats, the SQL is trimmed directly for the activity view and category aggregates are sliced post-processing.
- Extended the backend schema provisioning (schema.sql, ensure_schema, importer) with indexes on entries(date), entries(activity), entries(activity_category), and activities(category)—added after validating plans with EXPLAIN QUERY PLAN.
- Documented the new query parameters and index rationale in README/API docs, noting the pagination defaults and indexed columns.
- Expanded the backend test suite to cover pagination behaviour and invalid inputs across entries, activities, today, and stats.

7. Caching pro často volané endpointy
Backend má nyní lehkou vnitřní cache pro nejčastěji čtené endpointy. V `app.py` přibyla vláknově bezpečná TTL cache s pomocnými funkcemi (`cache_get`, `cache_set`, `invalidate_cache`) a konstantami pro dobu platnosti. Endpoint `/today` ukládá výsledky podle data, limitu a offsetu asi na 60 s, `/stats/progress` na 5 minut podle celého dotazu. Všechny zápisové operace (přidání, mazání, úpravy aktivit, import, uzavření dne) cache automaticky zneplatňují. Testy ověřují, že se data po změně okamžitě obnoví, a dokumentace popisuje chování cache, TTL i invalidaci. Nepřibyly žádné nové závislosti.

DONE by Codex

Implemented lightweight in-process caching for the hottest read endpoints and wired it into the data-changing flows.

- Added a threadsafe TTL cache to backend/app.py with helper utilities (cache_get, cache_set, invalidate_cache) and constants (TODAY_CACHE_TTL, STATS_CACHE_TTL). /today now caches each (date, limit, offset) slice for ~60 s, and /stats/progress caches grouped responses for ~5 min using full query parameters as the cache key.
- All relevant mutating routes (/add_entry, deletes, activity CRUD, /finalize_day, CSV import) now invalidate the cache prefixes so clients don’t see stale data after writes.
- Expanded the API test suite to cover pagination plus two new cases (test_today_cache_invalidation, test_stats_cache_invalidation) ensuring cache hits are refreshed immediately when data changes.
- Documented the caching behavior and existing indexes in README/API docs, noting the short TTLs and auto-invalidation.
- Kept dependencies unchanged (no external cache library needed) and ensured README highlights the new optimization.

8. Unit a integrační testy
Testy nyní plně pokrývají autentizaci i cache – ověřují registraci, přihlášení, chybné údaje, neplatné a expirované tokeny i funkci cache s posunutým časem. Do repozitáře byla přidána GitHub Actions pipeline, která při každém pushi nebo pull requestu nainstaluje závislosti, spustí pytest a sestaví React aplikaci. README zmiňuje, že testy a buildy běží automaticky.

Done by Codex

- Added full auth/caching unit coverage in mosaic_prototype/backend/tests/test_auth.py, including register/login flow, bad credentials, invalid/expired tokens, and direct cache helper verification with monkeypatched time.
- Documented the new test coverage and automation, and introduced a GitHub Actions workflow (.github/workflows/tests.yml) that installs backend/frontend deps, runs pytest, and builds the React app on every push/PR.
- README now notes that CI runs automatically.

Backend byl vyčištěn a sjednocen: cache pomocné funkce jsou nyní centralizované v `app.py` s vláknově bezpečným úložištěm a všechny zápisové operace nad entries a activities automaticky zneplatňují cache pro `/today` a `/stats`. Přidány byly jednotkové testy pro auth a cache (`tests/test_auth.py`), které doplňují existující integrační sadu; problém s testem cache byl opraven fixací časového okna. Všechny potřebné Python závislosti jsou již uvedeny v `requirements.txt`, stejně jako všechny frontendové balíčky v `package.json` — bez chybějících či nadbytečných položek.