# 2025-10-31 – Unified stats payload & dashboard refresh

## Overview
- Replaced the legacy `/stats/progress` aggregation with a unified dashboard payload and enhanced 30-day insights.
- Refactored the React stats view to visualise the new metrics (progress, streaks, distribution, fulfilment, polarity, consistency).
- Hardened API caching behaviour and expanded test coverage (structure validation, cache busting, date guards).
- Applied minor DX fixes (TypeScript no-emit, stricter JWT parsing, safer file imports).

## Backend
- `backend/app.py`
  - Reworked `/stats/progress` to compute goal completion, streak, activity distribution, fulfilment averages, active-day ratio, polarity split, and top consistent activities in one response.
  - Added caching per-date (`stats::dashboard::<date>`); reused updates to invalidate caches on mutations.
  - Updated goal completion to use total `avg_goal_per_day` of active activities; streak now counts consecutive qualifying days (yesterday backwards) with a ratio ≥ 0.5.
  - Hardened JWT claim parsing, CSV import filenames, and import typing hints.
- `backend/extensions.py`
  - Marked Flask extension imports with `type: ignore` for static analyzers.

## Frontend
- `frontend/src/store/entriesSlice.js`, `frontend/src/api.js`
  - Adjusted stats thunk to consume the new payload shape (single snapshot + optional date).
- `frontend/src/components/Stats.jsx`
  - Replaced table-based view with dashboard widgets (progress meter, streak badge, pie, trend line, polarity bar, consistency bars) using shared Loading/Error components.
- `frontend/tsconfig.json`
  - Set `"noEmit": true` to prevent TypeScript from writing JS output during IDE checks.

## Tests
- `backend/tests/test_api.py`
  - Added payload structure assertions, invalid-date handling, and cache invalidation coverage for the new stats endpoint.
