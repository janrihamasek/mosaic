# Daily Log – 2024-10-28

- Date: 2024-10-28
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 28_10_entries_refactoring.md

## Notes (raw import)

Změny na kartě Entries.
Účel:
EntryForm budeme používat pro nastavení parametrů, na základě kterých se nám zobrazí seznam Entries v tabulce v EntryTable.
Změny:
EntryForm bude nově obsahovat:
1. pole pro výběr data 
	- možnosti: zvolit jeden den, celý měsíc, období od-do, speciální volba: "all time" (zobrazí všechny záznamy)
	- defaultně: "all time" (všechny záznamy chronologicky od dnes zpětně)
2. select "Activity"
	- lze volit jednotlivě ze všech aktivit (aktivní i neaktivní) nebo variantu all activities (všechny aktivity)
	- defaultně: "all activities" (všechny aktivity aktivní i neaktivní)
3. select "Category"
	- lze volit jednotlivě ze všech kategorií nebo variantu all categories (všechny najednou)
	- defaultně: "all categories" (všechny kategorie)
4. button "Enter"
	- aplikuje výběr na záznamy v tabulce
5. button "Import CSV"
	- funkcionalita se nemění
- select pro volbu value a input Note se odstraní
EntryTable bude nově obsahovat sloupce:
1. Date
2. Activity
3. Category
4. Goal
a tlačítko "Delete" s nezměněnou funkcionalitou.
Doporučení (volitelné, ale vhodné):
- Vyčistit tabulku po změně filtrů, než se načtou nové výsledky.
- Přidat Loading indikátor.
- Možnost exportu filtrovanych výsledků do CSV (připravit do budoucna).