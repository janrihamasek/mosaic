# Daily Log – 2024-11-13

- Date: 2024-11-13
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 13_11_mosaic.md

## Notes (raw import)

soubor má deset listů:
january, february, march, april, may, june, july, august, september, october
v každém listě je tabulka náležející k měsíci v názvu listu:
sloupec A řádky 2 - 11 = Name (název aktivity)
sloupce B - AF řádek 1 = Date (dd/mm/yyyy)
sloupce B - AF řádky 2 - 11 = Value (num)
převeď všechny tabulky do jednoho csv souboru se sloupci:
date,activity,value,note,description,category,goal
pokud chybí note: nechat prázdné
pokud chybí description: nechat prázdné
pokud chybí category: "General"
pokud chybí goal: 1

251113_frontend_admin_access_and_import_scope
Goal: Make Admin → User and Admin → Settings visible to all users, while keeping other sections admin-only; verify CSV import always assigns records to the authenticated user.  
DONE
- Allowed all users to access the User and Settings tabs by filtering sections with PUBLIC_SECTION_IDS (mosaic_prototype/frontend/src/components/Admin.jsx (line 23), Admin.jsx (line 28)) while the existing effect at Admin.jsx (line 40) still resets activeSection whenever visibility changes.
- Documented that the CSV import helper only appends the uploaded file so user_id is never sent (mosaic_prototype/frontend/src/api.js (line 138)), keeping backend scoping aligned with the authenticated user.
**Admin Visibility**
- “User” and “Settings” tabs now bypass the admin filter while all other panels stay admin-only, and the active section resets to the first available tab whenever visibility changes so non-admins always land on a shown panel (mosaic_prototype/frontend/src/components/Admin.jsx:14-44).
- The Dashboard always exposes the “Admin” tab, which lets everyone open the component while still leaving section access scoped on the inside (mosaic_prototype/frontend/src/Dashboard.jsx:62-110).
- The CSV import helper now only appends the file payload (no user_id), relying on the backend to scope records to the signed-in user (mosaic_prototype/frontend/src/api.js:138-145).

--- code freeze ---

