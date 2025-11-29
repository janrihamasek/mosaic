# Mosaic – jednotná architektura pro osobní data

Cíl: Jeden zdroj pravdy (backend), více klientů (web/PWA, Android), jasný tok dat ze sběru → úložiště → zobrazení. Všude stejné výsledky, lokální schopnosti jen rozšiřují sběr.

## 1) Komponenty a role

- **Android klient (Capacitor/React)**
    
    - HC Reader: čte Health Connect (Steps, HeartRate, SleepSession/Stage, ExerciseSession).
        
    - Sync Agent: normalizuje → šifruje v přenosu → posílá na backend; plánuje delta-sync.
        
    - Offline cache: IndexedDB (nezávisle na webu), fronta neodeslaných dávek.
        
- **Web/PWA klient (React)**
    
    - Čtení a vizualizace dat z backendu; žádný přímý přístup k HC.
        
- **Backend (Flask + PostgreSQL)**
    
    - Ingest API (idempotentní POST dávky).
        
    - Normalizační/ETL vrstva (raw → canonical → agregace).
        
    - Query API pro UI (denní/intervalové dotazy, metriky).
        
    - Auth (JWT), audit, rate-limit, zálohy, exporty.
        

## 2) Datový model (minimální kanonická vrstva)

- `wearable_sources`(id, user_id, source_app, device_id, device_model, tz, created_at)
    
- `wearable_raw`(id, user_id, source_id, record_type, payload_json, start_ts_utc, end_ts_utc, dedupe_key, received_at)
    
- `wearable_canonical_*` (po jedné tabulce na typ; všechny v UTC + origin tz):
    
    - `wc_steps`(user_id, start_ts_utc, end_ts_utc, steps, source_id)
        
    - `wc_hr`(user_id, ts_utc, bpm, source_id)
        
    - `wc_sleep_session`(user_id, start_ts_utc, end_ts_utc, efficiency?, source_id)
        
    - `wc_sleep_stage`(user_id, start_ts_utc, end_ts_utc, stage, source_id)
        
    - `wc_exercise`(user_id, start_ts_utc, end_ts_utc, kind, kcal?, hr_avg?, source_id)
        
- `wearable_daily_agg`(user_id, date_local, steps, hr_rest?, sleep_total_min, sleep_eff?, sessions, updated_at)
    

Pozn.: `dedupe_key` = stabilní hash (user_id + source + record_type + čas + hodnoty) pro idempotenci.

## 3) Synchronizační protokol

- **Identita:** JWT (už existuje) + volitelně `X-Device-Id` pro odlišení klientů.
    
- **Endpointy (backend):**
    
    - `POST /ingest/wearable/batch`  
        Body: `{ source_app, device_id, tz, records: [ {type, start, end?, fields, dedupe_key} ] }`  
        Odpověď: `{ accepted, duplicates, errors[] }`.
        
    - `GET /wearable/summary?from=&to=` (agregace pro UI).
        
    - `GET /wearable/raw?type=&from=&to=&limit=` (diagnostika).
        
- **Klient (Android) – dávkování:**
    
    - První sync: interval N dní zpět (např. 30), po typech.
        
    - Delta: „since last_ts“ per typ.
        
    - Backoff a retry s uloženou frontou (IndexedDB).
        

## 4) Normalizace a pravidla

- **Čas:** uložit v UTC + `origin_tz`; pro denní výpočty používat uživatelův `tz`.
    
- **Idempotence:** před insertem ověřit `dedupe_key`; konflikty řešit „last-write-wins“ s `source_priority` (např. lékařské > hodinky > telefon).
    
- **Sloučení zdrojů:** u steps a hr preferovat záznamy s vyšší granularitou a validním zdrojem; duplicity agregovat.
    
- **Validace:** rozsahy (bpm 30–240), překryvy spánku, nesmyslné délky cvičení.
    

## 5) API pro UI (dotazy)

