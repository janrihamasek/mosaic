## ~~**T1 — Daily Tracking (core loop)**~~

**Cíl:** stabilní denní smyčka, typizace, listener architektura.

**Úkoly:**

- ✅ Typizace Stats/Today (TS migration, selectors)
    
- ✅ Mutation services (nový servisní layer pro zápisy)
    
- ✅ Listener middleware (nahradit cross-slice cascades)
    
- ✅ UX: refresh při kliknutí na tab, barevné označení hodnot v Entries, layout corrections
    
- ✅ Různé typy záznamů (pozitivní/negativní/neutral) – base model
    
- ✅ Mood tracking 
    
- ✅ Finalize Day (stabilizace)
    

---

## ~~**T2 — Activities Management**~~

**Cíl:** čistá práce s aktivitami, správné propagace, stabilní metadata.

**Úkoly:**

- ✅ activities_service (přesun SQL logiky z controller layer)
    
- ✅ Propagation refactor (auto-update entries při změnách aktivit)
    
- ✅ Batch actions (více položek najednou)
    
- ↻ Sloučení aktivit (backend + frontend) – odloženo
    
- ✅ Category metadata cleanup
    
- ✅ UX: hover zobrazení kategorií, odstranění názvů kategorií v selectech
    

---

## **T3 — Analytics**

**Cíl:** trendová analytika, mood scoring, denní agregace.

**Úkoly:**

- Trends page (frontend)
    
- stats_service (services/queries místo controller SQL)
    
- Sliding windows (7/30/90 dní)
    
- Mood UI + mood scoring integration
    
- Negative/neutral scoring logika
    
- Vylepšení category baselines
    
- `/wearable/trends` integrace do Stats
    
- Vize/cíle v UI
    

---

## **T4 — Admin Suite**

**Cíl:** operátorská sada nástrojů, observabilita, správa uživatelů.

**Úkoly:**

- Health panel upgrades (více metrik, latency detail)
    
- Logs pagination + filtry
    
- User search / rozšířený Admin panel
    
- Query services pro logy (service layer)
    
- Admin UX cleanup
    
- Audit logging rozšíření
    

---

## **T5 — Backups / Import–Export**

**Cíl:** robustní bezpečnost dat, správný scheduler, validace.

**Úkoly:**

- backup_service (oddělení controller/service)
    
- Serizalizers (lepší struktura JSON/CSV)
    
- Import wizard (frontend)
    
- Filename validation hardening
    
- Automated backup tests (CI)
    
- Integrity checks (hash, timestamp)
    
- UX run/interval polish
    

---

## **T6 — Wearables**

**Cíl:** kompletní wearable pipeline, aggregace, rychlé dotazy, mobile sync.

**Úkoly:**

- ETL performance improvements (canonical queries)
    
- HR / sleep integration (canonical tables)
    
- Wearable inspector stabilization
    
- Trend endpoints (hotovo, ale přidat test coverage)
    
- Mobile offline cache (IndexedDB)
    
- Mobile delta-sync (HC agent)
    
- ETL latency metrics
    
- Ingest dedupe metrics
    

---

## **T7 — NightMotion**

**Cíl:** stream wrapper, budoucí detekce, čistý service layer.

**Úkoly:**

- nightmotion_service (oddělení controller logic)
    
- ONVIF integrace
    
- Motion ingestion (události, timestamps)
    
- Detection markers (v UI)
    
- Motion → Analytics integrace
    
- Error handling upstream (retry / alerts)
    

---

## **T8 — UX / UI Quality**

**Cíl:** konzistentní design, přístupnost, form patterns.

**Úkoly:**

- TS migration (zbývající slice/jsx)
    
- Jednotný form pattern (react-hook-form)
    
- Layout consistency (form panels, grids)
    
- Přístupnost / mobilní breakpoints
    
- Hints, tooltips, popisy
    
- Best-practices příklady aktivit
    
- PWA UX enhancements
    

---

## **T9 — Architecture Stabilization**

**Cíl:** dlouhodobě udržitelné jádro, guardrails, testy, čisté vrstvy.

**Úkoly:**

- Controllers → service layer extraction (activities, entries, stats)
    
- Cache manager (centralizovaná invalidace)
    
- No cross-slice imports (ESLint/Flake8 rules)
    
- Guardrails CI (madge/pydeps, lint zónování)
    
- Mutation services (frontend)
    
- Listener architecture (frontend)
    
- Infrastructure services (rate limit, auth, metrics jako moduly)
    
- Namespace cache keys by user_id
    
- Test coverage backend services
    
- Test coverage admin tools
    
- Repository boundaries enforcement
