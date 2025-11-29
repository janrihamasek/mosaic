# Daily Log – 2024-11-02

- Date: 2024-11-02
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 2_11_mosaic.md

## Notes (raw import)

# bugfixing - github actions
1. 251102_frontend_tests_textencoder_polyfill
Goal: Ensure Jest frontend tests (especially NightMotion.test.tsx) pass in Node CI where TextEncoder/TextDecoder are undefined.  

DONE
Added a Jest polyfill so Node’s test runtime now exposes TextEncoder/TextDecoder via frontend/src/jest.setup.ts, with Jest configured to load it before each test (frontend/jest.config.js). Updated the NightMotion streaming tests to use a synthetic ReadableStream helper that keeps the MJPEG stream alive, listens for aborts, and closes cleanly; snapshot coverage remains intact (frontend/src/__tests__/NightMotion.test.tsx). All tests pass with npm test -- --runInBand.

2. 251102_frontend_tests_eslint_fixes

Goal: Fix remaining ESLint and Jest warnings causing GitHub Actions failure. 

DONE
- frontend/src/jest.setup.ts: moved the util import and added setupTests import at the top so globals are wired before module body code.
- frontend/src/__tests__/NightMotion.test.tsx: dropped the unused streamControls assignment to satisfy ESLint.

# Fáze 2 – Datová vrstva a analytika
1. 251102_backend_data_export_csvjson
Goal: Implement data export endpoints and scripts for user-accessible CSV/JSON downloads.  

DONE
- Introduced shared export helpers and pagination-aware fetch logic to serve user-authenticated CSV/JSON downloads with proper headers (mosaic_prototype/backend/app.py (line 203), mosaic_prototype/backend/app.py (line 752)).
- Added pytest coverage that seeds sample data, asserts auth enforcement, and validates CSV/JSON structure plus pagination metadata (mosaic_prototype/backend/tests/test_export.py (line 8)).
- Extended the frontend API client with filename parsing and blob-handling helpers to retrieve export files over authenticated requests (mosaic_prototype/frontend/src/api.js (line 13)).
- Added export controls to the Entries view that trigger CSV/JSON downloads with user feedback and disabled states while transfers are in progress (mosaic_prototype/frontend/src/components/EntryTable.jsx (line 32)).

2. 251102_backend_csv_import_validation
Goal: Enhance CSV import routine with duplicate and incomplete record detection.  

DONE
- Hardened CSV import to validate rows with Pydantic, normalize dates, guard against missing fields, and emit a per-row audit while tracking created/updated/skipped counts and ignoring in-file duplicates (mosaic_prototype/backend/import_data.py (line 165)).
- Introduced CSVImportRow schema that enforces required fields, cleans text, converts metrics, and sets sane defaults for optional frequency metadata (mosaic_prototype/backend/schemas.py (line 221)).
- Added pytest coverage for duplicate detection, missing field rejection, and mixed batches that combine updates with new inserts (mosaic_prototype/backend/tests/test_import_validation.py (line 18)).

2. 251102_backend_backup_manager
Goal: Implement an in-app backup system allowing automatic periodic database dumps (JSON/CSV) that can be toggled and downloaded by the user.  

DONE
Implemented scheduled backup system with API endpoints and UI controls anchored to the Entries page.

