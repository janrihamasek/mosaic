# NightMotion Page Specification

## Identification
- Route: `/night-motion` (navigated when tab `NightMotion` is active)
- Primary component: `mosaic_prototype/frontend/src/components/NightMotion.tsx`
- Redux slice: `nightMotionSlice`
- Ancillary services: `authService` (`getAccessToken`, `getCsrfToken`), streaming proxy via `getStreamProxyUrl`
- API touchpoints: `/api/stream-proxy` (proxied MJPEG stream)

## Purpose
- Authenticate against proxied camera stream and render live NightMotion preview within dashboard shell
- Persist stream credentials client-side for rapid reconnects
- Provide start/stop controls with robust error handling and status feedback

## Layout
- Flex container (`layoutStyle`) splitting into two columns (form + preview); collapses to vertical stack under compact layout
- Form column uses `FormWrapper` with inputs for username, password (toggleable visibility), stream URL
- Video column (`videoWrapperStyle`) displays status indicator, optional error text, and stream preview area (img placeholder)
- Helper copy below preview explains latency and troubleshooting tips

## Interactive Elements
- Form submission runs validation, persists credentials to `localStorage` (`nightMotionConfig`), and invokes streaming logic
- Password visibility toggle switches between text/password inputs using inline button
- Start button disabled while stream starting/active; Stop button disabled in idle state
- Component listens for status changes and animates indicator (`statusVisible` fade)
- Stream lifecycle
  - On submit: dispatch `startStreamAction`, fetch MJPEG via proxy with auth headers, parse multipart frames
  - `AbortController` used for cancellation; `stopStream` dispatched on cleanup or stop button
  - Auto-transition to `error` status when fetch fails or `<img>` emits `onError`
- `useEffect` hydrates stored config once, resets on unmount to prevent leaks

## Data Bindings
- `selectNightMotionState` provides `{ username, password, streamUrl, status, error }`
  - Inputs register via `react-hook-form` and dispatch `setField` on change; also clears errors when user edits after failure
  - Status indicator maps to `statusColors`/`statusLabels`
  - Error copy bound to `error` state; resets on successful start or explicit stop
- Stream pipeline uses tokens from auth service to set `Authorization` and `X-CSRF-Token` headers
- `setStatus` transitions: `idle` → `starting` → `active`, or `error` with message “Stream nelze navázat” / “Vyplňte všechna pole” etc.
- Successful frame decode updates React state `streamSrc` (object URL) for `<img src>` binding
- Cleanup (`clearStreamResources`) revokes object URLs and aborts fetch to avoid memory leaks

## Styles
- Shared button/input styling from `styles/common.js`
- Video wrapper uses gradient background and border radius for premium look
- Status indicator color-coded via `statusColors`; dot uses box shadow to mimic glow
- Responsive adjustments via `useCompactLayout` for min heights and max video height

## Notes
- Streaming assumes MJPEG boundary `--frame`; adjust parser if backend format changes
- Credentials stored in `localStorage`; consider encryption/secure storage before shipping to production
- Proxy requires valid Mosaic session tokens—spec ensures `getAccessToken`/`getCsrfToken` present before attempting stream
- Current UI does not auto-retry on failure; future iteration could surface retry button or timed backoff
- Tests rely on Jest setup (TextEncoder/TextDecoder polyfills) to simulate stream parsing; keep parity when refactoring
