# Today Page Specification

## Identification
- Route: `/` default tab inside `Dashboard` when authenticated
- Primary component: `frontend/src/components/Today.jsx`
- Supporting components: `Loading`, `ErrorState`
- Redux slice: `entriesSlice.today`
- Related async thunks: `loadToday`, `saveDirtyTodayRows`, `finalizeToday`

## Purpose
- Provide a single-day activity diary with quick capture of quantitative value and short note per activity
- Surface progress against aggregate daily goals and contextual feedback about pending autosaves or errors
- Allow users to navigate historical days while preserving unsaved changes and preventing forward navigation beyond today

## Layout
- High-level structure (desktop)
  - Summary grid with date navigation, progress meter, and save status indicator
  - Activity table (`<table>`) with columns Activity | Value | Note; rows highlight when `value > 0` and tint green for `activity_type === 'positive'` or red for `activity_type === 'negative'`
- High-level structure (compact/mobile)
  - Summary grid remains stacked; navigation buttons expand to full width
  - Activities rendered as stacked cards with inline select/input controls
- Component hierarchy
  - `Dashboard` ➜ `Today`
    - Summary section (buttons, date input, helper copy)
    - Progress meter (computed percent + ratio label)
    - Status hint (autosave indicator / dirty count)
    - Activity content (responsive table or cards)
    - `Loading` inline banners where applicable
    - `ErrorState` full-surface fallback when `status === "failed"`

## Interactive Elements
- Date picker (`type="date"`) limited by `max=todayString`; prev/next day buttons disabled past today
- Value dropdown (`select` 0–5) triggers immediate `updateTodayRow` dispatch and debounced `saveDirtyTodayRows`
- Note input (`<input>` max 100 chars) schedules autosave (`NOTE_SAVE_DELAY_MS` 5000ms) or flushes on Enter submit
- Midnight finalization: interval checks every 60s and dispatches `finalizeToday` near local midnight
- Autosave feedback: `dirtyCount` > 0 shows “change(s) pending”; when saving, shows `💾 Auto-saving...`
- Error recovery: `ErrorState` exposes “Retry load” button calling `loadToday(date)`

## Data Bindings
- `selectTodayState` hydrates `{ date, rows, status, dirty, savingStatus, error }`
- `rows` items (normalized in `entriesSlice`) supply
  - `row.name` → row label
  - `row.category` → tooltip/auxiliary copy
  - `row.value` → select current value
  - `row.note` → note input value
  - `row.goal` contributes to aggregate `progressStats`
  - `row.activity_type` drives green/red row tinting when the entry has `value > 0`
- Progress summary pulls from derived totals: `totalValue`, `totalGoal`, `percentLabel`, `ratioLabel`
- Debounced autosave pipeline uses `saveDirtyTodayRows` thunk ➜ `/add_entry`; success triggers `loadToday`, `loadEntries`, `loadStats`
- Midnight finalization hits `/finalize_day` via `finalizeToday`
- Initial and subsequent loads call `/today` through `loadToday`

## Styles
- Shared tokens from `styles/common.js` (`styles.button`, `styles.input`, `styles.card`, `styles.positiveRow`, `styles.negativeRow`)
- Responsive adjustments via `useCompactLayout` toggling grids, padding, and layout direction
- Progress meter uses inline style computed color (`styles.highlightRow.backgroundColor` when ≥50%)
- Table alternates `styles.table`/`styles.tableRow`; cards reuse `styles.card` with conditional background for completed activities (green positive, red negative)

## Notes
- Autosave debounce clears on component unmount and when manually flushing to prevent stale timers
- Notes truncated client-side to 100 chars before dispatch; consider surfacing remaining character counter in future iteration
- `loadToday` re-runs on date change, tab revisit, and after mutation thunks that may alter available rows
- Friendly error messaging derived from `todayError.friendlyMessage`; ensure backend aligns error schema
- Extend spec later if goal ranges or custom scales change—current UI assumes discrete 0–5 scale
