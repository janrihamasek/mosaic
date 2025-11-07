# NightMotion Page Specification

## Identification
- Location: `Dashboard` → `Admin` tab → `NightMotion` section (admin-only)
- Wrapper: `AdminNightMotion.jsx` (renders `NightMotion.tsx`)
- Redux slice: `nightMotionSlice`
- Ancillary services: `authService` (`getAccessToken`, `getCsrfToken`), streaming proxy builder `getStreamProxyUrl`
- API touchpoints: `/api/stream-proxy` (MJPEG stream, inherits global auth/API key headers)

## Purpose
- Allow administrators to proxy a secured NightMotion RTSP feed through Mosaic without exposing credentials in the browser.
- Persist per-operator credentials locally for fast reconnects during surveillance/debug sessions.
- Co-locate advanced tooling (start/stop controls, troubleshooting) with the rest of the Admin surface.

## Layout
- Flex container (`layoutStyle`) splitting into two columns (form + preview); collapses to vertical stack on compact layouts.
- Form column uses `FormWrapper` with inputs for username, password (toggleable visibility), and stream URL.
- Video column (`videoWrapperStyle`) displays status indicator, optional error copy, and the MJPEG preview `<img>`.
- Helper copy under the preview clarifies latency expectations and rate limiting (2 requests/minute).

## Interactive Elements
- Form submission validates required fields, persists credentials to `localStorage` (`nightMotionConfig`), and kicks off the streaming pipeline.
- Password visibility toggle switches between `type="password"` / `type="text"`.
- Start button disabled while `status === "starting"` or `status === "active"`; Stop disabled when idle.
- Status indicator animates based on `nightMotion.status` (`idle`, `starting`, `active`, `error`) and includes textual feedback.
- Stream lifecycle:
  1. Dispatch `startStream` (clears errors, sets `status="starting"`).
  2. Build proxy URL via `getStreamProxyUrl` and fetch the MJPEG stream with JWT, CSRF, and API key headers.
  3. Update `<img>` source with the response stream; listen for `onError` to flip to `error` state.
  4. `AbortController` halts the request when stopping or unmounting; `stopStream` resets slice state.
- Admin tab unmounts the component when navigating away, ensuring resources are released.

## Data Bindings
- `selectNightMotionState` → `{ username, password, streamUrl, status, error }`.
  - Inputs dispatch `setField` on change and clear previous errors.
  - Status indicator + helper text derive from `status` and `error`.
- Stream pipeline uses tokens from `authService` (`getAccessToken`, `getCsrfToken`) to populate headers and meet `/api/stream-proxy` security requirements.
- `setStatus` transitions enforce `idle → starting → active` or `error`; stopping resets credentials unless user stored them explicitly.
- Object URLs created for the `<img>` preview are revoked in the cleanup effect to avoid memory leaks.

## Styles
- Shared button/input styling from `styles/common.js`
- Video wrapper uses gradient background and border radius for premium look
- Status indicator color-coded via `statusColors`; dot uses box shadow to mimic glow
- Responsive adjustments via `useCompactLayout` for min heights and max video height

## Notes
- Section only renders for admins; `Admin.jsx` omits it for standard users to avoid exposing protected tooling.
- Backend enforces a per-minute rate limit; surface clearer UI feedback if we detect 429 responses.
- Streaming assumes MJPEG boundary `--frame`; adjust parser if backend format changes.
- Credentials remain in `localStorage`; consider encryption or per-user secrets before production rollout.
- Tests rely on Jest setup (TextEncoder/TextDecoder polyfills) to simulate stream parsing; keep parity when refactoring.
