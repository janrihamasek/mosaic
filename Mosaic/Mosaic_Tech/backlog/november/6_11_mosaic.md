# Daily Log – 2024-11-06

- Date: 2024-11-06
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 6_11_mosaic.md

## Notes (raw import)

- nová sekce do statistik a její ladění
- ladění refreshe stránek
- facelift a úprava karet
- nová karta Admin
---
251106_frontend_admin_dashboard_menu
Goal: Add a new Admin tab to the dashboard with internal menu sections for user management, settings, and NightMotion.  
DONE
Added an Admin tab to the dashboard and moved the backup/import and NightMotion tooling into scoped admin sections for clearer navigation.
- mosaic_prototype/frontend/src/Dashboard.jsx (line 26) switches the main tab list to include Admin, drops the standalone NightMotion block, and keeps Entries focused on entry tools while still wiring notifications to the admin content area.
- mosaic_prototype/frontend/src/components/Admin.jsx (line 9) introduces the responsive admin shell with a sidebar/tab menu that swaps between User, Settings, and NightMotion sections while passing notifications through.
- mosaic_prototype/frontend/src/components/AdminSettings.jsx (line 6) nests the existing BackupPanel and ImportExportPanel so their controls live under Admin settings.
- mosaic_prototype/frontend/src/components/AdminNightMotion.jsx (line 5) now solely imports NightMotion, satisfying the requirement that the feature only loads inside the admin area.
- mosaic_prototype/frontend/src/components/AdminUser.jsx (line 5) adds a placeholder card earmarked for future user-management tools.
- mosaic_prototype/frontend/src/App.jsx (line 17) removes the dedicated /night-motion route so navigation happens exclusively via the new Admin tab.

251106_backend_userid_schema_migration
Goal: Add user ownership to core data tables and enforce referential integrity.  
DONE
- Updated mosaic_prototype/backend/models.py (line 18) and mosaic_prototype/backend/models.py (line 43) to add nullable user_id foreign keys on activities and entries and wire them to the owning User, with back-populated relationships (models.py (line 64)) so deletes can cascade cleanly from the ORM.
- Added Alembic migration mosaic_prototype/backend/migrations/versions/20241125_000002_add_user_ownership.py (line 1) that introduces the new columns, supporting indexes, and ON DELETE CASCADE foreign keys while guarding against reruns; downgrade removes the artifacts in reverse order.

251106_backend_user_scope_filters
Goal: Restrict all API queries and mutations to the authenticated user.  
DONE
Updated the backend so every request carries user scope and we enforce it across exports, CRUD, and stats.
- mosaic_prototype/backend/app.py (lines 153-169) introduces helpers to read the current account plus is_admin, and the token pipeline now includes that flag (app.py (lines 272-283), app.py (lines 732-736)) with a resilient login query that falls back if the column is missing (app.py (lines 638-678)).
- _fetch_export_data and the export endpoints are now user-aware (app.py (lines 366-443)), returning only the caller’s rows unless is_admin is true, while keeping counts/indexes consistent.
- Core entry and activity endpoints (app.py (lines 986-1174), app.py (lines 1183-1206), app.py (lines 1226-1426)) now filter reads/updates/deletes by user_id, stamp it on inserts, and only let admins bypass the check; existing null-owned records are claimed on first update.
- Analytical surfaces—progress stats, today view, and finalize-day (app.py (lines 1430-1851))—apply the same scoping so aggregates, cache payloads, and auto-generated rows stay tied to the authenticated user feed.
Hotovo – přidal jsem podporu pro admin flag a nástroj na přiřazení existujících záznamů ke konkrétnímu uživateli.
- mosaic_prototype/backend/models.py (line 60) rozšířil model User o sloupec is_admin, takže ORM i budoucí operace vědí, kdo je admin.
- Nová migrace mosaic_prototype/backend/migrations/versions/20241125_000003_add_is_admin_flag.py (line 1) přidává na databázi sloupec is_admin se základní hodnotou FALSE.
- mosaic_prototype/backend/manage.py (line 44) nově obsahuje CLI příkaz assign-user-data, který přiřadí všechny dosud neobsazené activities a entries vybranému uživateli a volitelně z něj udělá admina (používá transakci přes SQLAlchemy).

251106_backend_user_admin_endpoints
Goal: Add user profile and admin management endpoints.  
DONE
- mosaic_prototype/backend/models.py (line 59) adds a required display_name column to User, and new migration mosaic_prototype/backend/migrations/versions/20241125_000004_add_display_name_to_users.py (line 1) backfills it from usernames.
- mosaic_prototype/backend/schemas.py (line 341) extends registration payloads with an optional display_name and introduces UserUpdatePayload used to validate profile edits.
- mosaic_prototype/backend/security.py (line 18) now exposes require_admin plus validate_user_update_payload, letting the API guard admin-only routes and sanitize profile updates.
- mosaic_prototype/backend/app.py (line 320) adds helpers to serialize user rows, includes display_name in JWTs, upgrades register/login flows, and implements the new endpoints:
    - `GET/PATCH/DELETE /user for self-profile management (app.py (lines 750-849))`
    - `GET /users and DELETE /users/<id> restricted via @require_admin (app.py (lines 852-891)).`
- mosaic_prototype/backend/manage.py (line 71) continues to work with the new schema (no extra changes required for the admin command).

 251106_frontend_user_profile_ui
Goal: Display and manage current user profile from the dashboard.  
DONE
- Added dynamic auth-aware tabs, header context, and profile modal wiring in mosaic_prototype/frontend/src/Dashboard.jsx (lines 63-420), hiding the Admin tab for non-admins, surfacing the signed-in name, and launching profile management from the dashboard.
- Persisted display name/admin flags and exposed a storage merge helper in mosaic_prototype/frontend/src/services/authService.js (lines 62-164), while new mosaic_prototype/frontend/src/services/userService.js (lines 1-14) wraps the /user endpoints.
- Extended auth state shape and async flows in mosaic_prototype/frontend/src/store/authSlice.ts (lines 21-272), adding profile/update/delete thunks that sync Redux with storage without dropping existing tokens.
- Declared the extra auth fields/status slots in mosaic_prototype/frontend/src/types/store.d.ts (lines 12-29).
- Introduced mosaic_prototype/frontend/src/components/ProfileModal.jsx (lines 1-239) to edit display name/password, reuse import/export tools, and trigger account deletion with feedback.

Konkrétně to znamená:
- **Každý účet má vlastní data.**  
    `entries`, `activities`, `stats`, `today` atd. se filtrují `WHERE user_id = current_user.id`. 
    Dva přihlášení uživatelé vidí zcela odlišné datové sady, i když běží ve stejné instanci serveru a sdílí databázi.
- **Současné přihlášení více uživatelů je podporováno.**  
    JWT token se ověřuje při každém requestu, takže můžeš mít třeba:
    - jeden účet otevřený v jednom prohlížeči,
    - druhý účet v jiném prohlížeči nebo anonymním okně,
    - oba komunikují paralelně s Flask backendem a mají oddělené session.
- **Admin má výjimky.**  
    Pokud `is_admin=True`, může přistupovat i k datům jiných uživatelů (např. v exportu, auditu nebo při mazání účtů).
- **Bezpečnostní vrstvy zůstávají aktivní.**  
    JWT + CSRF ochrana, rate limiting, transakce a cache invalidace fungují stejně pro každý účet.

