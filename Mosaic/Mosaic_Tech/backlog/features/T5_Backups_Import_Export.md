# Feature Ticket – T5 Backups / Import–Export

- Owner: Jan
- Priority: P1
- Status: In progress
- Related goals/OKRs: tech_roadmap T5; main_roadmap M1 (operátorská stabilita)

## Aktuální stav
- Backend: `backup_controller` + `backup_service` + `BackupManager` se schedulerem a `backup_settings`. Export `/export/csv|json` sdílí schema (entries+activities), zvýšen default limit na 10k (max 20k). Import z exportního CSV podporuje dataset `activities` i `entries` a u aktivit aplikuje goal/type/frequency/deactivated_at. Přidán endpoint DELETE `/user/data` pro wipe dat uživatele.
- Frontend: Admin Backup panel (run/toggle/download, interval presets, stav scheduleru, metadata posledního backupu, loaders) a Import wizard (upload → server dry-run → preview → confirm) v sekci Admin/Data.
- Testy: základní backup API testy + nové unit testy pro hash/pattern/serializéry a FE testy exportních tlačítek; zbývají případné CI guardrails.

## Scope
- Zpevnit backupy (hotovo): validace filename/path traversal, hash+timestamp v metadata, dokumentované CSV/JSON serializéry, scheduler/logování.
- UX polish: doplnit metadata/hash do UI, další stavové indikátory pro backup panel, případné vylepšení wizardu.
- Testy/CI: backend coverage (hash/serializéry/filename), frontend thunk/UX testy wizardu a backup panelu, guardrails/linty v CI.
- Out of scope: šifrování backupů, plnohodnotný restore; wearables/analytics.

## Acceptance / DoD
- [x] Backup service vrací metadata (timestamp/hash/size/last_run), controller je orchestrátor HTTP; hash/validace pokryto.
- [x] Validace filename/import payloadu pokrývá pattern `backup-<ts>.<ext>` a path traversal.
- [x] Export JSON/CSV sdílí jednu schema definici; klíče jsou stabilní a dokumentované v kódu.
- [x] Scheduler respektuje `backup_settings` (enabled/interval), ukládá `last_run`, stav se zobrazuje.
- [x] Import wizard na FE: upload → server dry-run → preview → confirm, chyby v UI; bez přímého `apiClient` v komponentách.
- [x] UX backup panel: interval presets, stav scheduleru, disable/loader, metadata posledního backupu.
- [x] Testy: backend unit/integration pro hash/serializéry/filename/scheduler; FE export/import UI testy přidané; CI guardrails spouštějí nové testy.

## Plan & Links
- Milníky:
  - M1 Backend hardening: zpevnit `get_backup_path` (pattern/length/..), přidat hash+size+timestamp do metadata z `create_backup`, scheduler persistuje `last_run` a respektuje `backup_settings`, logování chyb.
  - M2 Export/import API: sjednotit JSON/CSV schema, endpoint vrací metadata, přidat import endpoint s validací/dry-run, aktualizovat API docs.
  - M3 Frontend: backup panel (interval presets, scheduler status, metadata, lepší loaders), import wizard (upload → server validate → preview → confirm) přes `backupSlice`/nový `importSlice`.
  - M4 Testy/CI: unit/integration backend (validace, hash, serializéry, scheduler), FE thunk+UI testy wizardu/panelu, CI joby rozšířit o nové testy + layering lint pokud přidáme nové moduly.
- Designs / specs: vycházet z `docs/architecture/layering-rules.md`, `guardrails.md`, `redux-flow.md` (backupSlice), `repo-structure.md` (controller/service/repo).
- Dependencies: backend `backup_manager`, `backup_repo`, `backup_slice` thunky; Admin routes/permissions.

## Notes
- Při refaktoru držet se layering guardrails (žádný Flask v services, controller nevolá repo přímo). Export/import kontrakty zdokumentovat v API docs a případné nové výjimky zapsat do `layering-rules.md`.
