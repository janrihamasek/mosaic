# Feature Ticket – T2 Activities Management

- Owner: Jan
- Priority: P1
- Status: Planned
- Related goals/OKRs: main_roadmap M1 (core loop), M2 (closed testing); tech_roadmap T2

## Context / Why
- Potřebujeme čistou správu aktivit (create/update/activate/deactivate/delete) s propagací do Entries/Today a konzistentními metadaty (category, goal, status).
- Současný stav: logika je rozptýlená mezi controller/service vrstvou, některé změny aktivit nepropagují do Entries/Today, chybí batch operace a UI je nejednotné v zobrazování kategorií.

## Scope
- In scope:
  - Backend: activities_service + propagation refactor (update entries při změně aktivit), batch akce (activate/deactivate/merge), kategorie/goal metadata konsolidace.
  - Frontend: UI pro batch akce a merge, jednotné zobrazení kategorií (hover/tooltip), úklid selectů (value/label), řazení aktivní → kategorie → název.
  - Data/DB: migrace/DDL pro potřebné sloupce (pokud chybí), ochrana proti orphan datům.
- Out of scope:
  - Wearables, analytics, NightMotion; nové typy aktivit mimo kategorii/goal.

## Acceptance / DoD
- [ ] Activity CRUD a batch akce (activate/deactivate/merge) dostupné v UI; backend endpointy pokrývají operace a vrací konzistentní payloady.
- [ ] Změna aktivity (název, kategorie, goal, status) se propíše do Entries/Today bez ručního zásahu; testy pokrývají propagaci.
- [ ] Kategorie a goal jsou povinné při vytváření/úpravě; validace/typy na FE i BE.
- [ ] UI zobrazuje kategorii jako tooltip/metadata napříč Today/Entries/Activities; selecty nepřidávají kategorie do labelu duplicitně.
- [ ] Třídění: Activities (active-first → category A–Z → activity A–Z), Entries: date desc → category → activity, Today: done state → category → activity.
- [ ] Testy: backend (service + endpoints) a frontend (reducer/komponenty) pro hlavní scénáře (CRUD, merge, batch, propagation).

## Plan & Links
- Milníky: M1 (základní provoz), M2 (stabilita pro testery).
- Roadmap: `Mosaic_Roadmaps/tech_roadmap.md#L1` (T2), `main_roadmap.md` (M1/M2).
- Templates: lze použít `templates/feature_ticket.md` pro další podúkoly.
- Archiv referencí: staré denní logy říjen/listopad v `backlog/october` a `backlog/november` (obsahují detailní požadavky na kategorie, řazení, batch).

## Notes
- Po implementaci aktualizovat kanban (`Mosaic_Roadmaps/roadmap_kanban.md`) a označit T2 u M1/M2 jako hotové, až DoD splněno.
