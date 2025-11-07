# Admin Logs Specification

## Overview
- Location: `Admin` tab → **Logs** section (admin-only)
- Component: `src/components/AdminLogs.jsx`
- Purpose: expose both the persistent ActivityLog records and the ephemeral runtime log buffer so administrators can audit user/system actions without leaving the dashboard.
- Related Redux slice: `adminSlice` (`activityLogs`, `runtimeLogs`)
- API touchpoints: `/logs/activity`, `/logs/runtime`

## Layout
1. **Header**
   - Title: “System Logs”
   - Subtext shows last refreshed time for the active tab and notes the 60 s auto-refresh.
   - “Refresh now” button triggers both log fetch thunks; disabled while any fetch is in flight.
2. **Tab selector**
   - Buttons: “Activity Logs” (default) and “Runtime Logs”.
   - Tab state stored locally so switching is instant without re-fetching.
3. **Description + Status**
   - Text describing the active data source.
   - Inline `ErrorState` appears only when a fetch fails but stale data exists; retry button re-dispatches both thunks.
4. **DataTable**
   - Shared table component renders responsive cards on mobile and a table on desktop.
   - Props vary per tab but always include columns, rows, empty message, and loading/error copy.

## Data & Columns
### Activity Logs
- Source payload: `{ items, total, limit, offset }`
- Columns:
  1. `timestamp` → locale string, fallback to raw ISO.
  2. `user` → `context.username` > `user_id` > “System”.
  3. `event_type`
  4. `level` → badge with tone (info/warn/error/etc.).
  5. `message`
- Empty message: “No activity logs recorded yet.”
- Loading copy: “Loading activity logs…”

### Runtime Logs
- Source payload: `{ logs: [{ timestamp, logger, level, message }], limit }`
- Columns:
  1. `timestamp`
  2. `logger`
  3. `level` badge
  4. `message`
- Empty message: “No runtime logs captured yet.”
- Loading copy: “Loading runtime logs…”

## Behaviour
- Requests fire on mount if the respective slice status is `idle`.
- A `setInterval` re-dispatches both thunks every 60 s; clearing occurs on unmount.
- Manual refresh triggers both thunks to keep datasets in sync with the same cadence.
- While loading with existing data, the header text adds “(refreshing…)” to avoid hiding the table.
- DataTable receives `error` only when there are zero rows, so stale data remains visible even if the latest poll fails.
- Row IDs prefer backend `id`; runtime entries fall back to `{timestamp}-{index}` to keep keys stable enough for React.

## Future Enhancements
- Add filters (user, event type, level, date range) mapped to the API query params.
- Enable CSV/JSON export directly from the logs panel.
- Surface structured context payloads in a collapsible drawer instead of plain text.
