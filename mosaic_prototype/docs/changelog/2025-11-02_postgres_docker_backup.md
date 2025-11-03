# 2025-11-02 Mosaic Changelog

## Phase 1 – Stabilization & Testing

* **Frontend CI polyfills:** Added TextEncoder/TextDecoder polyfill in `jest.setup.ts`; fixed NightMotion tests and ESLint warnings so GitHub Actions runs cleanly.
* **Autosave behavior:** Today screen now saves values instantly and notes on Enter or idle timeout (5 s), improving responsiveness and preventing duplicates.

## Phase 2 – Data Layer & Analytics

* **Data export:** New authenticated CSV/JSON download endpoints with pagination and frontend download controls.
* **CSV import validation:** Duplicate and missing-field detection via Pydantic schemas; per-row audit and unit tests added.
* **Backup manager:** Automatic and manual database backups (JSON/CSV/ZIP) with persistent user settings and frontend BackupPanel.
* **User docs:** Created `docs/USER_DOCS.md` as introductory guide.

## Phase 3 – Backend, Migration & DevOps

* **PostgreSQL integration:** Replaced SQLite with PostgreSQL; added SQLAlchemy ORM, Flask-Migrate migrations, updated tests and .env examples.
* **Runtime adapter:** All database operations now go through SQLAlchemy transactions via `db_utils.py`; import and backup modules rewritten for Postgres.
* **Docker stack:** Introduced `Dockerfile.backend`, `Dockerfile.frontend`, and `docker-compose.yml` defining dev/prod instances with shared Postgres service and persistent volume; documented start/stop procedures.
