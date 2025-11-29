# Feature Ticket – T2 Activities Management

- Owner: Jan
- Priority: P1
- Status: V řešení (část dodaná)
- Related goals/OKRs: main_roadmap M1 (core loop), M2 (closed testing); tech_roadmap T2

## Aktuální stav
- Backend: `activities_service` oddělené od controllerů, validace Pydantic (frekvence 1–3/den, 1–7/týden, goal=0 pro neutral/negative). Update propaguje `category`/`description`/`activity_type`/`goal` do všech entries dané aktivity, invaliduje cache `today`/`stats`; neexistují batch ani merge endpointy a `name` nelze měnit.
- Frontend (Activities tab): `ActivityForm` vytváří aktivitu (goal pro negative/neutral = 0, frekvence fixně 1×1), `ActivityDetail` modal umožňuje editaci kategorie/typu/frekvencí/description, ale `name` je read-only. Mutace používají offline queue + snapshots, emitují mutation events; listener middleware pouze značkuje slices jako `stale`, refresh proběhne při přepnutí na tab nebo pokud data „zestárnou“ (>60 s). Žádné batch akce ani merge UI. Řazení active → category → name implementováno, kategorie se zobrazuje v tabulce i tooltipu.
- Propagace do Today/Entries/Stats se spoléhá na staleness + refresh v `Dashboard` (nikoli na okamžité cascades v thuncích). Backend už při update doplňuje metadata v `entries`.

## Scope
- Dokončit chybějící části: batch akce (BE+FE), okamžitější refresh/invalidation pro Today/Entries/Stats, UX/validace při editaci, testy. Merge flow nyní mimo scope.
- Out of scope: wearables, analytics, NightMotion; nové typy aktivit mimo category/goal.

## Acceptance / DoD (realita)
- [x] Backend service layer pro Activities, propagace metadat do Entries (category/goal/activity_type/description), invalidace cache `today`/`stats` pro CRUD/aktivace/deaktivace; validace frekvencí a activity_type.
- [x] UI: single-item CRUD (create/update/activate/deactivate/delete), řazení active → category → name, kategorie zobrazena (column + tooltip), offline queue + snapshots.
- [ ] Batch akce (multi-select activate/deactivate/delete) – chybí BE endpoints i FE UI. Merge flow pro tuto fázi neimplementujeme.
- [ ] Okamžité refreshy Today/Entries/Stats po mutacích (aktuálně jen `stale` flag + reload při návratu na tab/po 60 s); rozhodnout, zda listener orchestruje přímo `load*` nebo přidat optimistické update.
- [x] Validace/UX: FE blokuje prázdnou kategorii při editaci (in-line chyba, disable Save); `name` je neměnné (žádný rename); goal vstupy pro neutral/negative sjednoceny (goal=0, žádné frekvenční vstupy, jednotné messaging).
- [ ] Testy: rozšířit backend coverage (activities_service/repo propagace) a frontend (activitiesSlice, listeners, ActivityDetail/Form/Table + offline queue).

## Plan & Links
- Milníky: M1 (základní provoz), M2 (stabilita pro testery).
- Roadmap: `Mosaic_Roadmaps/tech_roadmap.md#T2`, `main_roadmap.md` (M1/M2).
- Templates: lze použít `templates/feature_ticket.md` pro další podúkoly.
- Archiv referencí: staré denní logy říjen/listopad v `backlog/october` a `backlog/november` (detail kategorie/řazení/batch).

## Notes
- Po implementaci aktualizovat kanban (`Mosaic_Roadmaps/roadmap_kanban.md`) a označit T2 u M1/M2 jako hotové, až DoD splněno.
