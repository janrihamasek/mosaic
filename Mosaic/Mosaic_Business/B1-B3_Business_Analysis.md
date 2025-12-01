# Mosaic Business Analysis: B1-B3 Detailed Specifications

*Vypracováno: 1. prosince 2025*  
*Na základě: business_roadmap.md, technické dokumentace, a existující implementace*

---

## **B1 – Narrative & Purpose**

### **Mosaic Narrative: "Personal Data Operating System"**

**Jádro příběhu:** Mosaic je osobní platforma pro sběr, normalizaci a analytické zpracování životních dat. Není to habit tracker ani fitness aplikace – je to **operační systém pro osobní data** s fokusem na hloubkové analytiky a vlastnictví informací.

**Daily Loop Philosophy:**
- Ráno: rychlý přehled včerejšího dne a cílů na dnes
- Večer: 2-minutová ritualizovaná reflexe – ohodnocení aktivit (0-5 škála)
- Týdně/měsíčně: trendy, vzorce, korelace mezi aktivitami a kategoriemi

**Data Clarity Principle:** 
Uživatel vlastní svá data lokálně (self-hosting), má plnou kontrolu nad exporty/zálohováním, a rozumí přesně tomu, jak se počítají metriky (transparentní formule v dokumentaci).

### **Purpose Statement (1 strana)**

**Mosaic existuje proto, aby poskytoval tech-oriented jednotlivcům unifikované rozhraní pro jejich osobní data s analytickou hloubkou, kterou mainstream aplikace neposkytují.**

**Problém:** Dnešní self-tracking aplikace jsou buď příliš jednoduché (habit trackery), nebo příliš uzavřené (Oura, Fitbit cloud). Chybí platforma, která:
- Spojuje manuální vstupy (aktivity, reflexe) s automatickými daty (wearables, Health Connect)
- Nabízí vlastní analytické formule místo "černých skříněk"
- Umožňuje plnou kontrolu nad daty (self-hosting, exporty)
- Poskytuje hloubkovou analýzu místo povrchních notifikací

**Řešení:** Mosaic jako modulární systém s jasným dělením:
1. **Core:** Daily loop + aktivní analytiky (completion ratios, streaks, trends)
2. **Extensions:** Wearable integrace, AI insights, admin tooling
3. **Infrastructure:** PWA offline capability, PostgreSQL, Docker deployment

**Hodnota:** Uživatel získá "Google Analytics pro svůj život" – detailní porozumění vlastním vzorcům, prediktivní schopnosti, a kontrolu nad svými daty bez závislosti na korporátních cloudech.

### **Oddělení osobní vs. produktová identita**

