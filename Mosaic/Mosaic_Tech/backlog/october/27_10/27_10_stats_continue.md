# Daily Log – 2024-10-27

- Date: 2024-10-27
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 27_10_stats_continue.md

## Notes (raw import)

1. struktura databází:
- entries(activities) má sloupce
	- e_id
	- date
	- activity (=name)
	- description (=description)
	- value
	- note
- activities(entries) má sloupce:
	- a_id
	- name (=activity)
	- category
	- goal
	- description (=description)
	- active
	- frequency_per_day
	- frequency_per_month
z toho vyplývá, že pokud vymažu aktivitu, přijdu o hodnoty category a goal. tyto hodnoty je tedy třeba ukládat i v tabulce entries.

2. pokud označím aktivitu na kartě Activities jako neaktivní, přestane se zobrazovat v listování časem zpět na kartě Today. to je špatně. musí se přestat zobrazovat od data, kdy byla deaktivována, ale zpětně musí být do data, kdy byla deaktivována viditelná.

Changes:
- Capture deactivation dates directly in the activities schema (adds deactivated_at with migration support) so history-aware queries can reason about when an activity stopped being active (mosaic_prototype/backend/app.py:44, mosaic_prototype/database/schema.sql:10, mosaic_prototype/backend/import_data.py:11).
- When deactivating or reactivating, persist the transition date and ensure Today/finalize queries include rows if the requested day predates that cutoff; insertions now seed deactivated_at as NULL for new activities (mosaic_prototype/backend/app.py:246, mosaic_prototype/backend/app.py:321, mosaic_prototype/backend/app.py:361, mosaic_prototype/backend/app.py:411).
- Updated CSV import helpers and API tests to handle the new column and to verify Today still shows a now-inactive activity for past dates while hiding it from the deactivation date onward (mosaic_prototype/backend/import_data.py:86, mosaic_prototype/backend/tests/test_api.py:13, mosaic_prototype/backend/tests/test_api.py:241).