## 0. Role jednotlivých roadmap

- Priority se řídí pořadím milníků (M1 → M4).
- Splnění T/B úkolů se značí checkboxy u každého milníku.

- MAIN = „co se kdy stane“ (časové milníky).
    
- TECH = „jak to technicky doručíme“ (T1–T9).
    
- BUSINESS = „jak z toho je produkt a peníze“ (B1–B10).
    
- Každý milník Mx má:
    
    - TECH rozsah (odkazy na T…),
        
    - BUSINESS rozsah (odkazy na B…),
        
    - MAIN/PRÁVO/INFRA (odkazy na I–VI z původní main_roadmap).
        

---

## M1 – Interní alfa: core loop + základ architektury

**Cíl:**  
Mít Mosaic použitelný pro tebe a velmi úzký okruh (ty + max pár lidí), bez Google Play, s funkční denní smyčkou a základní stabilitou.

**Scope – TECH**

- [x] T1 — Daily Tracking (core loop)
    
- [x] T2 — Activities Management (v rozsahu potřebném pro denní používání; merge odloženo)
    
- [ ] T5 — Backups / Import–Export (alespoň základní ruční zálohy, CSV)
    
- [ ] T8 — UX / UI Quality (nejhorší špičaté hrany)
    
- [ ] T9 — Architecture Stabilization (jen to, co je nutné, aby se to „nerozpadalo pod rukama“)
    

**Scope – BUSINESS**

- [x] B1 – Narrative & Purpose (jasně pojmenovaný účel pro tebe + partnerku)
    
- [x] B2 – Personas & Segments (primárně „ty“ + 1–2 modelové uživatele)
    
- [x] B3 – Value Proposition (co konkrétně ti Mosaic přináší v denním použití)
    
- [x] B9 – Business Risks & Constraints (minimálně identifikace hlavních bloků: čas, peníze, zdraví)
    

**Scope – MAIN / PRÁVO / INFRA**

- [ ] I. Technická připravenost – v rozsahu „self-host alpha“, ne Play:
    
    - HTTPS-only, žádné hardcoded secrets, základní healthcheck `/healthz`.
        
- [ ] VI. Uživatelská data, hosting:
    
    - Lokální / self-host backend, zálohy DB, základní monitoring.
        

---

## M2 – Google Play „closed testing“ release

**Cíl:**  
Aplikace je technicky i právně způsobilá pro uzavřený test přes Google Play (internal / closed testing track) s cca 5–10 testery.

**Scope – TECH**

- [ ] T1–T2 – dotažení pro reálné uživatele (stabilita, UX drobnosti).
    
- [ ] T8 – UX / UI Quality (minimální standard, aby to nevypadalo jako čistý prototyp).
    
- [ ] T9 – Architecture Stabilization (guardrails, základ CI, aby další práce nebyla chaos).
    

**Scope – BUSINESS**

- [ ] B7 – Messaging & Communication:
    
    - jednoduchý text pro testery (co to je, k čemu to je, jak to používat).
        
- [ ] B8 – Distribution / Delivery:
    
    - základní plán „jak dostanu appku k testerům“ (bez marketingu, jen closed group).
        

**Scope – MAIN / PRÁVO / INFRA**

- [ ] I. Technická připravenost (Google Play + App Architecture):
    
    - Android App Bundle (.aab), Target API level 34, Privacy Manifest, HTTPS-only, žádné hardcoded keys.
        
- [ ] II. Právní požadavky (GDPR + Google Play Policy):
    
    - Privacy Policy v minimální verzi, Terms of Use pro testery, základní soulad s Play zásadami.
        
- [ ] VI. Uživatelská data, hosting a správa prostředí:
    
    - vybraný hosting (VPS / cloud), nastavené logování, monitoring, manuální proces záloh a obnovy.
        

---

## M3 – Veřejné uvedení + Free / Plus model

**Cíl:**  
Aplikace je veřejně dostupná v Google Play, má jasný Free/Plus model (i kdyby Plus zatím nebyl plně implementovaný), první malá skupina běžných uživatelů a připravenost na první platby.

**Scope – TECH**

- [ ] T3 — Analytics (základní metriky používání + osobní statistiky).
    
- [ ] T4 — Admin Suite (minimální nástroje pro dohled a správu uživatelů/incidentů).
    
- [ ] T5 — Backups / Import–Export (rozumná automatizace, ne jen ručně).
    
