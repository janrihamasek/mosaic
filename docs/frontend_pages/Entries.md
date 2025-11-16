# Entries Page Specification

## Identification
- Route: `/` tab `Entries` within `Dashboard`
- Primary components: `EntryForm.jsx`, `EntryTable.jsx`
- Redux slice: `entriesSlice` (`items`, `filters`, `today`, `stats`)
- API endpoints consumed: `/entries`, `/add_entry` (via shared thunks), `/entries/:id`

## Purpose
- Filter and review historical activity entries with fine-grained criteria
- Provide quick delete tooling for cleanup or corrections
- Surface paginated, denormalised row data that mirrors CSV/JSON exports (which now live under Admin → Settings)

## Layout
- Component hierarchy
  - `Dashboard` ➜ `EntryForm` ➜ `EntryTable`
    - `EntryForm` uses `FormWrapper` with responsive filter grid
    - `EntryTable` uses `DataTable` for sorted, paginated rows
- Visual order emphasises filter controls first, then the result table
- `EntryForm` fields adapt via `flex-wrap` to keep inputs legible on narrow screens

## Interactive Elements
- Filter form
  - `dateMode` select toggles between All / Single day / Month / Range; revalidates relevant inputs via `react-hook-form`
  - Date inputs auto-populate from existing Redux filters on mount via `reset`
  - Activity/category selects derived from activities list + entries categories; default `all`
  - Submit dispatches `loadEntries` with computed `startDate/endDate`
  - CSV import / export is now handled in Admin → Settings (`ImportExportPanel`)
- Entry table
  - Delete button per row dispatches `deleteEntry`; disabled while request pending for that id
  - `ErrorState` appears when `status === 'failed'` with retry hooking `loadEntries`

## Data Bindings
- `selectEntriesFilters` hydrates form defaults (react-hook-form `reset` on each filter change)
- `selectAllActivities` (from activities slice) supplies options for activity filter
- `selectEntriesList` populates table rows (each augmented with `_rowIndex` fallback key)
- `selectEntriesState` yields `{ status, deletingId, error, importStatus }`
  - Drives loading overlays (`Loading` inline when refreshing) and disables delete actions
- Subsequent thunks triggered
  - `loadEntries` calls `/entries` with query params from filters
  - Delete entry cascades to `loadStats` + `loadToday` for cross-tab updates

## Styles
- Shared palette and control styles from `styles/common.js`
- `FormWrapper` standardises form header, submit/cancel area, and padding
- `DataTable` provides consistent header, empty state, and loading skeleton behaviour; row `background-color` reflects `activity_type` (green for positive, red for negative)

## Notes
- Filter form autodetects month range by checking start/end boundaries; ensure backend keeps inclusive semantics
- Entry deletion uses optimistic removal from `items`; no undo—consider confirmation dialog if data sensitivity increases
- Data lifecycle actions (CSV import/export, backups) have moved to Admin → Settings; keep this page focused on review/deletion
- `EntryTable` currently focuses on display + delete actions; all export/download logic resides in Admin → Settings
