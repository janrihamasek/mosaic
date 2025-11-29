# Daily Log – 2024-10-25

- Date: 2024-10-25
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 22_10_changes.md

## Notes (raw import)

bylo by dobré, aby bylo možné v kartě activities kliknout na konkrétní aktivitu a tím otevřít jakýsi její přehled. otázkou je, jak se vypořádat s mazáním aktivit.
je potřeba, aby byly historické záznamy zachovány a mělo by být možné zobrazit statistiky již nevykonávané aktivity. taková aktivita by ale současně neměla být na výběr v selectu na kartě entries.
tím se nabízí dělit activities na aktivní a neaktivní. například mít u dané aktivity možnost ji nejprve deaktivovat a až poté definitivně vymazat. pak by se v selectu v entries zobrazovaly jen aktivity aktivní, v tabulce activities by ale mohly být jak aktivity aktivní tak neaktivní. deaktivovanou aktivitu by bylo možné buď opětovně aktivovat a tak ji přidat do selectu, nebo definitivně smazat, čímž by byla odstraněna z tabulky activities.
také se nabízí zobrazení today. to musí zobrazovat i aktivity, které nebyly v ten den zaznamenány (vykonány), ale jsou aktivní. tzn, že today (karta nebo cokoliv) zobrazuje všechny aktivní aktivity pro ten den. pokud se ten den vytvoří nová aktivita, je přidána do aktivit dne. pokud je ten den deaktivována nějaká aktivita, je odebrána z aktivit tohoto dne.
bylo by logické aby bylo možné měnit value přímo ve vypisu today. tím pádem si ale nejsem jistý významem všech karet dohromady.
