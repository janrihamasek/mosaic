# Admin Tab Specification

## Identification
- Tab: `Admin` inside `Dashboard` (visible to all users, but non-admins only see the **User** section)
- Primary wrapper: `src/components/Admin.jsx`
- Sub-components:
  - `AdminUser.jsx`
  - `AdminSettings.jsx` → `BackupPanel.jsx`, `ImportExportPanel.jsx`
  - `HealthPanel.jsx`
  - `AdminLogs.jsx`
  - `AdminNightMotion.jsx` → `NightMotion.tsx`
- Redux slices involved: `authSlice`, `backupSlice`, `adminSlice`, `nightMotionSlice`
- API touchpoints: `/user`, `/users`, `/backup/*`, `/export/(csv|json)`, `/import_csv`, `/healthz`,
  `/metrics?format=json`, `/logs/activity`, `/logs/runtime`, `/api/stream-proxy`

## Purpose
- Provide a single surface for profile management, tenant administration, backups/import/export controls, and production health monitoring.
- Reduce dashboard clutter by relocating advanced tooling (backups, NightMotion) away from the Entries tab.
- Give administrators quick visibility into uptime, request throughput, and error rates.

## Layout & Navigation
- Left rail renders a vertical (desktop) or horizontal (compact) button group. Items:
  1. **User** — always available.
  2. **Settings** — admin-only.
  3. **Health** — admin-only.
  4. **Logs** — admin-only.
  5. **NightMotion** — admin-only.
- Active item button uses `styles.tabActive` (compact) or a bordered card style (desktop). Selection stored in component state; it resets if the available sections change (e.g., non-admin view).
- Right content area swaps in the selected component. Each card reuses `styles.card` for consistency.

## Section Details
### User
- Shows immutable account metadata (username, displayName, role).
- Edit form fields:
  - Display name (`input[type="text"]`)
  - New password / confirm password (two `input[type="password"]` fields)
- Save button dispatches `updateCurrentUserProfile`; validation ensures passwords match and meet length requirements.
- Delete account button triggers `deleteAccount` with `window.confirm`, then navigates to `/login`.
- Status indicators rely on `auth.status.profileUpdate` and `auth.status.deleteAccount` to disable inputs.

### Settings
- **BackupPanel**
  - Toggle automatic backups via `toggleBackup` (button text flips between enable/disable).
  - Interval select uses dynamic options (`[15,30,60,120,240]` + stored value) and dispatches `toggleBackup` with the chosen cadence.
  - "Run backup now" triggers `runBackupNow`; success toasts include the generated filename.
  - "Download latest backup" fetches blobs via `downloadBackupFile`; handles object URL clean-up.
  - Panel auto-loads status on mount via `loadBackupStatus` and reflects `backupState.status/toggling/running` in button disabled states.
- **ImportExportPanel**
  - `CsvImportButton` opens a file picker, validates client-side (extension/size), and dispatches `importEntries` (shared thunk). Toasts summarise the `created/updated/skipped` counts.
  - Export buttons call `downloadCsvExport` / `downloadJsonExport`, constructing temporary anchors for downloads.
  - Layout adapts between stacked (compact) and inline (desktop) action rows.

### Health
- `HealthPanel` polls `/healthz` and `/metrics?format=json` via `loadHealth` / `loadMetrics` thunks in `adminSlice`.
- Summary cards show uptime, requests per minute, error rate, DB/cache status; card styles adjust based on tone (`ok`, `info`, `warn`, `alert`).
- Metrics table lists endpoints grouped by request count; data sorted descending by `count`.
- `Refresh` button manually re-dispatches both thunks; auto-refresh runs every 60 seconds via `setInterval`.
- Error handling: combined error surfaces a toast + inline `ErrorState` when data is unavailable while still rendering stale data when possible.

### NightMotion
- `AdminNightMotion` simply renders `NightMotion.tsx`, but availability is restricted to admins through the Admin tab filter.
- Inherits all behaviour from the NightMotion page spec (form + preview), now co-located with other admin tools.

## Interactive & Data Binding Notes
- `Admin.jsx` inspects `auth.isAdmin` to determine available sections. Non-admins never render Settings/Health/NightMotion, ensuring backend-only APIs remain inaccessible via UI.
- Notifications bubble up through the shared `onNotify` callback from `Dashboard`, so every section can emit toasts consistently.
- `adminSlice` maintains independent status/error/lastFetched values for health vs metrics requests, enabling partial success rendering.
- `adminSlice` also maintains cached responses for activity/runtime logs so all admin users see a synchronized auto-refresh cadence.
- `backupSlice` tracks long-running states (`running`, `toggling`, `downloading`), preventing duplicate operations.

## Open Questions / Future Enhancements
- Add user list & role management UI (currently CLI/`/users` only).
- Surface backup history/audit entries directly in the Settings section instead of raw file names.
- Expand Health with sparkline histories or Prometheus badge integration once external monitoring is wired up.
- Add richer log filtering (per-user/event-type search) and CSV export from the Logs section.

### Logs
- `AdminLogs.jsx` exposes two tabs: **Activity Logs** (persistent audit trail from `/logs/activity`) and **Runtime Logs** (ephemeral structlog buffer from `/logs/runtime`).
- Each tab reuses `DataTable.tsx` with columns for timestamp, user, event type, level badge, and message body. Runtime logs swap the "user" column for the emitting logger name.
- The component dispatches `loadActivityLogs` / `loadRuntimeLogs` on mount and via a shared 60 s interval; manual refresh button triggers both thunks immediately.
- State: `admin.activityLogs` and `admin.runtimeLogs` track `status`, `data`, `error`, and `lastFetched`. Errors surface inline without clearing previously loaded rows.
- User identification prefers `context.username`, falling back to `user_id` or “System” to distinguish backend automations.
