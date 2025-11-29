# Daily Log – 2024-11-08

- Date: 2024-11-08
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 8_11_mosaic.md

## Notes (raw import)

- [x]  Zavést **responzivní layout** a **PWA podporu**. 🟧 (~3 000 tok.)
- [ ] streak se neukazuje při dnešním datu

---
251108_backend_cache_user_namespace_fix
Goal: Prevent cross-user leakage in cached payloads for /today and /stats by namespacing caches with user_id and role.  
DONE
Backend Cache
- Introduced CacheScope plus helpers to prepend user:{id}/role:{...} segments to every cache key so entries are automatically namespaced per-tenant (mosaic_prototype/backend/app.py (lines 150-177), app.py (lines 458-548)). Each cache record now carries its originating scope, and cache_get emits a cache.cross_user_hit warning if a request ever resolves to a payload produced for another user.
- /stats/progress and /today build the appropriate CacheScope before calling the cache helpers, keeping mutation invalidations intact while ensuring admins/users only read their own cached payloads (mosaic_prototype/backend/app.py (lines 2051-2307), app.py (lines 2313-2376)).
Tests & Docs
- Updated the stats cache invalidation test to derive the correct namespaced key via the new helper, preventing brittle string assumptions (mosaic_prototype/backend/tests/test_api.py (lines 722-778)).
- Added tests/test_cache_namespace.py which provisions two users, warms the cache for user A, and verifies user B continues to see empty /today and /stats/progress responses, guarding against future regression leaks (mosaic_prototype/backend/tests/test_cache_namespace.py (lines 1-68)).
- Documented the fix in docs/changelog/2025-11-08_backend_cache_user_namespace_fix.md (lines 1-5) so release notes highlight the tenant-safety change.

251108_frontend_pwa_installable_adaptive
Goal: Enable installable PWA with identical adaptive UI across mobile and desktop, no separate themes.  
DONE
PWA Updates
- Added a full web manifest with theme/background colors plus branded icons so browsers can detect the installable app shell (public/manifest.json (lines 1-17), referenced in public/index.html (lines 14-21)).
- Introduced a custom Workbox service worker that precaches the UI shell, routes SPA navigations back to index.html, serves static assets cache-first, and keeps API GET calls network-first with a short timeout (src/sw.js (lines 1-86)). It’s registered only on secure production origins via the new registerServiceWorker helper and bootstrap hook (src/registerServiceWorker.ts (lines 1-48), src/index.jsx (lines 1-19)).
- Documented the deploy steps (HTTPS requirement, build process, verification checklist) in docs/DEPLOY_PWA.md (lines 1-39) so ops knows how to ship the PWA bundle.
- Declared the Workbox runtime deps so future installs pull in the modules we import directly (package.json (lines 6-20)).
Responsive UI
- Dashboard now derives availableTabs from the user role and forces non-admins back to standard tabs, preventing accidental exposure of the admin view (src/Dashboard.jsx (lines 57-139)).
- Captured the beforeinstallprompt event and expose an inline “Install App” button that triggers the A2HS flow when eligible; success is surfaced through the existing toast system (src/Dashboard.jsx (lines 72-224)).
- Reworked the tab bar so it docks to the bottom of small screens while leaving the desktop layout untouched, and padded the container to avoid overlap (src/Dashboard.jsx (lines 174-283), src/styles/common.js (lines 315-340)). This keeps the single responsive design but gives mobile users the expected bottom navigation affordance.

251108_frontend_backend_offline_sync_indexeddb
Goal: Implement offline-first writes for Today/Activities using IndexedDB with periodic and on-demand sync; local data wins on conflict.  
DONE
Offline Sync
- Added IndexedDB-backed helpers plus a sync manager (frontend/src/offline/db.ts, frontend/src/offline/queue.ts, frontend/src/offline/syncManager.ts, frontend/src/offline/snapshots.ts) to persist pending mutations and cached Today/Activities snapshots, replaying the queue every 60 s and whenever the browser comes back online.
- Entries and Activities thunks now save/load snapshots, route writes through the offline queue, and update local caches so Today and Activities stay usable offline (frontend/src/store/entriesSlice.ts (line 95), frontend/src/store/activitiesSlice.ts (line 1)). Dashboard shows backend/offline/sync badges driven by the new Redux slice (frontend/src/store/offlineSlice.ts (line 1), frontend/src/Dashboard.jsx (line 44)), and the store bootstraps the sync loop (frontend/src/store/index.ts (line 1)).
- Documented the workflow in docs/OFFLINE.md (line 1) and added Jest coverage for the queue, including the overwrite retry path (frontend/src/__tests__/offline_sync.test.ts (line 1)).
Backend Idempotency
- Introduced an in-memory idempotency cache plus helper utilities (backend/app.py (lines 175-220)) and wired /add_entry and /add_activity to honour X-Idempotency-Key, returning cached responses on replay and storing results after successful mutations (backend/app.py (line 1704), backend/app.py (line 1880)).
- /add_activity now understands X-Overwrite-Existing so local data can overwrite server-side conflicts during sync, and pytest coverage verifies idempotent entries plus overwrite behaviour (backend/tests/test_idempotent_writes.py (line 1)).

251108_backend_https_ip_cert
Goal: Enable HTTPS on the Mosaic Flask backend using a self-signed certificate bound to the server’s LAN IP (e.g. 192.168.x.x) instead of localhost.  
DONE
HTTPS Support
- Added https_utils.py and wired app.py to read USE_HTTPS/SERVER_IP. When enabled, Flask now listens on 0.0.0.0 with an ssl_context that points to `./certs/<ip>.pem/-key.pem` (configurable via SSL_CERT_DIR) and respects FLASK_RUN_HOST/PORT. This lets you run the backend directly or via Docker with mkcert-issued IP certs (mosaic_prototype/backend/app.py (line 22), app.py (line 2611), backend/https_utils.py (line 1)).
- Docker Compose mounts a shared ./certs directory into each backend service so the containers can read the LAN IP certificate (docker-compose.yml (line 38), docker-compose.yml (line 66), docker-compose.yml (line 90)).
- .env.dev gained USE_HTTPS and SERVER_IP placeholders (mirroring what you already added to .env.prod) to make this workflow discoverable.
Docs
- docs/DEPLOY_PWA.md now documents mkcert-based LAN certificates: generating 10.0.1.31.pem, mounting them into ./certs, setting USE_HTTPS/SERVER_IP, and trusting the CA on mobile so PWAs can install over HTTPS (docs/DEPLOY_PWA.md (lines 1-40)).
Bug Fix
- Defensive guard around the offline queue ensures listPendingWrites() returning undefined (e.g., transient IndexedDB hiccup) won’t crash the sync loop (frontend/src/offline/queue.ts (lines 151-165)).