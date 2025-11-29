Jan, vezmeme to po malých, ověřitelných krocích. Každý krok má “co udělat” a “co čekat v logu/na obrazovce”. Když něco nevyjde, napiš, kde to spadlo — navážeme přesně tam.

I. Předpoklady (jednorázově)

1. [x] Zařízení: fyzický Android s Android 13+ a aplikací “Health Connect by Android”. Ověř: Health Connect otevřeš a povolíš přístup (kroky, tep, spánek) alespoň jedné fitness aplikaci, která data produkuje (Google Fit, výrobce hodinek apod.).
    
2. [x] Backend: běží a je dostupný z telefonu přes LAN (např. [http://192.168.x.y:5001](http://192.168.x.y:5001/)). V `.env` mobilu si připrav BASE_URL, případně `X-API-Key`.
    
3. [x] Autentizace: máš endpoint `/login` a získáš JWT. Na mobilu zajistíme `jwtProvider()` (funkce, která vrátí platný token).
    

Očekávané logy backendu: nic speciálního zatím.

II. Přidání pluginu do mobilní app

1. Instalace: v kořeni mobilu přidej plugin (lokální cesta nebo balík).  
    npm i ./mobile/plugins/healthconnect-agent  
    npx cap sync android
    
2. Konfigurace: do `capacitor.config.ts` uveď API base URL a volitelně device name.
    
3. Android projekt otevři v Android Studiu, zkontroluj závislosti `androidx.health.connect:connect-client` a oprávnění v `AndroidManifest.xml` (READ_* pro steps/heart-rate/sleep).
    
4. Povolit cleartext pro vývoj (pokud používáš HTTP): `network_security_config` s povolením pro tvoji LAN IP, plus `android:usesCleartextTraffic="true"` pro debug build.
    

Očekávané logy: `npx cap sync android` projde bez chyb; Android Studio nehlásí chybějící permission.

III. Inicializace na JS/TS straně

1. V bootstrapu app přidej inicializaci:  
    import { HealthConnectAgent } from 'healthconnect-agent'  
    HealthConnectAgent.init({ baseUrl: process.env.BASE_URL, jwtProvider, deviceId: persistedUuid() })
    
2. Implementuj `jwtProvider`: po přihlášení ulož JWT (SecureStorage/Storage) a vracej ho při volání.
    
3. `persistedUuid()`: vygeneruj jednou (crypto UUID) a ulož pro další běhy.
    

Očekávané logy: žádné chyby v konzoli; `init` proběhne.

IV. Povolení přístupů (runtime permissions)

1. Při prvním vstupu do “Wearables” obrazovky vyvolej žádost o Health Connect oprávnění (plugin ji má vystavenou, případně metoda `requestPermissions(types)`): steps, heart rate, sleep.
    
2. Uživatele proveď systémovým dialogem Health Connect (povolí datové kategorie).
    

Očekávané chování: systémové dialogy se zobrazí; po schválení plugin vrátí “granted: true”.

V. První “read-only” test (bez odesílání)

1. Spusť:  
    const since = new Date(Date.now() - 24*3600e3).toISOString();  
    const steps = await HealthConnectAgent.readSteps({ since });  
    const hr = await HealthConnectAgent.readHeartRate({ since });  
    const slp = await HealthConnectAgent.readSleepSessions({ since });
    
2. Zkontroluj, že každý záznam má kanonickou podobu: `{ type, start, end?, fields, dedupe_key }`.
    

Očekávané logy: v JS uvidíš počty záznamů; typicky jednotky až stovky položek/den.

VI. Fronta a delta (IndexedDB)

1. Zapni frontování: `await HealthConnectAgent.queueDeltas({ since })`. To uloží čtené položky do `pending_readings` a nastaví “checkpointy” pro další delta-run.
    
2. Zavolej `await HealthConnectAgent.getPendingCount()` – měl bys vidět nenulový počet.
    

Očekávané logy: žádná chyba; počty pending položek v řádu toho, co se načetlo.

VII. První odeslání na backend

1. Ověř, že `jwtProvider()` vrací platný JWT.
    
2. Spusť: `await HealthConnectAgent.syncPending()` — to odešle dávky na `/ingest/wearable/batch` s hlavičkami `Authorization: Bearer <JWT>` a `X-Device-Id`.
    
3. Plugin používá exponenciální backoff; při chybě síť/401/429 to uvidíš v návratové hodnotě a pending zůstane.
    

Očekávané logy backendu:

- 200 OK s počty `{accepted, duplicates, errors:[]}` v JSON.
    
- Ve strukturovaných logách přibydou `request.completed` pro `POST /ingest/wearable/batch`.
    
- Při opakovaném `syncPending()` uvidíš nárůst `duplicates` (správně — dedupe funguje).
    

VIII. Kontrola agregací

1. Po úspěšném ingestu spusť job agregací (pokud máš CLI/cron), nebo počkej na on-write aktualizaci.
    
2. Ověř obsah `wearable_daily_agg` (např. přes dočasný admin endpoint nebo přímo v DB).
    
3. (Volitelně) zapni na frontendu volání `/wearable/day?date=YYYY-MM-DD` — pokud už máš implementované, uvidíš reálná čísla.
    

Očekávané logy: dotazy na agregace; žádné 404, pokud jsi endpointy zavedl.

IX. Autosync a provoz

1. Přidej posluchače konektivity: při přechodu “offline→online” volej `syncPending()`.
    
2. Přidej periodický režim v popředí (např. `setInterval` každé 2–3 h: `queueDeltas({ since: lastCheckpoint })` → `syncPending()`).
    
3. Později lze přidat background (WorkManager) přes Capacitor plugin/bridge.
    

X. Troubleshooting (rychlá mapa)

- 401/403: zkontroluj JWT (expirace), `X-API-Key` a CORS/network-security na Androidu.
    
- 404: špatná BASE_URL nebo chybí ingest endpoint.
    
- 429: rate limit; sniž frekvenci, nech backoff doběhnout.
    
- Prázdná data: Health Connect nemá zdroj; otevři Health Connect a povol sdílení z aplikace, která data generuje.
    
- HTTP na LAN: povol cleartext pro debug a přidej výjimku pro IP v `network_security_config`.
    

Co dál po rozchození “end-to-end”

- Přidej HealthConnect Inspector do Adminu (přehled posledních dávek, počty, duplicitní %).
    
- Přidej UI indikátory stavu syncu (pending count, naposledy synchronizováno).
    
- Zaveď metriky ingest pipeline v `/metrics` (počty přijatých/duplicit/chyb).
    

Chceš, abych ti připravil krátký testovací skript (TS) pro kroky V–VII, který si vložíš do mobilní obrazovky “Debug Wearables” a který vypíše počty načtených, zařazených a odeslaných záznamů?