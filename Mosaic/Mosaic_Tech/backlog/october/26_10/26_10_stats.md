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
- Source: 26_10_stats.md

## Notes (raw import)

max 5 x týdně
max 3 x denně
15 bodů za 7 dnů
30 bodů za 14 dnů
60 bodů za 28 dnů
63 bodů za 29 dnů
66 bodů za 30 dnů
69 bodů za 31 dnů

Mosaic je určen pro denní záznamy aktivit za účelem vysledování dlouhodobých trendů a případných závislostí mezi měřenými aktivitami.
Každá aktivita (jídlo, cvičení, hra na nástroj...) náleží do kategorie (health, workout, arts...), která má širší rozsah a obvykle sdružuje více aktivit, čímž vytváří segment, který lze dále sledovat a vyhodnocovat jako celek.
Každé aktivitě lze udělit 0 - 5 bodů.
0 znamená, že se aktivita nekonala, bodové ohodnocení pak nějakou její kvalitu, počet apod. Podstatné je, kolik bodů chce člověk za měsíc "nasbírat". Řekněme, že chceme každý druhý den chodit na procházku. To je za měsíc patnáct dní, tedy patnáct bodů. Můžeme jít víckrát za den a získáme více bodů. Několik dní nejdeme, nezískáme nic. Ze získaných bodů a požadovaných bodů za měsíc získáme procentuelní vyjádření úspěšnosti našeho snažení.
Na kartě Activities je tedy potřeba přidat input Goal, který bude přijímat "požadovanou četnost za dané období" dané aktivity. Activity, Category i Goal musí být mandatory, pouze Description optional. Bude potřeba přidat další sloupec v databázi.
Jak bys to udělal?

**Backend**

- Added per-activity goals to the schema, loader, and API: ensure_schema backfills the column on existing DBs, endpoints now persist and return goal, and validation enforces integer goals (mosaic_prototype/backend/app.py:24, mosaic_prototype/backend/security.py:96, mosaic_prototype/backend/import_data.py:27).
- CSV import accepts the new goal column, trims inputs, auto-creates/updates activities, and the upload endpoint streams FormData straight into the importer with rate limiting (mosaic_prototype/backend/import_data.py:55, mosaic_prototype/backend/app.py:331).
- Test suite extended for goal handling, CSV upload, and validation edge cases; fixtures reset the lazy schema flag so migrations run against temp DBs (mosaic_prototype/backend/tests/test_api.py:10, mosaic_prototype/backend/tests/conftest.py:10).

**Frontend**

- Activity creation now captures Activity, Category, Goal, and an optional description; values are coerced to non-negative integers before posting (mosaic_prototype/frontend/src/components/ActivityForm.jsx:4).
- Activity listing shows goal/category metadata, keeps the requested sorting (active-first → category → name), and tooltips expose category info everywhere it’s relevant, including Today and Entry views (e.g. mosaic_prototype/frontend/src/components/ActivityTable.jsx:31, mosaic_prototype/frontend/src/components/EntryForm.jsx:11, mosaic_prototype/frontend/src/components/Today.jsx:16).
- Entries tab has a CSV import button wired to the backend uploader, and both tables respect the updated sorting/column requirements (mosaic_prototype/frontend/src/App.jsx:112, mosaic_prototype/frontend/src/components/EntryTable.jsx:34).