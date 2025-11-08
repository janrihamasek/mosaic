# Deploying the Mosaic PWA

The React frontend now ships as an installable Progressive Web App (PWA). This guide summarizes the required steps to build, host, and verify the offline-ready bundle.

## Requirements

- HTTPS-enabled origin (Chrome, Edge, Safari require secure contexts for installation).
- Service-worker friendly hosting that serves `index.html` for unknown routes (already configured in the generated `sw.js` fallback).
- Ability to serve the static assets produced by `npm run build` (or the Dockerfile frontend image).

## Build Steps

```bash
cd mosaic_prototype/frontend
npm install
npm run build
```

During `npm run build`, `react-scripts` compiles the React bundle, copies the manifest/icons from `public/`, and Workbox injects the precache manifest into `build/service-worker.js`. The output folder contains:

- `manifest.json` referencing `/icons/icon-192.png` and `/icons/icon-512.png`.
- `service-worker.js` which precaches the UI shell, provides a navigation fallback to `index.html`, caches static assets with a cache-first strategy, and caches API GET responses using network-first.

## Hosting Checklist

1. Serve the contents of `build/` via HTTPS.
2. Ensure `/manifest.json` and `/icons/*` are publicly reachable (they are copied during the build).
3. Redirect all unknown routes to `/index.html` so client-side routing works after refreshes or offline. The Workbox navigation route already falls back to the shell for offline visits.
4. When deploying behind a proxy, expose the `service-worker.js` file without additional caching/proxy rewrites.
5. For Docker-based deployments, rebuild the frontend image so the new manifest, icons, and service worker are included.

## Verifying Installation

1. Visit the hosted site over HTTPS using Chrome/Edge.
2. Open DevTools → Application → Manifest to confirm icons/theme colors were detected.
3. Use the browser’s “Install App” prompt or the new “Install App” button in the Mosaic header (only appears when eligible) to trigger the Add-to-Home-Screen flow.
4. Toggle “Offline” in DevTools and reload—`/today`, `/entries`, `/stats`, etc. should render from precache with API requests served from the network-first cache when previously visited.

Following these steps keeps the PWA installable on both desktop and mobile while preserving the single responsive layout shared across devices.
