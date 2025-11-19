# Mosaic – Roadmap (rev. 2025-11-16)

## 0. Architektura & stabilizace

-  Controllers → Services → Repositories (fázová refaktorizace)
    
-  Cache manager + namespaced cache keys
    
-  Redux mutation services + listeners
    
-  Guardrails (ESLint, flake8, CI import rules)
    
-  Normalizace API kontraktů + error envelope cleanup
    
-  Nová repo structure (`repo-structure.md`)
    
## 1. Daily Tracking

-  Migration Today/Entries do mutation services
    
-  Listener middleware místo kaskád
    
-  Negative / neutral entries
    
-  UI drobnosti (sorting, highlighting, layout)
    
-  Mood tracking (základní verze)
    
## 2. Activities Management

-  Merge aktivit (backend + UI)
    
-  Batch akce v UI
    
-  Propagation refactor přes service layer
    
-  Activity lineage
    
## 3. Analytics

-  Trends page (7/30/90)
    
-  Mood analytics
    
-  Negative habit scoring
    
-  Sliding windows ve stats_service
    
-  Prometheus export metrik
    
-  Daily aggregates refactor
    
## 4. Wearables (ETL + UI)

-  HR & Sleep canonicalization
    
-  `/wearable/trends` endpoints
    
-  Inspector upgrade (pagination, filters)
    
-  Ingest/ETL metriky (latence, duplicitnost)
    
-  Android offline cache + delta-sync
    
## 5. Admin Suite & Observability

-  User search + audit log
    
-  Logs pagination + filtering
    
-  Backup integrity tests (CI)
    
-  Wearable ingest metrics v `/healthz`
    
-  ONVIF + motion ingest (verze 1)
    
-  Motion → sleep analytics korelace
    
## 6. UX / UI Quality

-  TS migrace zbývajících komponent a slices
    
-  Layout consistency (Entries, Activities, Admin)
    
-  Tooltipy a hinty
    
-  Úpravy barev, kontrastů
    
-  Mobile-first layout pro Admin/Health/NightMotion
    
## 7. Mobile / PWA

-  Offline Today editor
    
-  Sync queue (Today & Activities)
    
-  Mobile dashboard (light Stats)
    
-  Push notifications
    
-  PWA offline shell + Workbox
    
## 8. Backups / Import-Export

-  Import wizard
    
-  Robustnější filename validation
    
-  Metadata models (checksums)
    
-  Automated restore test (CI)
    
## 9. Dokumentace & Specifikace

-  OpenAPI / Swagger
    
-  Developer guide (ETL, NightMotion, mutation flows)
    
-  ER diagram (vč. wearables)
    
-  Architecture overview