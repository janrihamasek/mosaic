# Daily Log – 2024-11-16

- Date: 2024-11-16
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 16_11_mosaic.md

## Notes (raw import)

backend_negative_activities_db_migration
Goal: Add activity_type to activities with default positive.  

- Added the permanent activity_type column to the SQLAlchemy model with both ORM and server defaults so existing code and new rows always default to positive; see backend/models.py (lines 15-33).
- Expanded the activity payload schemas to accept/validate the new field, normalizing it to positive/negative and exposing it through the validation helpers; refer to backend/schemas.py (lines 55-213).
- Updated API logic to persist and surface the field everywhere activities are created, updated, exported, or listed (backend/app.py (lines 824-903), backend/app.py (lines 1660-1691), backend/app.py (lines 2048-2193), backend/app.py (lines 1810-1870), backend/app.py (lines 2563-2627)). These changes ensure new activities set the requested type, overwrites honor it, ad‑hoc inserts default to positive, and responses (/activities, /today, CSV export) now include the value.
- Introduced Alembic migration backend/migrations/versions/20241205_000007_add_activity_type_to_activities.py to add the non-null column with a positive server default so existing data is backfilled automatically.

---

backend_negative_activities_crud_logic
Goal: Implement full backend logic for negative activities.  

- backend/models.py (lines 18-69) now tracks activity_type on both activities and entries, and the accompanying Alembic revision backend/migrations/versions/20241205_000008_add_activity_type_to_entries.py (lines 1-28) adds the non-null column with a positive server default so existing snapshots are backfilled automatically.
- backend/app.py (lines 1805-1967) propagates the type through entry CRUD: selecting it from activities, persisting it on every update/insert, and keeping placeholder activities/entries in sync (plus backend/import_data.py (lines 20-108) ensures CSV imports seed both activities and entries with the correct type). Activity updates also push the new type into historical entries (backend/app.py (lines 2239-2244)), and finalize_day now stores the type when creating missing entries (backend/app.py (lines 2723-2762)).
- The CSV/backup exports include the new metadata for both datasets so downstream snapshots stay self-contained (backend/app.py (lines 1633-1693), backend/backup_manager.py (lines 250-301)), and _fetch_export_data includes e.activity_type for API consumers (backend/app.py (lines 838-885)).
- Today’s payload zeroes the goal for negative activities to keep the UI logic simple (backend/app.py (lines 2600-2663)), while the stats pipeline filters out negative activities/entries across every aggregate (goal sums, daily/category groupings, distributions, consistency lists) and repurposes the “positive vs negative” widget to count active activities by type (backend/app.py (lines 2349-2592)). All existing cache invalidations remain in place so flipping a type immediately refreshes /today and /stats.

---
backend_negative_activities_crud_logic
frontend_negative_activities_ui
Goal: Add UI and styling for positive/negative activity types.  

- Added full activity-type editing support: the create form now exposes a Positive/Negative selector and submits it to the backend (frontend/src/components/ActivityForm.jsx (lines 60-176)), while the detail modal keeps the field in sync and persists changes alongside frequency updates (frontend/src/components/ActivityDetail.jsx (lines 14-205)).
- Normalized API types/state so activity_type data flows everywhere: shared types now declare the enum, activities/entries slices normalize values from both live and cached payloads, and today rows keep the flag for local edits (frontend/src/types/api.d.ts (lines 1-36), frontend/src/types/store.d.ts (lines 1-50), frontend/src/store/activitiesSlice.ts (lines 74-137), frontend/src/store/entriesSlice.ts (lines 83-141)).
- Introduced reusable styling hooks for positive/negative rows and taught DataTable to accept per-row styles, enabling consistent colouring across Activities, Entries, and Today views (frontend/src/styles/common.js (lines 260-298), frontend/src/components/shared/DataTable.tsx (lines 27-154)).
- Applied the new tinting plus subtle completion highlight to each view: activities show a type column and colour-coded rows, entries tint rows in both table and card layouts, and Today’s compact and desktop tables now reflect type while still outlining completed values (frontend/src/components/ActivityTable.jsx (lines 24-205), frontend/src/components/EntryTable.jsx (lines 38-152), frontend/src/components/Today.jsx (lines 269-387)).

---

tests_negative_activities_fullstack
Goal: Add basic test coverage and documentation for negative activities.  

- Backend now returns activity_type for every /entries row so the UI and tests can reason about colors, and new regression tests cover full negative-activity flows plus stats exclusion (backend/app.py (lines 1750-1782), backend/tests/test_api.py (lines 120-190)).
- Added Jest coverage for the form UX and row coloring: ActivityForm hides cadence inputs for negative activities and dispatches goal: 0 (frontend/src/components/__tests__/ActivityForm.test.jsx), while EntryTable verifies the green/red tinting logic via the shared styles (frontend/src/components/__tests__/EntryTable.test.jsx).
- Documentation explains the new activity_type payload field, the automatic goal=0 semantics, and the frontend tinting rules across Activities, Entries, and Today (docs/API_DOCS.md (lines 120-189), docs/frontend_pages/Activities.md (lines 1-82), docs/frontend_pages/Entries.md (lines 1-42), docs/frontend_pages/Today.md (lines 1-76)).