**Osobní (Jan's) projekt:**
- Architektonické experimenty a dlouhodobý systém pro sebepoznání
- Technický showcase různých disciplín (fullstack, mobile, analytics, devops)
- Nástroj pro řízení vlastní produktivity a zdravotních dat

**Produktová identita:**
- B2C SaaS pro power-user segment (data analysts, quantified-self komunita, tech individuals)
- Potenciální B2B licence pro wellness firmy nebo research instituce
- Technická platforma s jasným API pro další rozšíření

### **Zjednodušené popisy pro různé publikum**

**Pro partnerku:** "Aplikace, kde si každý večer rychle ohodnotím, jak jsem se cítil s různými aktivitami (sport, čtení, meditace), a ona mi ukazuje trendy a vzorce v čase."

**Pro investora:** "Personal data platform pro tech-savvy uživatele. Kombinujeme manual tracking s wearable daty a poskytujeme analytics, které konkurence nemá. Self-hosting model snižuje provozní náklady a diferencuje od mainstream habit apps."

**Pro tech komunitu:** "Open-source personal analytics stack. React/Flask/PostgreSQL s PWA capabilities, Health Connect integration, a transparentními metrikami. Alternativa k proprietárním řešením typu Oura nebo Fitbit."

**Jedna věta pro všechny:** "Mosaic je operační systém pro osobní data – sbírá, normalizuje a analyzuje vaše aktivity s transparencí a kontrolou, kterou mainstream aplikace neposkytují."

---

## **B2 – Personas & Segments**

### **Primární Persona: "The Architect" (Jan's profile)**

**Demografika:** Technicky orientovaný jednotlivec, 25-40 let, programátor/analyst/researcher
**Motivace:** 
- Potřeba kontroly nad osobními daty a systémy
- Hloubková analýza vlastních vzorců chování
- Architektonické řešení dlouhodobého self-trackingu

**Očekávání:**
- Plná transparence metrik (open formule)
- Self-hosting schopnosti
- Modulární rozšiřitelnost (wearables, API, custom analytics)
- Offline fungování bez cloudové závislosti

**Pain Points:** Mainstream aplikace jsou "černé skříňky", cloudová závislost, omezené analytické možnosti
**Současná podpora:** ✅ Plně podporována (core daily loop + admin tooling)

### **Sekundární Persona: "The Quantified-Self Enthusiast"**

**Demografika:** Data analyst, researcher, nebo health-conscious professional, 30-50 let
**Motivace:**
- Detailní tracking multiple health/productivity metrik
- Korelační analýzy mezi různými životními oblastmi
- Evidence-based rozhodování o lifestyle změnách

**Očekávání:**
- Wearable integrace (Health Connect, Oura, Apple Health)
- Pokročilé trendy a predikce
- Export dat pro vlastní analýzy (CSV, JSON, API)
- Kategorizace a segmentace aktivit

**Pain Points:** Fragmentace mezi aplikacemi, omezené export možnosti, povrchní insights
**Současná podpora:** 🔄 Částečná (core funguje, wearable integrace v development)

### **Terciární Persona: "The Wellness Professional"**

**Demografika:** Wellness kouč, nutritionist, behavior therapist, 30-45 let
**Motivace:**
- Nástroj pro tracking klientských dat s klienty
- Evidence-based coaching a reporting
- Privacy-first řešení pro citlivá data

**Očekávání:**
- Multi-user management
- Reporting a dashboard pro klienty
- GDPR compliance a data security
- Integration s external tools

**Pain Points:** Expensive enterprise řešení, vendor lock-in, komplexní setup
**Současná podpora:** ❌ Nepodporována (budoucí B2B direction)

### **Quaternární Persona: "The Tech Administrator"**

**Demografika:** DevOps engineer, system administrator, 25-40 let
**Motivace:**
- Self-hostované řešení pro rodinu/malý team
- Technické experimenty s personal data
- Kontrola nad infrastrukturou a bezpečností

**Očekávání:**
- Docker deployment
- Monitoring a health checks
- Backup a recovery procedures
- Clear documentation a API

**Pain Points:** Složité setup, chybějící dokumentace, vendor lock-in
**Současná podpora:** ✅ Částečná (Docker stack ready, admin tooling existuje)

### **Segment Prioritization & Support Timeline**

**Fáze 1 - NYNÍ (Q4 2024 - Q2 2025):**
- **Primary support:** The Architect (100% focus)
- **Secondary support:** Tech Administrator (pomocí existing Docker/admin infrastructure)

**Fáze 2 - MEDIUM (Q3-Q4 2025):**
- **Full support:** Quantified-Self Enthusiast (wearable integrace, advanced analytics)
- **Enhanced support:** Tech Administrator (better documentation, monitoring)

**Fáze 3 - FUTURE (2026+):**
- **Evaluation:** Wellness Professional (B2B pivot možnost)
- **Community:** Open-source community contributors

### **Niche vs. Mainstream Decision**

**Záměrně DEEP/NICHE přístup:**
- Cílíme na 1000-10000 power-users místo miliony casual users
- Vyšší willingness to pay ($10-50/month) pro specialized funkce
- Lower support overhead (tech-savvy audience)
- Diferencovaný produkt vs. mainstream habit apps

**Odmítáme mainstream:**
- Žádné gamifikace nebo "streak addiction" featury
- Žádné social sharing nebo competitive elements  
- Žádná simplifikace na úkor analytické hloubky
- Žádná mobilní-first strategie (PWA + desktop equal priority)

---

## **B3 – Value Proposition**

### **Primary Value Propositions**

#### **1. Unified Personal Data Platform**
**Hodnota:** Jeden zdroj pravdy pro všechna osobní data – manuální vstupy (daily reflection) + automatická data (wearables, Health Connect) + derived analytics
**Konkrétně:** Místo 5+ různých aplikací (habit tracker, fitness app, sleep tracker, nutrition log) máte jeden systém s normalizovanými daty a cross-kategorial analytics

#### **2. Analytics Depth & Transparency**
**Hodnota:** Pokročilé metriky s transparentními formulemi - completion ratios, streak algorithms, rolling averages, trend predictions, korelační analýzy
**Konkrétně:** Rozumíte přesně, jak se počítá každý metric (dokumentované formule), můžete validovat výpočty, a getting insights které mainstream aplikace neposkytují

#### **3. Daily Clarity Ritual**
**Hodnota:** Strukturovaný 2-minutový večerní ritual reflexe + ranní dashboard s jasným přehledem pokroku a cílů
**Konkrétně:** Místo chaotického multitaskingu získáváte intentional daily loop s měřitelným pokrokem a jasnou zpětnou vazbou

### **Secondary Value Propositions**

#### **4. Data Ownership & Privacy**
- **Self-hosting capability:** Vaše data zůstávají pod vaší kontrolou
- **Export/backup flexibility:** JSON, CSV, automated backups
- **No vendor lock-in:** Open-source komponenty, standard formáty

#### **5. Wearable Integration Intelligence**
- **Health Connect normalization:** Automatic ingest z Android zdravotních dat
- **Cross-device synchronization:** PWA + mobile app coordination
- **Contextual analytics:** Spojení manual entries s wearable daty pro hlubší insights

#### **6. Admin & Observability Tooling**
- **System health monitoring:** Metrics, health checks, structured logging
- **Backup management:** Automated + manual backup with restore capabilities
- **Performance analytics:** Usage patterns, system load, data quality metrics

### **Simplified Benefit Messaging**

#### **Jedna věta:**
"Mosaic je Google Analytics pro váš osobní život – sbírá, analyzuje a poskytuje insights o vašich aktivitách s transparencí a kontrolou, kterou mainstream aplikace nemají."

#### **Jeden odstavec:**
"Mosaic spojuje váš večerní reflection ritual (2-minutové hodnocení aktivit) s automatickými daty z wearables a vytváří z toho pokročilé analytics s transparentními formulemi. Místo fragmentovaných habit trackerů získáváte unified platform s deep insights, data ownership, a daily loop který vás skutečně posune dopředu."

#### **Krátký pitch (30 sekund):**
"Používáte několik aplikací na tracking zdraví a produktivity? Mosaic je nahradí jedním systémem. Každý večer minutu ohodnotíte své aktivity, systém to spojí s daty z vašich wearables, a ráno vidíte detailní analytics - trendy, korelace, predikce. Na rozdíl od běžných aplikací rozumíte každému výpočtu, vlastníte svá data, a můžete si systém hostovat sami. Je to Google Analytics pro osobní život."

### **Competitive Differentiation Matrix**

| **Aspekt** | **Mosaic** | **Habit Apps (Habitify, Streaks)** | **Notion/Obsidian** | **Google Fit/Apple Health** | **Oura/Fitbit Premium** |
|------------|------------|-------------------------------------|----------------------|------------------------------|--------------------------|
| **Data Ownership** | ✅ Self-hosting + exports | ❌ Cloud lock-in | ⚠️ Notion cloud dependency | ❌ Google/Apple servers | ❌ Company servers |
| **Analytics Depth** | ✅ Transparent formules + advanced metrics | ⚠️ Basic streaks/completion | ❌ Manual only | ⚠️ Basic aggregations | ⚠️ Black-box algorithms |
| **Manual + Auto Data** | ✅ Unified pipeline | ❌ Manual only | ❌ Manual only | ⚠️ Auto only | ⚠️ Auto only |
| **Customization** | ✅ Full code control + API | ❌ Limited themes/categories | ✅ Full customization | ❌ Fixed interface | ❌ Fixed metrics |
| **Privacy Control** | ✅ Local deployment option | ❌ Cloud-based | ⚠️ Enterprise controls | ❌ Corporate surveillance | ❌ Corporate surveillance |
| **Learning Curve** | 🔴 High (tech users) | ✅ Low | 🔴 High | ✅ Low | ✅ Low |
| **Cost Structure** | ✅ One-time/self-host | ⚠️ Monthly subs | ⚠️ Monthly subs | ✅ Free/ecosystem | 🔴 High monthly |

### **Key Differentiators**

**vs. Habit Apps:** Hloubka analytics + automatic data integration
**vs. Notion:** Specialized pro personal tracking + automatic insights  
**vs. Google Fit:** Data ownership + manual reflection + advanced analytics
**vs. Oura:** Transparency + unified manual+auto data + customization
**vs. Excel/Sheets:** Automated pipeline + mobile app + designed UX

### **Value Proposition Validation Metrics**

**Primary metrics za Q1 2025:**
- Time-to-first-insight: <5 minut od registrace k užitečnému dashboardu
- Daily engagement: 80%+ users loggují data daily po 1 měsíci používání
- Analytics usage: 60%+ users prohlížejí Stats tab týdně

**Secondary metrics za H1 2025:**  
- Self-hosting adoption: 20%+ paying users používá vlastní deployment
- Wearable integration: 40%+ users má připojená wearable data
- Export usage: 30%+ users exportoval data alespoň jednou

---

---

## **B9 – Business Risks & Constraints**

### **Reálné osobní limity**

#### **Časové limity**
- **Dostupná kapacita:** 15-25 hodin/týden pro Mosaic development (včetně víkendů)
- **Nelineární výkon:** Periodicité hyperfokus (3-6h intensive blocks) vs. útlumové periody
- **Competing priorities:** Obživa, zdraví, vztahy mají vyšší prioritu než projekt
- **Seasonální variace:** Zimní měsíce = vyšší produktivita, léto = nižší kapacita

#### **Zdravotní limity** 
- **Energetické cykly:** Nelze udržet konzistentní 40h/týden bez burnout rizika
- **Stress sensitivity:** Vysoký tlak = okamžitý pokles výkonu a zdravotních problémů
- **Physical constraints:** Potřeba optimálního prostředí (teplo, klid, komfort)
- **Mental bandwidth:** Max 1 major feature současně, fragmentace = produktivitní kolaps

#### **Finanční limity**
- **Bootstrap budget:** Max $500-1000/měsíc pro infrastrukturu a tooling
- **No external pressure:** Žádné investor expectations nebo client deadlines
- **Revenue timeline:** Minimálně 12-18 měsíců do první významné monetizace
- **Risk tolerance:** Nízká - projekt nesmí ohrozit základní obživu

### **Scope Guardrails: Co NEDĚLAT**

#### **Technická omezení**
- ❌ **Mikroservisová architektura:** Complexity overhead vs. single-developer capacity
- ❌ **Cutting-edge technologie:** Stabilní, mature stack preferuje experimental features
- ❌ **Multiple deployment targets:** Focus na Docker Compose, ne Kubernetes/cloud-native
- ❌ **Real-time features:** WebSockets, push notifications = unnecessary complexity
- ❌ **Mobile-native apps:** PWA + Capacitor sufficient, ne native iOS/Android

#### **Business scope omezení**
- ❌ **B2B enterprise sales:** Vyžaduje sales team a enterprise support capabilities
- ❌ **Multi-tenant SaaS:** Complexity growth vs. self-hosting model benefits
- ❌ **Social/competitive features:** Community management overhead + off-brand
- ❌ **Marketplace/plugin ecosystem:** API management + quality control overhead
- ❌ **Compliance certifications:** HIPAA, SOC2 = legal a process overhead

#### **Marketing/Sales omezení**
- ❌ **Mainstream marketing:** Mass advertising, influencer partnerships, PR campaigns
- ❌ **Freemium with support:** Customer support load incompatible s single developer
- ❌ **Platform dependencies:** App Store optimization, social media marketing
- ❌ **Partnership integrations:** Vendor relationship management overhead

### **Integration Risk Assessment**

#### **Wearables Integration Risks**
**High Risk:**
- **API instability:** Health Connect, Oura, Fitbit APIs se měníse bez notice
- **Device fragmentation:** Android Health Connect support varies by manufacturer  
- **Data quality issues:** Inconsistent data formats, missing fields, sync delays

**Mitigation:**
- Graceful degradation - core functionality works without wearables
- Multiple data source fallbacks (manual entry vždy possible)
- Robust error handling a user feedback při sync issues

#### **Analytics/AI Features Risks**
**Medium Risk:**
- **Algorithm complexity:** Advanced ML models = maintenance burden
- **Data privacy concerns:** AI processing může konfliktovat s privacy-first positioning
- **Performance overhead:** Complex analytics na large datasets vs. simple daily tracking

**Mitigation:**
- Start with simple statistical analysis, postupně advanced features
- Client-side computation where possible (privacy preservation)
- Clear performance budgets a user-controlled analytics depth

#### **NightMotion Integration Risks**
**Low-Medium Risk:**
- **Hardware dependencies:** Camera/streaming setup failures
- **Network stability:** MJPEG streaming vulnerable k network issues  
- **Privacy sensitivity:** Video data storage a processing concerns

**Mitigation:**
- Optional feature clearly marked as experimental
- Local-only processing, no cloud storage of video data
- Graceful fallback to static image capture mode

### **Failure Mitigation Plans**

#### **Scenario 1: Health/Burnout Crisis**
**Triggers:** Persistent fatigue, depression episode, physical health issues
**Response:**
1. **Immediate:** Complete work pause 1-4 týdny
2. **Communication:** Auto-responder s "on health break" message  
3. **Technical:** Automated backups continue, monitoring alerts disabled
4. **Recovery:** Gradual re-engagement starting with 2-3h blocks
5. **Prevention:** Mandatory health breaks every 6-8 týdnů intensive work

#### **Scenario 2: Financial Pressure** 
**Triggers:** Income drop, unexpected expenses, revenue delays
**Response:**
1. **Prioritize:** Client work over Mosaic development
2. **Scope reduction:** Freeze new features, maintenance-only mode
3. **Monetization acceleration:** Fast-track premium features rollout
4. **Community:** Request user donations/sponsorship if product has traction
5. **Exit strategy:** Open-source release if unable to continue

#### **Scenario 3: Technical Disaster**
**Triggers:** Data loss, security breach, infrastructure failure
**Response:**
1. **Immediate:** Activate backup restoration procedures
2. **Communication:** Transparent user notification within 24h
3. **Investigation:** Root cause analysis a public post-mortem
4. **Remediation:** Security patches, improved backup procedures
5. **Trust rebuilding:** Enhanced transparency, security audit results

#### **Scenario 4: Market Validation Failure**
**Triggers:** Low user adoption, churn rates >80%, no paying users after 12 měsíců
**Response:**
1. **Pivot assessment:** Analyze user feedback pro possible pivots
2. **Scope reduction:** Focus na core daily tracking only
3. **Community handoff:** Open-source transition, community maintenance
4. **Learning extraction:** Document lessons learned for future projects
5. **Graceful shutdown:** 6-month notice, data export tools, user migration guide

### **Risk Monitoring Metrics**

#### **Personal Sustainability Indicators**
- **Weekly development hours:** Alert if >30h or <10h sustained
- **Feature completion rate:** Alert if dropping below 1 meaningful feature/month  
- **Health check-ins:** Weekly self-assessment (energy, motivation, stress level)
- **Financial runway:** Monthly burn rate vs. available resources

#### **Project Health Indicators**  
- **User engagement:** Daily/weekly active users, retention curves
- **Technical debt:** Code coverage, test failure rates, security scan results
- **Performance:** API response times, database query optimization needs
- **Community health:** GitHub issues/PRs activity, user feedback sentiment

---

### **Implementation Recommendations**

### **Immediate Actions (Q4 2024)**
1. **Messaging Consistency:** Update všech marketing materials s unified messaging
2. **Documentation:** Vytvořit "Getting Started" guide pro každou personu
3. **Metrics Tracking:** Implementovat analytics pro validation metrics
4. **Risk Monitoring Setup:** Basic health/financial tracking dashboard

### **Short-term (Q1 2025)**
1. **User Onboarding:** Guided setup flow pro different personas
2. **Self-hosting Documentation:** Detailed deployment guides
3. **Analytics Dashboard:** Enhanced Stats page s predictive features
4. **Backup/Recovery Testing:** Quarterly disaster recovery drills

### **Medium-term (H1 2025)**
1. **Wearable Integration:** Full Health Connect pipeline s graceful degradation
2. **API Documentation:** Complete API reference pro power users
3. **Community Building:** Discord/GitHub community pro feedback loop
4. **Sustainability Framework:** Automated health break scheduling, financial monitoring