- **Přehled dne:** `/wearable/day?date=YYYY-MM-DD`
    
    - `{ steps, sleep:{total, sessions[], stages[]}, hr:{rest, min,max,avg}, exercise[] }`
        
- **Trendy:** `/wearable/trends?metric=steps|sleep|hr&window=7|30`
    
- **Detailní proud:** `/wearable/series?type=hr|steps&from=&to=&bucket=1m|5m|1h`
    

## 6) Bezpečnost, audit, soukromí

- Transport: HTTPS/TLS; možnost klientské `X-API-Key` pro ingest (navíc k JWT).
    
- Uložení: šifrované zálohy; PII minimálně (žádná jména zařízení od výrobce, jen `device_model`).
    
- Audit: `activity_log` události: ingest_start, ingest_ok, ingest_dup, ingest_error.
    
- Smazání: kaskádově dle `user_id`.
    

## 7) Offline a konzistence

- Android klient ukládá neodeslané dávky (fronta), odešle při připojení.
    
- Backend po ingestu aktualizuje `wearable_daily_agg`; UI vždy čte agregát (rychlé).
    
- Rebuild agregátů nočním jobem (idempotentní), nebo on-write trigger.
    

## 8) Monitoring a kvalita

- Metriky: přijaté záznamy/min, duplicitní podíl, průměrná latence, chybovost per typ.
    
- Logy: strukturované; korelace přes `request_id` a `source_id`.
    
- Testy: unit (normalizace), integration (ingest → canonical → agg), e2e (Android stub → backend).
    

## 9) Minimální MVP scope

1. Android klient: čtení HC (Steps, HR, SleepSession/Stage); delta-sync; fronta.
    
2. Backend: `POST /ingest/wearable/batch`, `wc_*` tabulky, denní agregace, `/wearable/day`.
    
3. Web UI: nová karta „Wearables“ (součást Admin/Stats), denní přehled + posledních 7 dní.
    

## 10) Formát záznamu (kanonický JSON příklad)

Steps (agregovaný interval):

```
{ "type":"steps", "start":"2025-11-10T06:00:00Z", "end":"2025-11-10T06:15:00Z",
  "fields": { "count": 423, "source":"HealthConnect:VeryFit" },
  "dedupe_key":"sha256(user|type|start|end|count|source)" }
```

Heart rate (bodový):

```
{ "type":"hr", "start":"2025-11-10T06:07:12Z",
  "fields": { "bpm": 68, "source":"HealthConnect:VeryFit" },
  "dedupe_key":"sha256(user|type|ts|bpm|source)" }
```

Sleep stage:

```
{ "type":"sleep_stage", "start":"2025-11-09T22:41:00Z", "end":"2025-11-09T23:15:00Z",
  "fields": { "stage":"light", "session_id":"hc-abc123" },
  "dedupe_key":"sha256(user|type|start|end|stage|session_id)" }
```

## 11) Rozhraní v UI (stručný návrh)

- **Admin → HealthConnect Inspector**: povolení přístupu, počty záznamů, rozsahy, ukázky.
    
- **Stats → Wearables (nová sekce)**: denní widgety (kroky, spánek, HR), 7/30-denní pruhy, odkaz na detail.
    
- **Entries → External**: auditní výpis posledních ingestů (čas, typy, objem, duplicitní %).
    

## 12) Migrační kroky

- Alembic: vytvořit `wearable_*` tabulky + indexy (time, user_id, type).
    
- Backend: moduly `ingest.py`, `wearable_service.py`, `agg_jobs.py`, testy.
    
- Frontend: Inspector panel (admin), Wearables view (stats).
    
- Android: Capacitor plugin `healthconnect-bridge` (read, page, delta).
    

Toto schéma je dostatečně stabilní pro postupnou implementaci a rozšiřitelné o další typy (VO₂max, HRV, krevní saturace) bez změny rozhraní.