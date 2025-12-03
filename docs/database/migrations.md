# Migrations Log (summary)

- **2025-10-29** – Introduced SQLAlchemy/Flask-Migrate scaffolding; added `users` table, authentication flow, transactional guards; initial SQLite schema recorded (`backend/database/schema.sql`).  
  Ref: `docs/changelog/2025-10-29_backend_frontend_summary.md`.

- **2025-11-02** – Backup manager added; `/backup/*` endpoints, `backup_settings` table; backup/export JSON/CSV generation; Postgres adapter via `db_utils`.  
  Ref: `docs/changelog/2025-11-02_postgres_docker_backup.md`.

- **2025-11-03..07** – Test DB workflow (`mosaic_test`), metrics/health admin tooling; pytest orchestration with DB create/migrate/drop.  
  Ref: `docs/changelog/2025-11-03-07_backend_frontend_admin_health_metrics.md`.

- **2024-11-15 (migration id `20241115_000001_initial_schema`)** – Alembic migration creating `users`, `activities`, `entries`, `backup_settings` tables and indexes (Postgres). Mirrors SQLite bootstrap schema.  
  File: `backend/migrations/versions/20241115_000001_initial_schema.py`.
- **2025-01-08 (migration id `20250108_000010_user_scoped_schema`)** – Recreates `activities`, `entries`, and `backup_settings` with `user_id` FKs (ON DELETE CASCADE) and per-user uniques: `(user_id, name)` for activities, `(user_id, date, activity)` for entries, and `UNIQUE(user_id)` for backup_settings. Aligns schema with per-user isolation.

## Notes
- All user-owned data now cascades when a user is deleted.
- Import/export/backup continue to use the same external CSV/JSON formats; imported rows are bound to the provided `user_id`.

## Artifacts
- SQLite bootstrap: `backend/database/schema.sql`
- Postgres migrations: `backend/migrations/versions/`
