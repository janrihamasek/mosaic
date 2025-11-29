# Daily Log – 2024-10-26

- Date: 2024-10-26
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 26_10_changes.md

## Notes (raw import)

Codex
**Technika dál**

- [x] Vytáhnout konfiguraci API URL do .env / build-time proměnných a doplnit fallback pro testy.
	- API klient teď bere základní URL z build-time proměnné a zároveň má jistý fallback. mosaic_prototype/frontend/src/api.js:1 přidává helper, který nejdřív sahá po REACT_APP_API_BASE_URL, jinak v testech i developmentu padá zpět na localhost (a zároveň odstřihává trailing slash). mosaic_prototype/frontend/.env.example:1 ukazuje výchozí hodnotu pro lokální vývoj. README.md:33 doplňuje instrukce ke kopírování .env.example a upravuje roadmapu, protože konfigurace už je vyřešená.
- [x] Přidat jednotné zpracování chyb a stavy načítání (spinner/toast), případně využít existující Notification.jsx.
	- Introduced reusable toast/loader styling and a variant-aware notifier rendered in the top-right corner (frontend/src/styles/common.js:98, frontend/src/components/Notification.jsx:4).
	- Centralized notification + loading management in the root component and wired it through forms, tables, detail, and “Today” views so every async path surfaces success/errors consistently and disables UI while busy (frontend/src/App.jsx:13, frontend/src/components/EntryForm.jsx:4, frontend/src/components/EntryTable.jsx:4, frontend/src/components/ActivityForm.jsx:4, frontend/src/components/ActivityTable.jsx:4, frontend/src/components/ActivityDetail.jsx:5, frontend/src/components/Today.jsx:5).
	- Hardened the REST client to throw on non-OK responses, ensuring the new handlers get reliable failure messages (frontend/src/api.js:17).
- [x] Zrychlit hromadné ukládání (Promise.all) a zvážit debounce/optimistický update v Today.
	- Parallelized manual save with Promise.all and added debounced auto-save that queues dirty rows and persists them optimistically (frontend/src/components/Today.jsx:1).
	- Surfaced pending/auto-saving status inline and wired select/input handlers to queue updates while keeping local state responsive (frontend/src/components/Today.jsx:74).
	- Exposed global toast styles for consistent messaging during these new flows (no extra change needed beyond prior update).
- [x] Doplnit backendové testy (pytest + Flask client), requirements a základní CI job.
	Backend Tooling
	- Added pinned backend deps and pytest tooling so local/CI environments install consistently (mosaic_prototype/backend/requirements.txt:1, .gitignore:1).
	- API now respects MOSAIC_DB_PATH, letting tests/CI point Flask at isolated SQLite files (mosaic_prototype/backend/app.py:9).
	- Documented install + test flow and the DB path override (README.md:42).
	Test Coverage
	- Introduced pytest config plus an initial suite covering activities, entries, today sheet, and finalize day behaviour (mosaic_prototype/backend/pytest.ini:1, mosaic_prototype/backend/tests/test_api.py:1).
	CI
	- New GitHub Actions job provisions Python, installs backend deps, and runs pytest with coverage on relevant pushes/PRs (.github/workflows/backend-tests.yml:1).
- [x] Rozšířit bezpečnost: validace vstupů, rate limiting, případně auth.
- [x] FE
	- Today
		- [x] zarovnat pole pro note tak, aby nepřekračovalo podklad
	- Entries
		- [x] zarovnat tlačítko Enter s řádkem
		- [x] přidat Import a Export CSV
	- Activities
		- [x] zarovnat tlačítka 
- [x] Activities
	- chtěl bych zavést pro aktivity kategorie.
	- důvody:
		- více možností pro budoucí statistiky
		- přehlednost, aktivity se budou řadit tematicky k sobě
	- pole Activity name v EntryForm přejmenovat na Activity
	- pole Name v EntryTable přejmenovat na Activity
	- EntryForm 
		- pole: Activity, Category, Description
		- button: Enter
	- EntryTable 
		- sloupce: Activity, Category, Description, Status
		- button: Deactivate (Activate/Delete)
	- řazení aktivit v tabulce bude nejprve podle Active/Inactive kdy aktivní jsou první a po nich neaktivní, v rámci toho dle kategorií od A do Z, pak v rámci kategorií podle Activity od A do Z.
	- bude potřeba přidat sloupec v databázi
	- v ostatních kartách se bude "Category" zobrazovat při najetí myší na název aktivity
- [x] Entries
	- chci přidat tlačítko pro import CSV, lze využít skript import_data.py
	- řazení aktivit v tabulce bude nejprve dle data od nejnovější po nejstarší, poté podle kategorií od A do Z, pak v rámci kategorií podle Activity od A do Z.
- [x] Today
	- řazení aktivit v tabulce bude nejprve dle provedeno(0)/provedeno(1,2,3,4,5) poté podle kategorií od A do Z, pak v rámci kategorií podle Activity od A do Z.