- [ ] T8 — UX / UI Quality (první „veřejně přijatelná“ verze).
    
- [ ] T9 — Architecture Stabilization (guardrails, test coverage základních služeb).
    

**Scope – BUSINESS**

- [ ] B3 – Value Proposition (pro veřejného uživatele, ne jen pro tebe).
    
- [ ] B4 – Monetization Models (Free/Plus schéma, jednoduchý pricing).
    
- [ ] B5 – Market Fit / Needs (první feedback od uživatelů, zjišťování, jestli to někomu řeší reálný problém).
    
- [ ] B6 – Product Positioning (OS-for-life / personal analytics, jasně popsané).
    
- [ ] B7 – Messaging & Communication (veřejný popis v Play, jednoduchý web / landing).
    
- [ ] B8 – Distribution / Delivery (základní kanály: osobní síť, blog, sociální sítě).
    
- [ ] B9 – Business Risks & Constraints (aktualizace podle reality).
    

**Scope – MAIN / PRÁVO / INFRA**

- [ ] I. Technická připravenost:
    
    - Subscription Billing (Google Play Billing Library), ladění výkonu a stability.
        
- [ ] II. Právní požadavky:
    
    - Privacy Policy + Terms of Use už ne jen „pro testery“, ale pro veřejnost.
        
- [ ] III. Produktová péče:
    
    - definovaný základní cyklus verzí (např. minor release 1× měsíčně), bugfix proces, support kanál.
        
- [ ] IV. Právní forma:
    
    - rozhodnutí, v jaké právní formě můžeš přijímat platby (OSVČ / s.r.o. apod.) a co to pro tebe znamená.
        
- [ ] V. Licence, autorská práva, ochrana značky:
    
    - minimálně jméno/logo, licence k použitému obsahu, základní ochrana značky, pokud dává smysl.
        

---

## M4 – Wearables & Analytics scale-up

**Cíl:**  
Mosaic přestává být jen „deník + ruční tracking“ a stává se datovou platformou s integrací wearables a smysluplnou analytikou nad tělem a každodenním životem.

**Scope – TECH**

- [ ] T3 — Analytics (rozšíření: korelace, dlouhodobé přehledy).
    
- [ ] T6 — Wearables (Health Connect / další integrace, import dat, ETL pipeline).
    
- [ ] T7 — NightMotion (spánková/ noční data jako součást celkového obrazu).
    
- [ ] T5 — Backups / Import–Export (větší datové objemy, robustnější řešení).
    

**Scope – BUSINESS**

- [ ] B5 – Market Fit / Needs (ověření, kdo skutečně využívá wearables+analytics kombinaci a proč).
    
- [ ] B6 – Product Positioning (Mosaic jako „OS-for-life“ s daty z těla, nejen jako deník).
    
- [ ] B10 – Strategic Themes / Long-Term Goals (jasné priority: analytics + wearables jako hlavní investiční osa).
    

**Scope – MAIN / PRÁVO / INFRA**

- [ ] III. Produktová péče:
    
    - roadmapa pro další datové zdroje a funkce, řízení dluhu (UX, performance).
        
- [ ] VI. Uživatelská data, hosting:
    
    - řešení objemu dat, retence, anonymizace, Data Retention Policy v praxi.
        
- [ ] V. Licence, autorská práva:
    
    - případné smluvní/licenční otázky kolem integrace třetích stran (pokud vzniknou).
        

---

## 5. Index: vazby MAIN ↔ TECH ↔ BUSINESS ↔ MAIN(I–VI)

Pro rychlou orientaci:

- M1 – Interní alfa
    
    - TECH: T1, T2, T5, T8, T9
        
    - BUSINESS: B1, B2, B3, B9
        
    - MAIN(I–VI): I (částečně), VI
        
- M2 – Google Play closed testing
    
    - TECH: T1, T2, T8, T9
        
    - BUSINESS: B7, B8
        
    - MAIN(I–VI): I, II, VI
        
- M3 – Veřejné uvedení + Free/Plus
    
    - TECH: T3, T4, T5, T8, T9
        
    - BUSINESS: B3, B4, B5, B6, B7, B8, B9
        
    - MAIN(I–VI): I, II, III, IV, V, VI
        
- M4 – Wearables & Analytics scale-up
    
    - TECH: T3, T5, T6, T7
        
    - BUSINESS: B5, B6, B10
        
    - MAIN(I–VI): III, V, VI
        
