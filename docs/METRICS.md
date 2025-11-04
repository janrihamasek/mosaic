# Mosaic Analytics Metrics

This document defines every metric returned by the backend endpoint `GET /stats/progress`. The goal is to provide reproducible, implementation-aligned formulas and naming so that backend, data, and frontend teams work from the same definitions.

## Scope and Windowing

- `T` — target date for the report. It equals the `date` query parameter in the request, or the current date if the parameter is omitted.
- All rolling metrics evaluate over the inclusive 30-day window `W30 = [T − 29, T]`.
- Activity metadata come from the `activities` table. Daily observations come from the `entries` table, where each row stores a snapshot of an activity's `category`, `goal` (as `activity_goal`), and the recorded `value`.
- All rounding follows Python's `round(value, 1)` (banker's rounding to one decimal place).

## Base Quantities

Let:

- `A_T` — set of activities that are active on `T`.  
- `G_total = Σ_{a ∈ A_T} goal_a` — sum of target goals for active activities. When `G_total ≤ 0`, all ratios defined below resolve to `0`.
- For each date `d ∈ W30`, let `V_d = Σ value` across all `entries` with `date = d`.
- The daily completion ratio is:

```
R_d = 0                                         if G_total ≤ 0
R_d = min( max(V_d, 0) / G_total, 1 )          otherwise
```

`R_d` is defined for all `d ∈ W30`. Days without entries contribute `V_d = 0`, hence `R_d = 0`.

## Example Dataset

The examples for each metric reuse the dataset below. Target date `T = 2024-06-01`.

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

With this dataset: `G_total = 2.0`. The daily ratios over `T` and the preceding six days are `[0.75, 0.95, 0.80, 0.30, 0.75, 0.00, 0.00]`.

## Metric Definitions

### Goal Completion Today (`goal_completion_today`)
- **Purpose** Measures how much of the combined daily targets were achieved on `T`.
- **Formula** `goal_completion_today = round(min(R_T, 1) * 100, 1)`. The clamp prevents values above 100%.
- **Dependencies** Uses `R_T` derived from `G_total` and the sum of entry values on `T`.
- **Example** `R_T = 0.75` ⇒ `goal_completion_today = round(0.75 × 100, 1) = 75.0`.

### Completion Streak (`streak_length`)
- **Purpose** Counts consecutive prior days with meaningful progress.
- **Logic**
  1. Evaluate days `d = T − 1, T − 2, …, T − 30`.
  2. Stop when encountering a day with no entries or `R_d < 0.5`.
  3. Return the number of days that satisfied `R_d ≥ 0.5`.
- **Dependencies** Uses `R_d`. The target date itself does not count toward the streak.
- **Example** Ratios for 2024-05-31 and 2024-05-30 are ≥ 0.5, while 2024-05-29 drops to 0.3. Hence `streak_length = 2`.

### Activity Distribution (`activity_distribution`)
- **Purpose** Shows how entry counts are distributed across activity categories in `W30`.
- **Formulae**
  - `count_c =` number of `entries` in `W30` whose `activity_category = c` (blank categories are labeled `"Other"`).
  - `percent_c = round((count_c / Σ count_c) * 100, 1)` with `0` when the denominator is `0`.
- **Sorting** The payload is ordered by `count_c` descending, then by lowercase category name ascending.
- **Example** Counts by category are Health = 5, Learning = 4, Wellness = 4 (total = 13). The distribution becomes:
  - Health — `38.5%`
  - Learning — `30.8%`
  - Wellness — `30.8%`

### Average Goal Fulfillment (`avg_goal_fulfillment`)
- **Purpose** Provides rolling completion percentages for the last 7 and 30 days (including `T`).
- **Formula** For window length `n ∈ {7, 30}`:

```
avg_goal_fulfillment[n] = round((Σ_{i=0}^{n-1} R_{T−i} / n) * 100, 1)
```

Days without entries contribute `R_d = 0`.
- **Example** `Σ R_d` over the last 7 days equals `3.55`, so `last_7_days = round((3.55 / 7) * 100, 1) = 50.7`. Over 30 days the sum remains `3.55`, giving `last_30_days = round((3.55 / 30) * 100, 1) = 11.8`.

### Active Days Ratio (`active_days_ratio`)
- **Purpose** Reports how many days in `W30` contain at least one entry.
- **Formulae**
  - `active_days = |{ d ∈ W30 | there exists an entry with date = d }|`
  - `total_days = 30`
  - `percent = round((active_days / 30) * 100, 1)` with `0` when `active_days = 0`.
- **Example** Entries exist on seven distinct dates, so `active_days = 7`, `percent = round(7 / 30 × 100, 1) = 23.3`.

### Positive vs Negative (`positive_vs_negative`)
- **Purpose** Captures polarity of entries relative to their snapshot goals.
- **Formulae**
  - `positive =` number of entries in `W30` where `value ≥ activity_goal`.
  - `negative =` number of entries in `W30` where `value < activity_goal`.
  - `ratio = round(positive / negative, 1)` when `negative > 0`; otherwise `ratio = round(float(positive), 1)` (mirrors the backend's fallback to the positive count).
- **Example** Positives = 8, negatives = 5, hence `ratio = round(8 / 5, 1) = 1.6`. The payload exposes `{ "positive": 8, "negative": 5, "ratio": 1.6 }`.

### Top Consistent Activities (`top_consistent_activities`)
- **Purpose** Highlights up to three activities with the broadest presence across the window.
- **Formulae**
  - For each activity `a`, `days_a = |{ d ∈ W30 | there exists an entry with activity = a on d }|`.
  - `consistency_percent_a = round((days_a / 30) * 100, 1)`.
- **Selection** Activities are sorted by `days_a` descending, then by lowercase activity name ascending. The top three are returned as objects `{ "name": a, "consistency_percent": consistency_percent_a }`.
- **Example** Running appears on 5 days, Meditation and Reading on 4 days each. The payload becomes:
  1. Running — `consistency_percent = 16.7`
  2. Meditation — `consistency_percent = 13.3`
  3. Reading — `consistency_percent = 13.3`

## Edge Cases and Implementation Notes

- When no activities are active (`G_total = 0`), all ratios (`R_d`) evaluate to `0`, yielding zeros across goal completion, averages, and streaks.
- Negative entry values contribute to `V_d` but are clamped to `0` before dividing by `G_total`, preventing negative completion ratios.
- All percentages are capped at `100.0` where relevant, ensuring consistent presentation for frontend dashboards.

