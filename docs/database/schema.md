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
- `user_id` (integer, not null, FK → `users.id` ON DELETE CASCADE)
- `name` (text, not null, unique per user via `UNIQUE(user_id, name)`)
- `category` (text, not null, default `""`)
- `activity_type` (text, default `positive`)
- `goal` (real/float, not null, default `0`)
- `description` (text, nullable)
- `active` (boolean/int, not null, default `true`)
- `frequency_per_day` (int, default `1`)
- `frequency_per_week` (int, default `1`)
- `deactivated_at` (text/timestamp, nullable)
- `is_system` (boolean, default `false`)

### entries
- `id` (PK, integer)
- `user_id` (integer, not null, FK → `users.id` ON DELETE CASCADE)
- `date` (text, not null)
- `activity` (text, not null) – matches the activity name for the same `user_id`
- `description` (text, nullable)
- `value` (real/float, default `0`)
- `note` (text, nullable)
- `activity_category` (text, not null, default `""`)
- `activity_goal` (real/float, not null, default `0`)
- `activity_type` (text, default `positive`)
- **Unique constraint:** `(user_id, date, activity)`

### backup_settings
- `id` (PK, integer)
- `user_id` (integer, not null, FK → `users.id` ON DELETE CASCADE, unique)
- `enabled` (boolean/int, default `false`)
- `interval_minutes` (int, default `60`)
- `last_run` (timestamp/text, nullable)

## Data ownership
- All user-generated data is scoped by `user_id`. Different users can safely have the same activity names without collisions.
- Cascading deletes from `users` will remove activities, entries, and backup_settings for that user.

## Artifacts
- SQLite/Postgres schema reference: `backend/database/schema.sql`
- Postgres Alembic migrations: `backend/migrations/versions/`
- Models: `backend/models.py`
