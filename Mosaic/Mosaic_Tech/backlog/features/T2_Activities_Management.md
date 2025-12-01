# Feature Ticket – T2 Activities Management

- Owner: Jan
- Priority: P1
- Status: Hotovo (merge odloženo na později)
- Related goals/OKRs: main_roadmap M1 (core loop), M2 (closed testing); tech_roadmap T2

## Aktuální stav
- Backend: `activities_service` + repo pokrývají CRUD, activate/deactivate/delete, batch endpoint `/activities/batch`, propagaci `category`/`description`/`activity_type`/`goal` do entries a invalidují cache `today`/`stats`; `name` je neměnné; merge flow odloženo.
- Frontend (Activities tab): `ActivityForm` a `ActivityDetail` validují kategorii (trim, goal=0 pro neutral/negative, frekvence fix 1×1 pro negative/neutral), `ActivityTable` má multi-select s batch activate/deactivate/delete, offline queue + snapshots, listener middleware ihned po mutacích dispatchuje `loadActivities/Today/Entries/Stats`. Řazení active → category → name, kategorie v column/tooltip.

## Scope
- Dokončit chybějící části: batch akce (BE+FE), okamžitější refresh/invalidation pro Today/Entries/Stats, UX/validace při editaci, testy. Merge flow nyní mimo scope.
- Out of scope: wearables, analytics, NightMotion; nové typy aktivit mimo category/goal.

## Acceptance / DoD (realita)
- [x] Backend service layer pro Activities, propagace metadat do Entries (category/goal/activity_type/description), invalidace cache `today`/`stats` pro CRUD/aktivace/deaktivace; validace frekvencí a activity_type.
- [x] UI: single-item CRUD (create/update/activate/deactivate/delete), řazení active → category → name, kategorie zobrazena (column + tooltip), offline queue + snapshots.
- [x] Batch akce (multi-select activate/deactivate/delete) – BE endpoint + FE UI hotovo. Merge flow pro tuto fázi neimplementujeme.
- [x] Okamžité refreshy Today/Entries/Stats po mutacích (listener nyní orchestruje přímé `load*` místo pouze `stale` flagu).
- [x] Validace/UX: FE blokuje prázdnou kategorii při editaci (in-line chyba, disable Save); `name` je neměnné (žádný rename); goal vstupy pro neutral/negative sjednoceny (goal=0, žádné frekvenční vstupy, jednotné messaging).
- [x] Testy: rozšířit backend coverage (activities_service/repo propagace) a frontend (activitiesSlice, listeners, ActivityDetail/Form/Table + offline queue).

## Plan & Links
- Milníky: M1 (základní provoz), M2 (stabilita pro testery).
- Roadmap: `Mosaic_Roadmaps/tech_roadmap.md#T2`, `main_roadmap.md` (M1/M2).
- Templates: lze použít `templates/feature_ticket.md` pro další podúkoly.
- Archiv referencí: staré denní logy říjen/listopad v `backlog/october` a `backlog/november` (detail kategorie/řazení/batch).

## Notes
- Označit T2 u M1/M2 jako hotové, až DoD splněno.
