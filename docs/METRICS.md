# Mosaic Analytics Metrics

This document specifies every metric returned by the backend endpoint `GET /stats/progress`. Definitions mirror the production implementation so that backend, data, and frontend teams can align on consistent formulas, naming, and rounding.

## Scope and Windowing

- `T` — target date for the report. The endpoint uses the `date` query parameter when provided, otherwise the current date.
- Rolling calculations use the inclusive window `W30 = [T − 29, T]`.
- Each activity stores an average daily reference value `goal` derived from its configured weekly and daily cadence. The backend snapshots this value into `entries.activity_goal` whenever an entry is created or updated.
- Unless noted otherwise, rounding applies Python's `round(value, 1)` (banker's rounding) to produce one decimal place.

## Base Quantities

- `A_T` — set of activities that are active on date `T`.
- `goal_a` — average daily reference for activity `a ∈ A_T`.
- `G_total = Σ_{a ∈ A_T} goal_a` — combined reference baseline for `T`. If `G_total ≤ 0`, all ratios defined below resolve to `0`.
- For each category `c`, `G_total,c = Σ goal_a` across active activities with category `c`.
- For any date `d ∈ W30`:
  - `V_d = Σ value` across all entries whose `date = d`.
  - `V_{d,c} = Σ value` across entries on `d` with `activity_category = c` (empty categories are treated as `"Other"`).
- Daily completion ratios:

```
R_d = 0                                                  if G_total ≤ 0
R_d = min(max(V_d, 0) / G_total, 1)                      otherwise

R_{d,c} = 0                                              if denominator_c(d) ≤ 0
R_{d,c} = min(max(V_{d,c}, 0) / denominator_c(d), 1)     otherwise
```

  where `denominator_c(d) = max(G_total,c, Σ activity_goal for entries on d in category c)`. This fallback lets historical entries for inactive categories contribute meaningfully.

- Active-day indicator used for streaks and productivity ratios:

```
active_day(d) = True  if R_d ≥ 0.5
               False otherwise
```

The 0.5 threshold matches the frontend transition from red to green on the "Today progress" bar.

## Example Dataset

The examples below reuse the same dataset with target date `T = 2024-06-01`.

| Activity   | Category | Goal |
|------------|----------|------|
| Running    | Health   | 1.0  |
| Reading    | Learning | 0.5  |
| Meditation | Wellness | 0.5  |

| Date       | Activity   | Category | Stored Goal | Value |
|------------|------------|----------|-------------|-------|
| 2024-06-01 | Running    | Health   | 1.0         | 0.8   |
| 2024-06-01 | Reading    | Learning | 0.5         | 0.5   |
| 2024-06-01 | Meditation | Wellness | 0.5         | 0.2   |
| 2024-05-31 | Running    | Health   | 1.0         | 1.0   |
| 2024-05-31 | Reading    | Learning | 0.5         | 0.4   |
| 2024-05-31 | Meditation | Wellness | 0.5         | 0.5   |
| 2024-05-30 | Running    | Health   | 1.0         | 1.1   |
| 2024-05-30 | Reading    | Learning | 0.5         | 0.5   |
| 2024-05-29 | Running    | Health   | 1.0         | 0.6   |
| 2024-05-28 | Running    | Health   | 1.0         | 1.0   |
| 2024-05-28 | Meditation | Wellness | 0.5         | 0.5   |
| 2024-05-27 | Reading    | Learning | 0.5         | 0.0   |
| 2024-05-25 | Meditation | Wellness | 0.5         | 0.5   |

Within this window:

- `G_total = 2.0`.
- Overall daily ratios for `T` and the six preceding days are `[0.75, 0.95, 0.80, 0.30, 0.75, 0.00, 0.25]`.
- `active_day` evaluates to `True` on 2024-05-31, 2024-05-30, and 2024-05-28; it is `False` otherwise.
- Category ratios on those same days are:
  - Health (`G_total,c = 1.0`): `[0.80, 1.00, 1.00, 0.60, 1.00, 0.00, 0.00]`
  - Learning (`G_total,c = 0.5`): `[1.00, 0.80, 1.00, 0.00, 0.00, 0.00, 0.00]`
  - Wellness (`G_total,c = 0.5`): `[0.40, 1.00, 0.00, 0.00, 1.00, 0.00, 1.00]`

## Metric Definitions

### Goal Completion Today (`goal_completion_today`)
- **Purpose** Measures how much of the combined reference goals were achieved on `T`.
- **Formula** `goal_completion_today = round(min(R_T, 1) * 100, 1)`.
- **Example** `R_T = 0.75` ⇒ `goal_completion_today = 75.0`.

