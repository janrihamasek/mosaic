
## 1. Cíl

Umožnit, aby každá aktivita měla typ:

- **positive** – žádoucí, přispívá k dennímu plnění (day completion), ovlivňuje streak, statistiky, kategorie.
    
- **negative** – nežádoucí, nepřispívá k day completion, nezvyšuje streak, může být zobrazována odděleně (např. analgetika, symptomy, zlozvyky).
    

Cílem je zavést tento typ bez narušení současného fungování a zároveň připravit půdu pro budoucí rozšíření (např. symptom tracking, negativní metriky).

---

## 2. Datový model (backend)

### 2.1 Úprava tabulky `activities`

Přidání pole:

- `activity_type` (string / enum): hodnoty **"positive"**, **"negative"**.
    
- Default: **"positive"** u všech stávajících aktivit.
    

### 2.2 Propagace do entries

- Do denormalizovaného snapshotu v `entries` se přidá kolonka `activity_type`.
    
- Backend bude toto pole automaticky zapisovat při vytváření nebo updatu entry.
    

### 2.3 CSV import/export

- Export: přidat `activity_type` jako volitelný sloupec.
    
- Import: pokud není uvedeno, používat default "positive".
    

---

## 3. Backend logika

### 3.1 Today (`GET /today`)

- Negative aktivity se zobrazí v Today normálně.
    
- Budou mít **goal = 0**, nebo budou při joinu zcela ignorovány pro výpočet splněnosti.
    
- Nezvyšují počet položek, které je potřeba splnit.
    

### 3.2 Přidávání záznamů (`POST /add_entry`)

- Neřeší se – negativní i pozitivní aktivity se zapisují stejně.
    
- Rozdíl nastane až při výpočtech.
    

### 3.3 Statistika (`GET /stats/progress`)

Změny ve výpočtech:

- **goal_completion_today**: počítá se pouze z pozitivních aktivit.
    
- **avg_goal_fulfillment** (7/30 dní): ignoruje negativní aktivity.
    
- **top_consistent_activities**: negativní aktivity se úplně vynechají.
    
- **positive_vs_negative**: možné budoucí rozšíření — negativní mohou být zobrazovány zvlášť.
    

### 3.4 Streak logika

- Negativní aktivity **nikdy** nezvyšují streak.
    
- Uživateli nehrozí, že by mu “negativní aktivita” rozbila streak.
    

### 3.5 Kategorie

- Kategorie zůstávají beze změny; typ aktivity (positive/negative) je samostatná vlastnost a nemá vliv na kategorizaci.
    

### 3.6 Cache

- Každá změna typu aktivity invaliduje Today a Stats cache (stejně jako změna category/goal).
    

---

## 4. Frontend – úpravy

### 4.1 ActivityForm

- Přidat výběr typu aktivity (positive / negative).
    
- Při editaci se načte aktuální typ.
    

### 4.2 Activities tabulka

- Může zobrazit ikonu či označení typu; pozitivní aktivity budou zeleně podbarvené, negativní červeně.
    
- Typ nemění chování tabulky.
    

### 4.3 Today

- Negative aktivity se zobrazí normálně; hodnotu goal Today nijak nezobrazuje a není pro toto zobrazení relevantní.
    
- Pozitivní aktivity se podbarví zeleně (stejně jako nyní při value > 0), negativní aktivity se podbarví červeně; současné řazení hodnot > 0 na konec tabulky zůstává zachováno.
    

### 4.4 Entries

- Typ u každého záznamu se zobrazí pomocí podbarvení: pozitivní zeleně, negativní červeně.
    

### 4.5 Stats

- Grafy a metriky se změní automaticky podle backend payloadu.
    

### 4.6 Redux

- `activitiesSlice`: CRUD operace musí posílat a přijímat `activity_type`.
    
- `entriesSlice`: žádná změna, vše řeší backend.
    

---

## 5. UX návrh

- Aktivita “Analgetikum” bude typu **negative**.
    
- Uživatel ji normálně uvidí v Today, může ji vyplnit.
    
- Day completion se nezmění.
    
- Statistiky zůstanou čisté a nezatížené tím, že si vzal lék.
    
- Do budoucna lze přidat:
    
    - graf frekvence negativních aktivit,
        
    - korelace s pozitivními,
        
    - zobrazení symptomů.
        

---

## 6. Strategické důsledky

### 6.1 Krátkodobě

- Jednoduchý doplněk, který nezkomplikuje ani architecture roadmap, ani Redux.
    
- Přidává užitečnou vrstvu interpretace (negative events), aniž by rozbil stávající statistiky.
    

### 6.2 Dlouhodobě

- Otevírá cestu k "symptom tracking" a "discomfort metrics".
    
- Lze kombinovat s wearables (např. korelace: bolest + špatný spánek).
    
- Lze z toho vyrobit premium dashboard.
    

---

## 7. Rizika a prevence

- **Riziko:** negativní aktivity se budou náhodně započítávat.
    
    - _Prevence:_ centralizovat logiku výpočtu do `stats_service`.
        
- **Riziko:** frontend bude dělat vlastní výpočty.
    
    - _Prevence:_ UI nepočítá nic – vše dělá backend.
        
- **Riziko:** CSV import/export se rozbije.
    
    - _Prevence:_ pole `activity_type` volitelné; u starých exportů default "positive".
        

---

## 8. Co všechno budeme řešit

- Migrace DB s default hodnotou.
    
- Úprava CRUD aktivit (backend + frontend).
    
- Úprava výpočtů statistik.
    
- Úprava Today payloadu.
    
- Volitelné UI úpravy (ikony, barvy).
    
- Dokumentace.
    
- Testy (minimálně sanity).