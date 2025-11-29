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
- Source: 25_10_changes.md

## Notes (raw import)

- [x] datum nahrané prostřednictvím skriptu import_data.py mají tvar DD/MM/YYYY, datum nahrané na kartách Today nebo Entries má tvar YYYY-MM-DD. je potřeba, aby bylo datum vždy uložené ve formátu YYYY-MM-DD.
- [x] tlačítka:
	-  Today/Save all changes - oznámení: "Changes saved", aktualizovat všechny karty
	-  Entries/Enter - oznámení: "Entry was saved" (stejný styl jako v Today), aktualizovat všechny karty
	- Entries/Delete - oznámení: "Entry was deleted" (stejný styl jako v Today), aktualizovat všechny karty
	- Activities/Enter - oznámení "Activity was created" (stejný styl jako v Today), aktualizovat všechny karty
	- Activities/Deactivate - oznámení "Deactivated" (stejný styl jako v Today), aktualizovat všechny karty
	- Activities/Activate - oznámení "Activated" (stejný styl jako v Today), aktualizovat všechny karty
	- Activities/Delete - oznámení "Activity was deleted" (stejný styl jako v Today), aktualizovat všechny karty
- [x] na kartě Activities defaultně řadit nejprve aktivní a pak neaktivní aktivity
- [x] karta entries musí někde končit ne být nekonečnou tabulkou, záznamy lze rolovat v rámci nějakého kontejneru a třeba po dvaceti záznamech mít tlačítko načíst další. všechny karty by měly být nějak ohraničené.