- **Backend** Introduced BackupSettings persistence and schema creation so backup preferences survive restarts (mosaic_prototype/backend/models.py (line 52), mosaic_prototype/backend/app.py (line 96), mosaic_prototype/backend/import_data.py (line 96), mosaic_prototype/database/schema.sql (line 31)).
- **Services** Added BackupManager with JSON/CSV/ZIP dumps, persistence, and scheduler plus new /backup/* routes for status, manual runs, toggles, and downloads (mosaic_prototype/backend/backup_manager.py (line 11), mosaic_prototype/backend/app.py (line 771)).
- **Frontend** Wired Redux backup slice, API helpers, and the BackupPanel UI with interval control, run-now, and download actions inside the Entries section (mosaic_prototype/frontend/src/store/backupSlice.js (line 1), mosaic_prototype/frontend/src/store/index.ts (line 11), mosaic_prototype/frontend/src/api.js (line 140), mosaic_prototype/frontend/src/components/BackupPanel.jsx (line 1), mosaic_prototype/frontend/src/Dashboard.jsx (line 10)).
- **Tests** Added integration coverage for backup creation, toggling, persistence, and download (mosaic_prototype/backend/tests/test_backup_manager.py (line 1)).

# autosave_issues 
251102_frontend_today_autosave_fix
Goal: Fix delayed autosave behavior on the Today screen to make saving immediate upon user interaction.  

DONE
Value selection now saves immediately, and notes auto-save on Enter or after a short inactivity delay to remove the previous 5 s lag.

- mosaic_prototype/frontend/src/components/Today.jsx (lines 31-110) renamed the debounce constant and made the delay note-specific, while syncing dirty refs and firing an immediate save when a value actually changes.
- mosaic_prototype/frontend/src/components/Today.jsx (lines 113-154) kept note edits constrained to 100 chars, scheduled the 5 s inactivity save, and added an Enter key handler that syncs state and flushes pending rows without creating duplicate requests.
- mosaic_prototype/frontend/src/components/Today.jsx (lines 284-355) wired the new key handler into both layouts and updated the placeholder copy to guide users to press Enter to save notes.

# user documentation
created in mosaik_prototype/docs/USER_DOCS.md

# Fáze 3 – Backend, migrace a DevOps 
251102_backend_postgresql_replacement
Goal: Replace SQLite with PostgreSQL as the backend database without migrating any existing data.  

DONE
PostgreSQL is now the runtime database: the Flask app boots from DATABASE_URL, retires the SQLite bootstrap, and routes raw SQL through SQLAlchemy helpers so existing queries keep working.

- mosaic_prototype/backend/app.py (line 50) introduces _resolve_database_uri, removes the SQLite path management, swaps get_db_connection/db_transaction over to SQLAlchemy connections, and updates / to report the active URI.
- mosaic_prototype/backend/db_utils.py (line 10) adds a thin adapter that converts ? placeholders and exposes transactional/non-transactional connections for reuse across the codebase.
- mosaic_prototype/backend/backup_manager.py (line 83) now operates inside an app context with SQLAlchemy connections, stores last_run as a timestamp, and rewrites toggling/status logic for Postgres.
- mosaic_prototype/backend/import_data.py (line 1) rewrites CSV import to run on the ORM session (activities entries upserted atomically), adds a CLI wrapper, and drops sqlite-specific schema checks.
- mosaic_prototype/backend/models.py (line 42) updates BackupSettings.last_run to DateTime(timezone=True) so ORM aligns with the new schema.
- Fresh Flask-Migrate scaffolding lives under mosaic_prototype/backend/migrations/ (see env.py (line 1) and versions/20241115_000001_initial_schema.py (line 1)) to create the activities, entries, users, and backup_settings tables with the right defaults and indexes.
- Postgres-ready CI and docs: .github/workflows/tests.yml (line 1) and backend-tests.yml (line 1) start a Postgres service and export DATABASE_URL; README.md (line 3) and mosaic_project_current_state.md (line 8) explain the new setup; mosaic_prototype/backend/.env.example (line 1) documents required variables.
- Test fixtures now build tables through SQLAlchemy and query via the ORM (tests/conftest.py (line 5), tests/test_backup_manager.py (line 1), tests/test_import_validation.py (line 1), tests/test_transactions.py (line 1)), matching the new importer behaviour.
- Legacy SQLite assets (mosaic_prototype/database/init_db.py, mosaic_prototype/database/mosaic.db) have been removed.

251102_backend_postgresql_runtime_migration
Goal: Finalize PostgreSQL as the default runtime database and ensure all backend components operate through SQLAlchemy connections.  

Backend already runs on PostgreSQL and every raw SQL call now goes through SQLAlchemy adapters:

- _resolve_database_uri in mosaic_prototype/backend/app.py (line 50) prefers DATABASE_URL, falls back to assembled POSTGRES_* pieces, and the / route surfaces the URI so we can confirm what booted.
- mosaic_prototype/backend/db_utils.py (line 10) rewrites ? placeholders into bound parameters before executing through SQLAlchemy connections, which keeps existing SQL snippets working.
- mosaic_prototype/backend/backup_manager.py (line 13) wraps all backup reads/writes in an app context, uses SQLAlchemy transactions, and stores last_run as a timestamp so the scheduler remains consistent.
- mosaic_prototype/backend/import_data.py (line 1) now performs atomic upserts on the ORM session (activities first, entries second) and exposes a CLI helper for batch loads.

251102_devops_docker_setup
Goal: Containerize the Mosaic application to enable parallel development and production instances.  

DONE
Added backend and frontend containers plus a shared Compose stack so you can run dev and prod side-by-side against a single Postgres instance with isolated databases.

- Dockerfile.backend (line 1) packages the Flask app on Python 3.12, installs requirements.txt, exposes port 5000, and starts via flask run with host binding for container networking.
- Dockerfile.frontend (line 1) builds the React bundle on Node 18, bakes in the REACT_APP_API_URL build arg (mirrored to the existing _BASE_URL variable), and serves the static build with serve plus a container healthcheck.
- docker-compose.yml (line 1) defines mosaic_backend_dev, mosaic_backend_prod, mosaic_frontend, and postgres services, wiring env files, healthchecks, restart policies, host port mappings (5000/5001/3000/5432), and the persistent postgres_data volume. The FRONTEND_API_URL variable lets you rebuild the frontend against dev (5000) or prod (5001) backends.
- .env.dev (line 1) and .env.prod (line 1) provide sample configurations for each backend, including Postgres connection details and API secrets, plus matching frontend API URLs.
- mosaic_prototype/database/init-mosaic.sql (line 1) seeds the Postgres container with mosaic_dev and mosaic_prod databases owned by the shared mosaic role so each backend instance connects cleanly.

**Jak Spustit**

- Ujistěte se, že máte nainstalovaný Docker a Docker Compose a že jste v kořenovém adresáři projektu (/home/jan/Dokumenty/code/mosaic), kde leží docker-compose.yml.
- Zkontrolujte a případně upravte .env.dev (line 1) a .env.prod (line 1) – tajné klíče vyměňte za vlastní hodnoty; pro prod instanci můžete rovnou nastavit skutečné API klíče.
- Pokud chcete frontend napojit na dev backend, spusťte FRONTEND_API_URL=http://localhost:5000 docker compose up --build. Pro frontend napojený na prod backend změňte hodnotu na http://localhost:5001 a příkaz zopakujte.
- Po doběhnutí buildů běží tyto služby: postgres (PostgreSQL 15 s volume postgres_data), mosaic_backend_dev na portu 5000, mosaic_backend_prod na portu 5001 a mosaic_frontend na portu 3000.
- První spuštění vytvoří databázové role a dvě databáze podle mosaic_prototype/database/init-mosaic.sql (line 1). Dev backend má kvůli volume namapovaný zdroják, takže změny kódu přeberete bez rebuildingu; prod backend běží z buildnutého obrazu.
- Migrace databáze spusťte v běžících kontejnerech, např. docker compose exec mosaic_backend_prod flask db upgrade a analogicky pro dev, aby se vytvořily tabulky.

**Jak To Funguje**

- Dockerfile.backend (line 1) staví Flask aplikaci na Pythonu 3.12, instaluje requirements.txt a spouští flask run naslouchající na 0.0.0.0 (line 5000). V prostředí čte proměnné z .env.dev nebo .env.prod, které určují připojení k Postgresu a JWT/API klíče.
- Dockerfile.frontend (line 1) nejdřív provede build Reactu (Node 18), do procesu injectuje REACT_APP_API_URL, aby frontend/src/config.js používal správný backend. Druhá fáze spouští statický build přes serve na portu 3000.
- docker-compose.yml (line 1) definuje čtyři služby a jejich vzájemné závislosti, health-checky a restart policy (unless-stopped), aby se kontejnery automaticky zkusily obnovit. Volume postgres_data zajišťuje perzistentní databázi pro obě instance.
- Frontend resource mosaic_frontend používá proměnnou FRONTEND_API_URL v build arg i runtime, takže lze snadno přepínat, na který backend míří. Změnu URL je potřeba udělat před docker compose up --build, aby se celý obraz rebuildnul.
- Aplikaci ukončíte pomocí docker compose down; přepínačem -v smažete i volume, což zresetuje databázi. Logy sledujte přes docker compose logs -f <služba>.