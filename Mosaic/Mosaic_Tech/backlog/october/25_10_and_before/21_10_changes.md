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
- Source: 21_10_changes.md

## Notes (raw import)

V aplikaci jsou dvě karty, mezi kterými lze přepínat.
1. karta Entries - obsahuje komponenty EntryForm a EntryTable
2. karta Activities - obsahuje komponenty ActivityForm a ActivityTable
EntryForm
Obsahuje čtyři pole: date, activity, value a note; a tlačítko Enter, pro uložení záznamu.
EntryTable
Obsahuje tabulku se čtyřmi sloupci: date, activity, value, note; a u každého záznamu tlačítko Delete pro smazání záznamu.
ActivityForm
Obsahuje dvě pole: Activity name a Description; a tlačítko Enter pro uložení aktivity.
ActivityTable
Obsahuje tabulku se dvěma sloupci: Name a Description; a u každého záznamu tlačítko Delete pro smazání aktivity.
Nyní jsou aktivity na kartě Entries dané na pevno v kódu souboru EntryForm.jsx. Activity, které je možné vytvořit na kartě Activities s aktivitami v Entries nijak nesouvisí. To je potřeba změnit tak, aby se aktivity, vytvořené na kartě Activity nabízeli jako možnost v selectu na kartě Entries. Zároveň je potřeba rozšířit tabulku entries v databázi o sloupec description. Scénář je takový, že uživatel vytvoří na kartě Activity několik aktivit, které krátce popíše. Následně na kartě entries vybere den, aktivitu a hodnotu, možná připíše poznámku a zaznamená aktivitu, kterou si zvolil ze svých dříve uložených. Na kartě entries se u zaznamenaných aktivit description nezobrazuje, ale v databázi musí být v tabulce entries, aby smazáním aktivity na kartě activities nedošlo ke ztrátě původní description.
Shrň v pár větách charakteristiku nové funkcionality a jejích vlastností a navrhni jak ji implementovat v rámci celého repozitáře