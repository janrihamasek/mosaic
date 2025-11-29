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
- Source: 23_10_changes.md

## Notes (raw import)

🔹 1. Fulltextové vyhledávání
✖️ nebude teď implementováno

🔹 2. Řazení a filtrování
Přidáno řazení kliknutím na hlavičky tabulky
Implementováno jak pro:
Entries (EntryTable.jsx)
Today (Today.jsx)
Umožní řadit podle Date, Activity, Value.

🔹 3. Automatické "Finalize Day" o půlnoci
Backend (app.py) dostane endpoint /finalize_day.
Ten zjistí, které aktivní aktivity nemají záznam pro daný den, a uloží je s hodnotou 0.
Frontend (Today.jsx) spustí kontrolu při každém načtení komponenty — pokud je čas po půlnoci nebo nový den, automaticky zavolá API.
(Pro lokální režim stačí kontrola, v budoucnu by se mohlo rozšířit na serverový cron.)

🔹 4. Barva splněných aktivit
Řádek na kartě Today se obarví světle zeleně (#d6f5d6), pokud value > 0.

🔹 5. Řazení nesplněné → splněné
Implicitní řazení na kartě Today podle value == 0 → value > 0.

🔹 6. Jedno tlačítko "Save All" + hláška
Z karty Today odstraněna individuální tlačítka „Save“.
Přidáno tlačítko "Save all changes" pod tabulku.
Po uložení všech záznamů se zobrazí krátká zelená hláška .

poznámky po implementaci:
- [x] na kartě Today nemá funkce řazení sloupců význam, postačí defaultní řazení na hotové a nehotové.
- [x] tlačítko Save all changes přemístit nahoru na řádek s polem Date, úplně doprava
- [x] vidím v tabulce Entries jen záznamy, které jsem nahrál z csv, když přiřadím aktivitě hodnotu na kartě Today, mělo by se to objevit také jako nový záznam na kartě Entries


