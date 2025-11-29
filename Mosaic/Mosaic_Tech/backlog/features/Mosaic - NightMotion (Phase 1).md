## 🧩 Fáze 1 – Frontend (React)

### 1️⃣ Vytvoření základní struktury

- Přidat novou kartu `NightMotion.tsx` do `src/components/`.
    
- Přidat routu `/night-motion` do `App.jsx` (autentizovaný dashboard).
    
- Do `src/store/` přidat prázdný `nightMotionSlice.ts` (Redux Toolkit, initial state + reducers stub).
    

### 2️⃣ Formulář a UI layout

- Implementovat `FormWrapper` se třemi vstupy: `username`, `password`, `streamUrl`.
    
- Přidat tlačítko Start/Stop, indikátor stavu a `<video>` / `<canvas>` blok.
    
- Použít `react-hook-form` pro validaci a napojení na Redux state.
    

### 3️⃣ Logika start/stop a validace

- Implementovat thunk `startStream()` a `stopStream()` (simulace → později napojení na API).
    
- Po kliknutí Start → validovat vstupy, změnit stav na `connecting → playing`.
    
- Po kliknutí Stop → zastavit stream, resetovat stav na `idle`.
    

### 4️⃣ Persistování konfigurace

- Na `onSubmit` uložit `username`, `password`, `streamUrl` do `localStorage`.
    
- Na mount formu načíst poslední uložené hodnoty.
    
- Redux slice doplnit o hydratační logiku (`loadFromStorage`).
    

### 5️⃣ API napojení

- V `api.js` přidat wrapper `getStreamProxy(url, username, password)` → `GET /api/stream-proxy`.
    
- Thunk `startStream` přesměrovat na tento endpoint.
    
- Zpracovat `401`, `429`, `500` → toasty a ErrorState.
    

### 6️⃣ Styl a UX

- Přidat stavové barvy (šedá = idle, žlutá = connecting, zelená = playing, červená = error).
    
- Zajistit dark-mode kompatibilitu.
    
- Test vizuální konzistence s ostatními kartami (`FormWrapper`, `Loading`).
    

### 7️⃣ Testy (Jest + RTL)

- Ověřit renderování formu (3 vstupy + button).
    
- Test Start→Stop změny stavu v Redux slice.
    
- Snapshot test UI (Idle vs Playing).
    

---

## ⚙️ Fáze 2 – Backend (Flask)

### 8️⃣ Endpoint `/api/stream-proxy`

- V `app.py` vytvořit nový route `/api/stream-proxy`.
    
- Parametry `url`, `username`, `password` (přes `request.args`).
    
- JWT kontrola (`@jwt_required()`).
    

### 9️⃣ Stream handler

- Vytvořit pomocnou funkci `stream_rtsp(url, user, pass)` → yield MJPEG frames.
    
- Použít `subprocess.Popen(ffmpeg, stdout=PIPE)` a yieldovat boundary `frame`.
    
- Nastavit hlavičku `Content-Type: multipart/x-mixed-replace; boundary=frame`.
    

### 🔟 Bezpečnost a rate limit

- Přidat rate limit (v `security.py` → `limit_request("stream_proxy", per_minute=2)`).
    
- Kill proces po odpojení klienta (`GeneratorExit`).
    
- Žádné ukládání citlivých údajů.
    

### 11️⃣ Testy backendu

- `test_stream_proxy.py`:
    
    - validní RTSP → HTTP 200 a hlavička `multipart/x-mixed-replace`.
        
    - neautorizovaný → 401.
        
    - překročení limitů → 429.
        
    - odpojení klienta → subprocess ukončen.
        

---

## 🔗 Fáze 3 – Integrace a stabilizace

### 12️⃣ Propojení frontend ↔ backend

- Upravit `startStream()` → přímé napojení na `/api/stream-proxy`.
    
- `<video>` získává `src` = `apiBase + /api/stream-proxy?...`
    
- Test reálného spuštění streamu.
    

### 13️⃣ Ladění a UX drobnosti

- Ošetřit ztrátu spojení → stav `error`.
    
- Reset stavu po odhlášení uživatele.
    
- Toasty při chybném připojení („Stream nelze navázat“).
    

### 14️⃣ Dokumentace

- `docs/NightMotion_Phase1.md` – popis endpointu, struktury slice, test scénářů.
    
- Shrnutí v `CHANGELOG` + doplnění do Roadmap (Phase 1 ).
    

---

### 💡 Celkový odhad

|Oblast|Tokeny|Typ|
|---|---|---|
|Frontend implementace (1–7)|~1 400 tok.|🟨|
|Backend endpoint + testy (8–11)|~1 000 tok.|🟨|
|Integrace, UX, dokumentace (12–14)|~600 tok.|🟩|
|**Celkem**|**~3 000 tok.**|Střední feature (Phase 1 complete)|
