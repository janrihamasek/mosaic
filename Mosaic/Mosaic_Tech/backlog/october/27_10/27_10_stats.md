# Daily Log – 2024-10-27

- Date: 2024-10-27
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 27_10_stats.md

## Notes (raw import)

### 🔧 Úkol: Úprava systému Goal a komponenty ActivityDetail

#### 1. Změna systému Goal
Nahradit původní pole `Goal` dvěma selecty v komponentě **ActivityForm**:

**Nové selecty:**
1. `frequency_per_day`
   - typ: integer  
   - rozsah: 1–3  
   - default: 1
2. `frequency_per_week`
   - typ: integer  
   - rozsah: 1–7  
   - default: 1

**Výpočet:**
```js
avg_goal_per_day = (frequency_per_day * frequency_per_week) / 7
```

- Výpočet provede **frontend** (ActivityForm) před odesláním dat.
- Backend uloží pouze hodnotu `avg_goal_per_day` do sloupce `goal` (REAL).
- Ve sloupci **Goal** na kartě Activities se zobrazuje právě `avg_goal_per_day` (zaokrouhleno na jedno desetinné číslo).

**Odvozené metriky (budou použity později):**
```python
goal_per_month = avg_goal_per_day * days_in_month(month)
goal_last_30_days = avg_goal_per_day * 30
goal_last_90_days = avg_goal_per_day * 90
goal_last_three_months = avg_goal_per_day * days_in_last_three_months()
```

---

#### 2. Úprava komponenty ActivityDetail
Komponenta **ActivityDetail** bude umožňovat přímou editaci polí aktivity.

**Nové rozložení:**
- Název: `"Activity name - overview"`
- Pole:
  - `Category` (editovatelné)
  - `Goal` – jeden řádek vedle sebe:
    1. Select `frequency_per_day` (1–3)
    2. Select `frequency_per_week` (1–7)
    3. Vypočtená hodnota `avg_goal_per_day` (readonly)
  - `Description` (editovatelné)
- Pole `Activity name` zůstává **neměnné**.

**Chování:**
- Pokud dojde ke změně v libovolném poli (`Category`, `Goal`, `Description`):
  - tlačítko **Close** se změní na **Save**  
    (uloží všechny změny a zavře detail)
  - pod ním se zobrazí tlačítko **Not Save**  
    (zavře detail bez uložení)
- Po uložení se nové hodnoty promítnou do všech záznamů se stejným `activity_name`
  (`Category`, `Goal`, `Description` se tedy aktualizují napříč souvisejícími entries).

**Odstranit z komponenty:**
- `Total entries`
- `Average value`
- `Last entry`

---

#### 3. Databázové a API detaily
- Sloupec `goal` v tabulce `activities` ukládá hodnotu `avg_goal_per_day` (REAL).
- API `/activities` při POST přijímá `frequency_per_day` a `frequency_per_week`, 
  vypočítává `avg_goal_per_day` a ukládá jej.
- API `/activities/<id>` při PUT umožňuje aktualizaci `category`, `goal`, `description`
  a promítne tyto změny do všech záznamů se stejným názvem aktivity.

---

 **Shrnutí:**
- Dvě dimenze cíle (`per_day`, `per_week`) → spočítat `avg_goal_per_day`.
- Umožnit plnou editaci detailu aktivity přes `ActivityDetail`.
- Odebrat neaktuální statistiky (Total, Average, Last entry).
- Všechny změny se projeví u všech odpovídajících záznamů.

**Frontend**

- Replaced the single goal input with dual frequency selectors and an avg/day preview when creating activities, including range validation before submit (mosaic_prototype/frontend/src/components/ActivityForm.jsx:5).
- Rebuilt the detail drawer to support editing category, description, and goal frequencies with live avg computation, save/not-save handling, and integration with the new update API (mosaic_prototype/frontend/src/components/ActivityDetail.jsx:5).
- Surfaced the updated goal value consistently by wiring the detail refresh hook, exposing the update RPC, and formatting goals to two decimals in the table view (mosaic_prototype/frontend/src/App.jsx:133, mosaic_prototype/frontend/src/api.js:63, mosaic_prototype/frontend/src/components/ActivityTable.jsx:60).

**Backend**

- Migrated the activities schema to store avg goals as REAL plus persisted frequency columns, with runtime upgrade logic covering existing databases (mosaic_prototype/backend/app.py:44, mosaic_prototype/backend/import_data.py:11, mosaic_prototype/database/schema.sql:10).
- Added create/update validators for the new payload shape and a PUT endpoint that recalculates averages, updates frequencies, and syncs descriptions across entries sharing the activity (mosaic_prototype/backend/security.py:129, mosaic_prototype/backend/app.py:240).
- Updated CSV import and API tests to honor the new goal semantics and verify propagation behaviour (mosaic_prototype/backend/import_data.py:80, mosaic_prototype/backend/tests/test_api.py:12).