### Completion Streak (`streak_length`)
- **Purpose** Counts consecutive productive days immediately preceding `T`.
- **Logic**
  1. Inspect `d = T − 1, T − 2, …, T − 30`.
  2. Stop at the first `d` with `active_day(d) = False`.
  3. Return the number of inspected days that satisfied `active_day(d) = True`.
- **Example** As only 2024-05-31 and 2024-05-30 are active preceding days, `streak_length = 2`.

### Activity Distribution (`activity_distribution`)
- **Purpose** Shows how entry counts spread across activity categories within `W30`.
- **Formulae**
  - `count_c =` number of entries with category `c`.
  - `percent_c = round((count_c / Σ count_c) * 100, 1)` (0 when the denominator is 0).
- **Sorting** Buckets are ordered by `count_c` descending, then case-insensitive category name ascending.
- **Example** Health = 5 entries, Learning = 4, Wellness = 4 ⇒ `[{"category": "Health", "count": 5, "percent": 38.5}, …]`.

### Average Goal Fulfillment (`avg_goal_fulfillment`)
- **Purpose** Provides rolling completion percentages that still include the current day `T`.
- **Formula** For window `n ∈ {7, 30}`:

```
avg_goal_fulfillment[n] = round((Σ_{i=0}^{n−1} R_{T−i} / n) * 100, 1)
```

- **Example** Over the seven most recent days (including `T`), the sum of ratios equals `3.55`, so `last_7_days = 50.7`. Over 30 days the sum remains `3.55`, yielding `last_30_days = 11.8`.

### Average Goal Fulfillment by Category (`avg_goal_fulfillment_by_category`)
- **Purpose** Surfaces rolling completion for each category, excluding the current day `T`.
- **Formula**

```
avg_goal_fulfillment_by_category[c][n] = round((Σ_{i=1}^{n} R_{T−i,c} / n) * 100, 1)
```

  where `n ∈ {7, 30}`.
- **Payload Shape** List of objects `{ "category": c, "last_7_days": value, "last_30_days": value }`, sorted by category name.
- **UI** Exposed via a carousel in the dashboard so users can cycle through categories.
- **Example**
  - Health: `(1.0 + 1.0 + 0.6 + 1.0 + 0 + 0 + 0) / 7 × 100 ≈ 51.4`, `(same sum) / 30 × 100 = 12.0`.
  - Learning: `25.7` over 7 days, `6.0` over 30 days.
  - Wellness: `42.9` over 7 days, `10.0` over 30 days.

### Active Days Ratio (`active_days_ratio`)
- **Definition** A day is active when `active_day(d) = True`.
- **Formulae**
  - Count active days across `d ∈ [T − 29, T − 1]`.
  - `active_days_ratio = round((count / 30) * 100, 1)` with `count = |{ d | active_day(d) = True }|`.
  - The payload retains the structure `{ "active_days": count, "total_days": 30, "percent": value }`.
- **Example** Three of the previous 30 days are active, hence `percent = round(3 / 30 × 100, 1) = 10.0`.

### Positive vs Negative (`positive_vs_negative`)
- **Purpose** Splits recent entries into “performed” (value > 0) and “not performed” (value = 0).
- **Formulae**
  - `positive = |{ entry ∈ W30 | value > 0 }|`.
  - `negative = |{ entry ∈ W30 | value = 0 }|`.
  - `ratio = round(positive / max(negative, 1), 1)`.
- **Example** With 12 positive entries and one zero entry, the payload is `{ "positive": 12, "negative": 1, "ratio": 12.0 }`.

### Top Consistent Activities by Category (`top_consistent_activities_by_category`)
- **Purpose** Highlights up to three activities per category with the broadest presence across `W30`.
- **Formulae**
  - For each activity `a`, `days_a = |{ d ∈ W30 | ∃ entry(activity = a, date = d) }|`.
  - `consistency_percent_a = round((days_a / 30) * 100, 1)`.
- **Payload Shape** List of category buckets `{ "category": c, "activities": [ { "name": a, "consistency_percent": value }, … ] }`, limited to three activities per category and ordered by category name.
- **UI** Rendered as a carousel where the user can browse categories to see their leading activities.
- **Example**
  - Health → Running present on 5 days ⇒ `16.7`.
  - Learning → Reading present on 4 days ⇒ `13.3`.
  - Wellness → Meditation present on 4 days ⇒ `13.3`.

## Edge Cases and Implementation Notes

- When no activities are active on `T`, ratios default to `0`, which propagates through completion metrics and active-day logic.
- Category denominators fall back to per-entry goal snapshots, ensuring historical data for inactive categories still yield ratios.
- Negative entry values are clamped to `0` before dividing by denominators to prevent negative percentages.
- The 0.5 threshold in `active_day` centralises all logic that depends on “meaningful progress” (streaks and active-day ratios).
- `positive_vs_negative` treats zero values as the only “negative” count; the ratio always divides by at least one thanks to `max(negative, 1)`.
