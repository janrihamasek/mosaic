# Backlog a logy

Jak psát a organizovat zápisy, aby byly konzistentní.

## Struktura (doporučení)
- Denní logy: `backlog/YYYY-MM-DD.md` nebo ve složkách typu `backlog/november/2024-11-08.md` (dnešní strukturu říjen/listopad nech jako archiv).
- Týden/sprint: `backlog/week-YY-WW.md` nebo v samostatné složce týdne.
- Feature tickets: `backlog/features/*.md` (použij šablonu).
- ADR: `backlog/adr/*.md` nebo v `Mosaic_Tech/rules/` (použij šablonu).

## Šablony
- Denní log: `../../templates/daily_log.md`
- Týden/sprint: `../../templates/week_review.md`
- Feature ticket: `../../templates/feature_ticket.md`
- ADR: `../../templates/adr.md`

## Metadata a tagy
- V úvodu přidej priority/status, např.: `Priority: P1`, `Status: In Progress`.
- Tagy do textu pro rychlé hledání: `#frontend`, `#backend`, `#infra`, `#P1`, `#ADR`, `#risk`.

## Odkazy
- Roadmapy: `../../Mosaic_Roadmaps/`
- Tech pravidla: `../rules/`
