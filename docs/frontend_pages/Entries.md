# Entries Page Specification

## Identification
- Route: `/` tab `Entries` within `Dashboard`
- Primary components: `EntryForm.jsx`, `BackupPanel.jsx`, `EntryTable.jsx`
- Redux slices: `entriesSlice` (`items`, `filters`, `importStatus`, `today`, `stats`), `backupSlice`
- API endpoints consumed: `/entries`, `/add_entry` (via shared thunks), `/import_csv`, `/entries/:id`, `/export/(csv|json)`, `/backup/*`

## Purpose
- Filter and review historical activity entries with rich export/delete tooling
- Provide CSV import workflow and backup controls for data resilience
- Serve as administrative hub for data lifecycle operations

## Layout
- Component hierarchy
  - `Dashboard` ➜ `EntryForm` ➜ `BackupPanel` ➜ `EntryTable`
    - `EntryForm` wrapped in `FormWrapper` with responsive filter grid and CSV import action in footer
    - `BackupPanel` standalone card showing automation toggles, interval selector, last run metadata, action buttons
    - `EntryTable` uses `DataTable` to render filtered entries and export buttons
- Visual order emphasises: filter controls → backup management → table results
- `EntryForm` fields adapt via `flex-wrap` to keep inputs legible on narrow screens

## Interactive Elements
- Filter form
  - `dateMode` select toggles between All / Single day / Month / Range; revalidates relevant inputs via `react-hook-form`
  - Date inputs auto-populate from existing Redux filters on mount via `reset`
  - Activity/category selects derived from activities list + entries categories; default `all`
  - Submit dispatches `loadEntries` with computed `startDate/endDate`
  - Footer `CsvImportButton` opens file picker, dispatches `importEntries`; shows toasts on success/failure
- Backup controls
  - Toggle button flips `enabled` via `toggleBackup`; label changes to reflect state and disables while `toggling`
  - Interval select updates cadence; options include current stored interval plus default set `[15,30,60,120,240]`
  - “Run backup now” triggers `runBackupNow`; shows spinner label
  - “Download last backup” fetches blob via `downloadBackupFile`; disabled without backups or during download
- Entry table
  - Export buttons call `downloadCsvExport` / `downloadJsonExport` and manage object URL lifecycle
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
  - CSV import `importEntriesCsv` posts multipart file; on success, refreshes `loadEntries`, `loadStats`, `loadToday`
  - Delete entry cascades to `loadStats` + `loadToday` for cross-tab updates
- Backup slice selectors
  - `selectBackupState` feeds toggle states, `enabled`, `intervalMinutes`, `lastRun`, `backups`, `running`, `toggling`, `error`
  - `selectLatestBackup` used to display latest file metadata and pass to download handler

## Styles
- Shared palette and control styles from `styles/common.js`
- `FormWrapper` standardises form header, submit/cancel area, and padding
- `BackupPanel` uses inline tokens for background (`#232428`) and responsive flex rows for actions/info
- `DataTable` provides consistent header, empty state, and loading skeleton behaviour
- Export buttons tinted via inline overrides (`#2f9e44` for JSON, default for CSV) to highlight variant actions

## Notes
- Filter form autodetects month range by checking start/end boundaries; ensure backend keeps inclusive semantics
- Entry deletion uses optimistic removal from `items`; no undo—consider confirmation dialog if data sensitivity increases
- `CsvImportButton` enforces MIME/size validation before dispatch (see component for details)
- Backup error messages stored as plain strings; consider centralising localization and severity mapping later
- `download*` helpers rely on browser environment; for server-side rendering contexts, guard invocations
