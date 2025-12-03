# Resetting the DB and Importing Data for a User

Use this checklist to recreate a clean database, apply per-user schema/migrations, and import an existing export/backup for a specific user.

1. **Drop and recreate the DB (dev/test):**
   - `psql -c "DROP DATABASE IF EXISTS mosaic_dev;"`  
   - `psql -c "CREATE DATABASE mosaic_dev OWNER mosaic;"` (adjust names/owner as needed)
2. **Apply migrations (preferred) or schema.sql:**
   - From the repo root: `cd backend && alembic upgrade head`
   - This creates `users`, `activities`, `entries`, `backup_settings` with per-user FKs and uniques.
3. **Create a user to own imported data:**
   - Via API: `POST /register` (or insert via SQL if scripting).
4. **Import an existing export/backup for that user:**
   - CSV export: `python -m import_data /path/to/export.csv --username <username>`
   - API: `POST /import_csv` with multipart form (`file=@export.csv`) while authenticated as the target user.
   - All imported rows are bound to the authenticated user_id; external CSV/JSON formats remain unchanged.
5. **Verify per-user ownership:**
   - Activities and entries are unique per user (`(user_id, name)` and `(user_id, date, activity)`), and backup_settings is one-per-user.
   - Deleting the user will cascade-delete their activities, entries, and backup_settings.

For ad-hoc local resets during development, you can also clear the public schema:
```sh
psql mosaic_dev -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
cd backend && alembic upgrade head
```
