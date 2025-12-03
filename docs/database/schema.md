# Database Schema Overview

This document summarizes the current Mosaic database schema, key constraints, and data ownership notes. It is intended as a quick reference for engineers and a starting point for migration planning.

## Tables

### users
- `id` (PK, integer)
- `username` (text, unique, not null)
- `password_hash` (text, not null)
- `created_at` (timestamp with timezone, default `now()`)

### activities
- `id` (PK, integer)
- `name` (text, unique, not null) **Note:** currently global unique – no `user_id` column yet.
- `category` (text, not null, default `""`)
- `activity_type` (text; in SQLite schema defaults to `positive`, in Postgres migration column exists)
- `goal` (real/float, not null, default `0`)
- `description` (text, nullable)
- `active` (boolean/int, not null, default `true`)
- `frequency_per_day` (int, default `1`)
- `frequency_per_week` (int, default `1`)
- `deactivated_at` (text/timestamp, nullable)

### entries
- `id` (PK, integer)
- `date` (text, not null)
- `activity` (text, not null) – references `activities.name` by convention, no FK.
- `description` (text, nullable)
- `value` (real/float, default `0`)
- `note` (text, nullable)
- `activity_category` (text, not null, default `""`)
- `activity_goal` (real/float, not null, default `0`)
- **Unique constraint:** `(date, activity)` in SQLite schema.
- **Missing scoping:** no `user_id` column; all rows share the same namespace.

### backup_settings
- `id` (PK, integer)
- `enabled` (boolean/int, default `false`)
- `interval_minutes` (int, default `60`)
- `last_run` (timestamp/text, nullable)

## Known Gaps / Risks
- **No per-user scoping:** `activities` and `entries` lack a `user_id` column. Activity names are globally unique, so two users cannot have the same activity name; imports may skip rows with “belongs to another user”.
- **Foreign keys:** none are enforced between `entries` and `activities`; integrity relies on application logic.
- **Backups/imports:** backup/export currently filter data by user in code, but the underlying schema is shared. Importers may collide on activity names across users.

## Planned Fixes (proposed)
- Introduce `user_id` on `activities` and `entries` with unique `(user_id, name)` for activities and `(user_id, date, activity)` for entries.
- Add foreign keys from `entries.activity` to `activities.name` (or better: `activity_id`), aligned with user scope.
- Migrate existing data to per-user scoped tables; update import/export to carry `user_id` (or enforce current user) to prevent leakage.

## Artifacts
- SQLite bootstrap schema: `backend/database/schema.sql`
- Postgres Alembic migration: `backend/migrations/versions/20241115_000001_initial_schema.py`
- Models: `backend/models.py`
