# Mosaic

Shrnutí co je kde, aby se v projektu dalo rychle orientovat.

## Rychlé odkazy
- **Now (vyplň):** [aktuální sprint/týden](#now) · [poslední log](Mosaic_Tech/backlog/) · [top priority backlog](Mosaic_Tech/backlog/features)
- Business: `Mosaic_Business/` (persóny, profily, úvodní poznámky)
- Roadmaps: `Mosaic_Roadmaps/` (`main_roadmap.md`, `bussiness_roadmap.md`, `tech_roadmap.md`, `roadmap_kanban.md`)
- Matice priorit: `Mosaic_Roadmaps/matrix/` (tech, business, inovace, backend refaktor)
- Tech pravidla: `Mosaic_Tech/rules/` (zásady, workflow, prompt spec)
- Tech backlog: `Mosaic_Tech/backlog/` (features + datované logy)
- Docker manuál: `Mosaic_Tech/docker_manual.md`

## Struktura
- `Mosaic_Business/` – business pohled, profily a brainstorming; např. `Mosaic - Business LCH.md`, `Mosaic - Business GPT.md`, `profile.md`.
- `Mosaic_Roadmaps/` – hlavní roadmapy pro byznys i tech; matice v `matrix/` pro priority a refaktoring.
- `Mosaic_Tech/` – technická část:
  - `rules/` – zásady správy konverzací a workflow (`Mosaic – Zásady správy konverzací a archivace.md`, `prompt_specification_compact_codex_instruction.md`, `workflow.md`).
  - `backlog/` – `features/` (návrhy funkcí, architektura osobních dat, NightMotion, core metrics) a datované logy (`october/`, `november/`).
  - `docker_manual.md` – poznámky k dockeru.

## Now
- Sprint/týden: _vyplň (např. 2025-W11)_
- Top 3 priority: _vyplň krátké bullets_
- Odkazy: _poslední denní log_, _plán sprintu_, _hlavní roadmapa_

## Jak psát logy a úkoly
- Denní log: použij šablonu z `templates/daily_log.md`, ukládej jako `Mosaic_Tech/backlog/YYYY-MM-DD.md` nebo do složky týdne (`backlog/november/` zachovej kvůli historii).
- Týden/Sprint: šablona `templates/week_review.md` pro review/plan, odkazuj na denní logy.
- Feature ticket: šablona `templates/feature_ticket.md`, ukládej do `backlog/features/`.
- Rozhodnutí (ADR): šablona `templates/adr.md`, ukládej do `Mosaic_Tech/rules/` nebo `Mosaic_Tech/backlog/adr/` (dle preference).

## Šablony
- `templates/daily_log.md` – denní zápis (co bylo, blokery, rozhodnutí, odkazy).
- `templates/week_review.md` – shrnutí týdne/sprintu + plán dalšího.
- `templates/feature_ticket.md` – popis funkce, scope, DoD, priority, odkazy.
- `templates/adr.md` – záznam architektoního/produktového rozhodnutí.

## Poznámka k backlogu
- `backlog/features/` – návrhy a větší položky; označ priority/status v hlavičce.
- `backlog/october/` a `backlog/november/` – historické denní zápisy/deliverables; můžeš je postupně přesouvat nebo nechat jako archiv.
