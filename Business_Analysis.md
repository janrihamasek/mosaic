## B1 – Narrative & Purpose

- **Narrativ (OS-for-life):** Mosaic je osobní operační systém nad každodenními daty. Sbírá aktivity, záznamy, wearables a administrativní telemetrii a spojuje je do jednoho obrazu dne. Denní smyčka (Today → Stats) dává okamžitou zpětnou vazbu a dlouhodobé trendy udržují směr.
- **Purpose (1 strana):**  
  - **Proč existuje:** odstranit chaos v datech o sobě, mít vlastní datové jádro a analytiku bez závislosti na centralizovaných službách.  
  - **Komu slouží:** tobě jako primárnímu uživateli + power-userům, kteří chtějí hlubokou analytiku a kontrolu nad daty.  
  - **Jak:** self-host/PWA, offline first, modulární architektura (ingest → normalizace → analytics → vizualizace).  
  - **Výsledek:** denní jasnost (co se stalo), kontrola (co zlepšit), bezpečí (zálohy, audit), rozšiřitelnost (wearables, NightMotion).
- **Oddělení identit:**  
  - **Osobní:** nástroj pro tvoji energii a zdraví, respektuje hyperfokus/útlum, chrání soukromí.  
  - **Produktová:** datová platforma pro power-user segment; může vyrůst na micro-B2B (rodina/tým), ale základ zůstává osobní OS.
- **Jednoduchý popis pro okolí:** „Mosaic je moje osobní datová mapa – zapisuje denní aktivity, tahá data z nositelností a ukazuje jasné trendy. Je to self-hostnutá PWA s analytikou a zálohami.“

---

## B2 – Personas & Segments

- **Ty (autor / architekt):** chceš úplnou kontrolu nad daty, rychlou denní smyčku, hlubokou analytiku, nízké provozní tření. Očekávání: offline, skriptovatelné exporty, admin nástroje, bezpečnost.
- **Power-user (technický nadšenec):** integruje více zdrojů (wearables, CSV), chce přesné metriky, nastavitelné kategorie/cíle, možnost vlastního hostingu. Očekávání: transparentní model dat, auditovatelné procesy, export/import bez vendor lock-in.
- **Health-tracker (zdraví / wellbeing):** sleduje spánek, HRV, náladu, rutiny. Chce jednoduchý vstup a jasné trendové grafy (7/30/90 dní), notifikace při odchylkách. Očekávání: spolehlivé sync s wearables, baseline metriky, jasné vizualizace.
- **Admin/Operator (malý tým/rodina):** stará se o dostupnost, zálohy, správu uživatelů. Očekávání: `/healthz`, `/metrics`, backup panel, jednoduché uživatelské role.
- **Podpora nyní vs. později:**  
  - **Teď:** Ty + Power-user + Health-tracker (osobní režim, closed testing).  
  - **Později:** Admin/Operator pro rodinu/malý tým, micro-B2B scénáře.  
  - **Scope hranice:** ne mířit na mainstream produktivitu ani na gamifikované habit appky; soustředit se na deep/niche uživatele se zájmem o data.

---

## B3 – Value Proposition

- **Hlavní VP:**  
  - **Unified data:** jedno datové jádro pro aktivity, zápisy, wearables, NightMotion.  
  - **Analytics depth:** trendové okna 7/30/90, kategorie baseline, streaky, korelace nálady.  
  - **Daily clarity:** Today/Stats smyčka s okamžitým refresh, offline zápisy, auto-save.
- **Sekundární VP:**  
  - **Wearables:** Health Connect / další ingest s normalizací a trendovými endpointy.  
  - **Admin/Observability:** `/healthz`, `/metrics`, backup manager, auditovatelné import/export.  
  - **Backups/Portability:** ZIP zálohy, CSV/JSON export, self-host bez vendor lock-in.
- **Messaging (1 věta → odstavec → krátký pitch):**  
  - **1 věta:** „Mosaic sjednocuje moje denní data a ukazuje mi, co se děje v těle i rutinách.“  
  - **Odstavec:** „Mosaic je osobní datová platforma. Sbírá aktivity, zápisy a údaje z wearables, normalizuje je a v PWA ukazuje denní i dlouhodobé trendy. Je offline friendly, self-host a má vestavěné zálohy a admin nástroje, takže mám jistotu a kontrolu nad daty.“  
  - **Pitch (krátký):** „Je to OS-for-life: jedno místo pro moje rutiny, náladu, spánek i výkon. Žádný vendor lock-in, jen jasná analytika a bezpečné zálohy.“
- **Srovnání s konkurencí:**  
  - **Habit apps (Habitica, běžné trackery):** Mosaic je méně gamifikovaný, více datově/analyticky orientovaný.  
  - **Notion:** Notion je generický workspace; Mosaic má doménový model aktivit/entries, automatickou analytiku a validace.  
  - **Google Fit / Oura:** tyto nástroje jsou uzavřené a single-source; Mosaic agreguje více zdrojů, je self-host a exportovatelný.  
  - **Výhoda:** hlubší datová práce, transparentní model, samostatnost (self-host), observability a zálohy jako součást produktu.

---

## B9 – Business Risks & Constraints

- **Reálné limity:**  
  - **Čas/kapacita:** nelineární výkon (hyperfokus vs. útlum); je nutné plánovat v blocích, krátké milníky (M1/M2), modulární scope.  
  - **Zdraví/energie:** riziko útlumu → potřeba nízkonákladového provozu a automatizace (backups, monitoring).  
  - **Finance:** omezený rozpočet → preferovat self-host, open-source stack, odložit marketing a velké integrace do chvíle, kdy přinesou hodnotu.
- **Scope guardrails (co nedělat):**  
  - Nespouštět masový marketing ani komunitní funkce; žádné komplexní týmové workflow.  
  - Nestavět gamifikaci ani všeobecnou produktivní „all-in-one“ appku.  
  - Neforkovat se do enterprise funkcí (SLA, SSO) před ověřením power-user segmentu.  
  - Nepodceňovat cache/tenant izolaci (riziko datového úniku při multi-tenant).
- **Rizika integrací:**  
  - **Wearables:** API změny, omezené quota, kvalita dat → potřebné testy, deduplikace, fallback na CSV import.  
  - **Analytics:** špatné baseline nebo chybná agregace může zkreslit vhledy → dokumentované metriky (`docs/METRICS.md`), test coverage, sanity check na datech.  
  - **NightMotion:** streaming/latence, bezpečnost přístupu → rate-limit, autentizace, izolace v Admin.  
  - **Cache/obs:** nenamespacované cache `/today`/`/stats` u multi-tenant → přidat `user_id` do klíčů nebo per-user store.
- **Mitigation plan (co dělat, když X selže):**  
  - **Výpadek kapacity (čas/zdraví):** spolehnout se na automatické zálohy, minimal ops (Docker Compose), malé backlog bloky.  
  - **Selhání integrace wearables:** fallback na CSV import a manuální zadávání, feature flag pro vypnutí sync, log/metrics pro rychlou diagnostiku.  
  - **Chyby analytiky:** verze metrik, rychlé revert script, testy na baseline datech, ruční sanity checky.  
  - **Bezpečnost/privátní data:** důsledná separace uživatelů, audit logy v admin, rate-limity, API key kontrola.  
  - **Finanční tlak:** držet náklady na VPS/hosting nízko, monetizační modul (Premium Analytics) až po ověření hodnoty, vyhnout se dluhům/investorům bez co-foundera.

