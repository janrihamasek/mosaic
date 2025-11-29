# Daily Log – 2024-11-04 to 2024-11-05

- Date: 2024-11-04 to 2024-11-05
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 4 - 5_11_mosaic.md

## Notes (raw import)

251104_backend_metrics_calculation
Goal:  
Define and document transparent computation logic for all analytics metrics in the Mosaic backend.
DONE
- **Shared Baseline** (mosaic_prototype/backend/app.py (lines 1240-1310)): Instead of using a single summed goal, we now track per-category goal totals and daily completion ratios (R_d, R_{d,c}) so we can derive category-specific metrics. The active_day ≥ 0.5 flag is introduced and reused for streaks and active-day ratios.
- **New Category Averages** (app.py (lines 1422-1459)): We assemble avg_goal_fulfillment_by_category by summing those per-category ratios over the previous 7 and 30 days (excluding the current day), returning a list of {category, last_7_days, last_30_days} blocks.
- **Polarity Shift** (app.py (lines 1375-1393)): “Positive” now means any entry with value > 0 and “negative” means value = 0, with the ratio dividing by max(negative, 1).
- **Consistency Carousel** (app.py (lines 1395-1459)): Instead of a single top-three list, we group activities by category, compute their active-day percentages, then emit the top three per category as the UI expects.
- **Documentation Alignment** (docs/METRICS.md (lines 1-152), mosaic_prototype/docs/API_DOCS.md (lines 300-350)): The written spec mirrors the new formulas, explicitly calls out the active_day threshold, category denominators, and payload shapes.
- **Contract Tests** (mosaic_prototype/backend/tests/test_api.py (lines 522-607)): Updated to assert the presence and structure of the new collections (avg_goal_fulfillment_by_category, top_consistent_activities_by_category) and still guard the numeric ranges.

251105_frontend_page_specs
Goal:
Create structured frontend page specifications for Mosaic.

Output:
frontend/docs/frontend_pages/{Today,Activities,Stats,Entries,NightMotion}.md and frontend/docs/frontend_pages/README.md
