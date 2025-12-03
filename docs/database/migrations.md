# Migrations Log (summary)

- **2025-10-29** – Introduced SQLAlchemy/Flask-Migrate scaffolding; added `users` table, authentication flow, transactional guards; initial SQLite schema recorded (`backend/database/schema.sql`).  
  Ref: `docs/changelog/2025-10-29_backend_frontend_summary.md`.

- **2025-11-02** – Backup manager added; `/backup/*` endpoints, `backup_settings` table; backup/export JSON/CSV generation; Postgres adapter via `db_utils`.  
  Ref: `docs/changelog/2025-11-02_postgres_docker_backup.md`.

- **2025-11-03..07** – Test DB workflow (`mosaic_test`), metrics/health admin tooling; pytest orchestration with DB create/migrate/drop.  
  Ref: `docs/changelog/2025-11-03-07_backend_frontend_admin_health_metrics.md`.

- **2024-11-15 (migration id `20241115_000001_initial_schema`)** – Alembic migration creating `users`, `activities`, `entries`, `backup_settings` tables and indexes (Postgres). Mirrors SQLite bootstrap schema.  
  File: `backend/migrations/versions/20241115_000001_initial_schema.py`.

## Known gaps / next migrations to plan
- Add `user_id` to `activities` and `entries`, enforce unique `(user_id, name)` and `(user_id, date, activity)`, add FK or switch to `activity_id` references.
- Add FK between entries and activities, aligned with per-user scope.
- Backfill existing data to per-user-scoped schema; update import/export/backup accordingly.

## Artifacts
- SQLite bootstrap: `backend/database/schema.sql`
- Postgres migration: `backend/migrations/versions/20241115_000001_initial_schema.py`
