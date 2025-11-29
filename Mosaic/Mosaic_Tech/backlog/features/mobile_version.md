Zde je přehledný seznam všech **rozhodnutí**, která je potřeba učinit, než se pustíme do implementace mobilní verze a PWA vrstvy Mosaicu.  
Rozděleno podle oblastí, ve kterých mají důsledky pro architekturu, UI a budoucí rozvoj.

---

## 1. **Rozložení a navigace**

1.1. Zda bude mobilní navigace **horizontální tab bar** (5 ikon dole) nebo **burger menu** v horní části. 
- horizontální tab bar
1.2. Zda se má **Admin** skrývat u běžného uživatele zcela, nebo zůstat dostupný jako poslední položka.  
- admin se skryje pro všechny a udělá se User, kde se bude nastavovat běžný uživatel.
1.3. Zda se má **Dashboard / karty** zobrazovat ve stacku (vertikálně pod sebou) nebo jako jednotlivé samostatné pohledy (každý na své stránce).
- jednotlivé pohledy

---

## 2. **Rozsah responzivity**

2.1. Jaké **breakpointy** budou oficiálně podporované (např. <640 px mobil, 640–1024 tablet, >1024 desktop).  
- ano
2.2. Zda bude **desktop layout zachován beze změny** a jen doplněn o mobilní variantu, nebo se sjednotí do jednoho adaptivního systému.  
- sjednotí do jednoho adaptivního systému
2.3. Jak se mají chovat **formuláře a tabulky** – zda se na mobilu přepnou do „karetního“ zobrazení, nebo zůstanou tabulkové s horizontálním skrollem.
- některé části, např. entries bude třeba nechat jako scroolovací tabulku, jinak co půjde převedeme do karetního zobrazení

---

## 3. **PWA charakteristiky**

3.1. Zda Mosaic má být jen **„instalovatelný web“ (standalone mode)**, nebo má mít i **offline funkce**.  
- musí mít offline funkce
3.2. Pokud offline:  
 – Které části musí fungovat bez internetu (např. Today, Stats, Entries).  
 – Zda povolit **lokální zápis a pozdější synchronizaci** (složitější, ale výrazně uživatelsky přínosné).  
- určitě Today pro možnost aktuálního zápisu, Activities pro tvorbu aktivit. ten zbytek nevím, nemám žádný cloud, tak musím mít zatím možnost všechno obsluhovat lokálně
3.3. Zda bude použit **CRA default service worker** nebo vlastní řešení s Workboxem (lepší kontrola, ale víc práce).  
- to nevím co je, potřebuji víc informací.
3.4. Jaký má být **název a ikony PWA** (název aplikace, barevné schéma, splash screen).
- potřebuji více informací

---

## 4. **Data a úložiště**

4.1. Kde se mají ukládat data pro offline režim – `localStorage` (jednodušší) nebo `IndexedDB` (vhodnější pro větší množství dat).  
- IndexedDB
4.2. Jaké množství dat má být k dispozici offline (poslední den, týden, celý měsíc?).  
- ideálně tři měsíce, netuším kolik to je místa
4.3. Jak se bude řešit **konflikt mezi lokálními a serverovými daty** po opětovném připojení.
- lokální data jsou nadřazená serverovým

---

## 5. **Bezpečnost**

5.1. Zda se má JWT token ukládat do `localStorage` (kompatibilní s PWA) nebo zůstat čistě v paměti.  
- uděláme to tak, jak je to z bezpečnostního i architektonického hlediska správně
5.2. Jak zacházet s CSRF tokeny při offline režimu (ignorovat při lokálním zápisu, validovat při synchronizaci?).  
- potřebuji více informací, preferuji ale správný a oficiální způsob
5.3. Jak dlouho mohou být data uložena offline (např. auto-expirace po 24 h).
- to záleží na tom, kolik jich bude a jakou další pamětí bude aplikace disponovat

---

## 6. **Testování a rollout**

6.1. Na jakých **mobilních prohlížečích** se bude oficiálně testovat (Chrome, Safari, Firefox, Samsung Internet).  
- hlavně Chrome, ale moje primární snaha je, aby to beželo jako aplikace, ne v prohlížeči
6.2. Zda bude Mosaic PWA **veřejně dostupný k instalaci** (z produkční domény) nebo jen jako interní test (přes dev/staging).  
- nejdřív ne, pak ano
6.3. Kdy proběhne **fáze pilotního testu** (interní test na několika zařízeních, sběr zpětné vazby).
- až to bude hotové

---

## 7. **Směřování do budoucna**

7.1. Zda má mobilní verze sloužit **jen jako rozšíření webu**, nebo být časem základem pro **nativní Mosaic Mobile** (Android, Health Connect, senzory).  
- a proč teda neudělat rovnou nativní Mosaic Mobile s možností ovládání v prohlížeči?
7.2. Pokud ano, jak moc má být současný kód připraven na pozdější extrakci do React Native / Capacitor.
 - to já nevim

---

Až tyto body projdeš a rozhodneš (stačí krátce „ano / ne / spíš ano / spíš ne“ + poznámky), mohu ti na jejich základě připravit přesnou specifikaci implementace – už zaměřenou na realistický první milník: **mobilní Mosaic (responzivní + instalovatelný)**.