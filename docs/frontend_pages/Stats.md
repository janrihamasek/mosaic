# Stats Page Specification

## Identification
- Route: `/` tab `Stats` within `Dashboard`
- Primary component: `frontend/src/components/Stats.jsx`
- Redux slice: `entriesSlice.stats`
- API endpoint: `/stats/progress` via `fetchProgressStats`

## Purpose
- Present rolling performance analytics (goal completion, activity distribution, streaks)
- Enable users to refresh metrics on demand and scan category-level trends
- Provide guidance on engagement balance (positive vs negative entries, consistency leaders)

## Layout
- Container structure: single card (`styles.card`) wrapping stacked analytic sections
- Sections (in order)
  - Header: title, subtitle, `Refresh` button
  - Top KPI grid: Goal Completion Today + Active Days (30d)
  - Distribution row: Activity Distribution pie + Goal Fulfillment Trend mini-chart
  - Secondary grid: Positive vs Negative meter + Category averages carousel
  - Consistency panel: “Top Consistent Activities by Category” with pagination controls
- Component hierarchy
  - `Dashboard` ➜ `Stats`
    - `Loading` or `ErrorState` wrappers for status
    - Main content divides into responsive grids using `useCompactLayout`

## Interactive Elements
- `Refresh` button triggers `loadStats({ date })`; disabled state handled implicitly by thunk status
- Category averages navigation buttons (`◀`/`▶`) cycle index when more than one bucket; disabled otherwise
- Consistency section also offers pagination controls when multiple categories exist
- Accessibility: charts provide `aria-label` (`svg` polyline) and progress bars include `role="progressbar"`

## Data Bindings
- `selectStatsState` supplies `{ snapshot, status, error, date }`
  - `status === 'loading'` shows blocking `Loading` within container
  - `status === 'failed'` surfaces `ErrorState` with retry bound to `loadStats`
- Snapshot structure fields consumed:
  - `goal_completion_today` → KPI percent + meter width
  - `streak_length` → streak badge text
  - `active_days_ratio` → numerator/denominator and percent copy
  - `activity_distribution[]` → pie chart segments + legend rows (color assigned via index)
  - `avg_goal_fulfillment.last_7_days` & `.last_30_days` → trend polyline points
  - `positive_vs_negative` → dual meter widths, totals, ratio text
  - `avg_goal_fulfillment_by_category[]` → paged cards showing 7d/30d stats per category
  - `top_consistent_activities_by_category[]` → paged list of activities with `consistency_percent`
- Refresh pipeline: thunk resolves JSON payload (or null) from `/stats/progress`; component stores last requested `date`

## Styles
- Utilises shared tokens from `styles/common.js` for card background, button styling, typography
- Custom inline gradients for goal meter (`linear-gradient(90deg,#3a7bd5,#43cea2)` when ≥80%)
- Responsive grids adapt `gridTemplateColumns` based on `useCompactLayout` to collapse to single column on narrow widths
- Pie chart rendered using CSS `conic-gradient`; fallback background `#2f3034` when no data

## Notes
- Component assumes percent values 0–100; ensure backend sanitises data to avoid NaNs/negative widths
- `loadStats` is also invoked from other thunks (entries creation/import) to keep analytics fresh
- Consider memoising pie gradient by caching computed string if performance becomes concern with frequent renders
- Future enhancements: swap inline charts for reusable chart primitives once design system grows
- Snapshot `date` is currently optional; spec leaves room for user-selectable timeframes later
