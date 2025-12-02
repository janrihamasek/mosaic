# Feature Ticket – T5 Backups / Import–Export

- Owner: Jan
- Priority: P1
- Status: Planned
- Related goals/OKRs: tech_roadmap T5; main_roadmap M1 (operátorská stabilita)

## Aktuální stav
- Backend: `backup_controller` + `services/backup_service` existuje, `BackupManager` umí vytvářet ZIP/JSON/CSV backup, běží scheduler, repo má `backup_settings`; validace filename je minimální.
- Frontend: Admin Backup panel umí run/toggle/download, používá `backupSlice`; import wizard chybí, export metadata/hash se neposílají.
- Testy: základní API testy `tests/test_backup_manager.py` pokrývají run/toggle/download, ale chybí hash/validace/import/export serializéry.

## Scope
- Vylepšit robustnost backupů: oddělit controller/service zcela od filesystem detailů, zpevnit scheduler a validace názvů, doplnit integritu (hash + timestamp) a konzistentní serializéry JSON/CSV.
- Dodat import/export UX: frontend wizard pro import (upload → validace → preview → confirm), zlepšit backup panel (interval presets, stav scheduleru, metadata).
- Testy/CI: vyšší coverage backendu a thunk/UX testy pro backup/import, případně lint/guardrails pro layering.
- Out of scope: šifrování backupů, plnohodnotný restore; wearables/analytics.

## Acceptance / DoD
- [x] Backup service vrací konzistentní metadata (timestamp, hash, velikost, poslední běh) a controller je jen orchestrace HTTP.
- [x] Validace filename i import payloadu pokrývá path traversal, pattern `backup-<ts>.<ext>`, typy a limity; chyby vrací `ValidationError`.
- [x] Export JSON/CSV sdílí jednu schema definici; CSV/JSON klíče jsou stabilní a dokumentované.
- [ ] Scheduler respektuje `backup_settings` (enabled/interval), per-run ukládá `last_run` a loguje chyby; status endpoint zobrazuje stav.
- [ ] Import wizard na FE: kroky upload → serverová validace/dry-run → preview → confirm, chyby zobrazí v UI; žádný přímý `apiClient` v komponentách.
- [ ] UX backup panel: interval presets, běžící/stop scheduler indikátor, disable/loader pro „Run now“, zobrazuje metadata (hash/timestamp/size).
- [ ] Testy: backend unit/integration pro validace/hash/serializéry/scheduler, frontend thunk + komponentové testy wizardu/backup panelu; CI joby spouštějí nové testy.

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
