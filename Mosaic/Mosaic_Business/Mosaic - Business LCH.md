### **1. Klíčové businessové procesy**

Z kódu je patrné, že projekt **Mosaic** podporuje následující procesy:

#### **a) Evidence aktivit a záznamů**

- Uživatelé mohou **přidávat, upravovat a mazat záznamy** (`/add_entry`, `/entries`, `/delete_entry`).
- Každý záznam obsahuje:
    - **Datum** (`date`)
    - **Aktivitu** (`activity`)
    - **Hodnotu** (`value`)
    - **Poznámku** (`note`)
    - **Popis** (`description`)
    - **Kategorii** (`category`)
    - **Cíl** (`goal`)

**Businessový význam:**

- Sledování denních aktivit (např. sport, práce, koníčky).
- Možnost nastavit si cíle pro jednotlivé aktivity.

#### **b) Správa aktivit**

- Uživatelé mohou **přidávat a spravovat aktivity** (`/add_activity`, `/activities`).
- Aktivity mají:
    - **Název** (`name`)
    - **Kategorii** (`category`)
    - **Cíl** (`goal`)
    - **Popis** (`description`)
    - **Frekvenci** (`frequency_per_day`, `frequency_per_week`)
    - **Stav** (`active`)

**Businessový význam:**

- Uživatelé si mohou definovat opakující se aktivity (např. "Běh", "Čtení").
- Možnost sledovat, jak často aktivitu vykonávají.

#### **c) Export a zálohování dat**

- Uživatelé mohou **exportovat data** (`/export/json`, `/export/csv`).
- **Automatické zálohování** (`/backup/run`, `/backup/status`).

**Businessový význam:**

- Uživatelé mohou analyzovat svá data mimo aplikaci (např. v Excelu).
- Zálohování zajišťuje bezpečnost dat.

#### **d) Autentizace a bezpečnost**

- Uživatelé se **registrují** (`/register`) a **přihlašují** (`/login`).
- Data jsou chráněna JWT a CSRF.

**Businessový význam:**

- Každý uživatel má své vlastní, soukromé údaje.

---

### **2. Co chybí nebo není jasné?**

#### **a) Uživatelský workflow**

- **Jak uživatelé interagují s aplikací?**
    - Jak vypadá typický den s Mosaic? (Např.: "Ráno si uživatel zkontroluje dnešní aktivity, večer zapíše, co udělal.")
    - Jaké jsou **hlavní obrazovky** ve frontendu? (Dashboard, přehled aktivit, statistiky?)
    - Jaké jsou **klíčové metriky**, které uživatelé sledují? (Např.: "Denní splnění cílů", "Týdenní trendy".)

#### **b) Businessové cíle**

- **Jaké problémy Mosaic řeší?**
    - Je to nástroj pro **osobní produktivitu**? (Např. jako "Notion pro aktivity".)
    - Je to nástroj pro **zdravý životní styl**? (Např. jako "Strava pro obecné aktivity".)
    - Je to nástroj pro **týmovou spolupráci**? (Např. jako "Trello pro aktivity".)

#### **c) Uživatelské role**

- **Kdo jsou typičtí uživatelé?**
    - Jednotlivci, kteří chtějí sledovat své aktivity?
    - Týmy, které potřebují koordinovat úkoly?
    - Firmy, které chtějí monitorovat aktivitu zaměstnanců?

#### **d) Klíčové funkce pro uživatele**

- **Notifikace a připomínky:**
    - Chybí automatické upozornění, pokud uživatel nesplní cíl.
- **Sdílení dat:**
    - Mohou uživatelé sdílet své aktivity s ostatními? (Např. pro týmovou spolupráci.)

#### **e) Integrace s jinými nástroji**

- **Lze Mosaic propojit s kalendářem (Google Calendar)?**
- **Lze importovat data z jiných aplikací?** (Např. z fitness náramků.)

---

### **3. Doporučení pro zpřesnění businessové stránky**

1. **Definujte cílovou skupinu:**
    
    - Pro koho je Mosaic určen? (Jednotlivci, týmy, firmy?)
    - Jaké jsou jejich **hlavní bolesti**, které Mosaic řeší?
2. **Vytvořte uživatelské příběhy (User Stories):**
    
    - Příklady:
        - "Jako uživatel chci vidět denní přehled svých aktivit, abych věděl, co jsem udělal."
        - "Jako uživatel chci dostávat upozornění, pokud nesplním svůj cíl."
3. **Doplněte chybějící funkce:**
    
    - **Statistiky a grafy** (např. měsíční přehledy).
    - **Notifikace** (např. "Nesplnil jsi svůj cíl pro běhání!").
    - **Sdílení dat** (např. pro týmy).
4. **Zlepšete dokumentaci:**
    
    - Popište, jaké **businessové procesy** Mosaic podporuje.
    - Vytvořte **příručku pro uživatele**, jak aplikaci používat.