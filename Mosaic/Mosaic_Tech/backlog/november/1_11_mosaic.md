# Daily Log – 2024-11-01

- Date: 2024-11-01
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 1_11_mosaic.md

## Notes (raw import)

# Updated the docs so they reflect the new unified stats flow.

- mosaic_prototype/docs/API_DOCS.md (line 291) now documents the dashboard-style /stats/progress response (single snapshot, new metrics, revised caching, streak rules) and refreshes the index notes to match the active-activity calculations.
- mosaic_project_current_state.md (line 12) and surrounding sections describe the TypeScript noEmit setup, the unified stats pipeline, the Redux snapshot shape, refreshed dashboard widgets, and the new analytics/testing priorities.

# Fáze 1 – Stabilizace a typizace
1. 251101_frontend-convert_formwrapper_datatable_tsx  
Goal: Convert FormWrapper.jsx and DataTable.jsx to .tsx with typed props.

DONE
- Converted src/components/shared/FormWrapper.tsx (line 1) to TypeScript, wiring in the shared FormWrapperProps, routing loading state through <Loading inline />, and tightening the action controls while preserving existing layout behaviour.
- Rebuilt src/components/shared/DataTable.tsx (line 1) as a typed component that normalises column metadata, reuses <Loading /> and <ErrorState /> for state handling, and keeps compact/desktop rendering intact.
- Centralised prop typing in src/types/props.d.ts (line 1) with reusable FormWrapperProps, DataTableProps, and helpers, and updated ActivityTable.jsx (line 184) and EntryTable.jsx (line 130) to pass string-based loading copy expected by the new signature.

2. 251101_types-api_and_store_state_definitions
Goal: Add strong TypeScript types for API responses and Redux slices.

DONE
- Hardened the shared API contracts (src/types/api.d.ts (line 1)) and captured Redux slice shapes plus reusable error/status helpers (src/types/store.d.ts (line 1)) for consistent typing across the app.
- Migrated the store entry point to TypeScript with typed helpers (src/store/index.ts (line 1)) and fully annotated the auth, entries, and activities slices (src/store/authSlice.ts (line 1), src/store/entriesSlice.ts (line 1), src/store/activitiesSlice.ts (line 1)) using the new interfaces and typed thunks.
- Ensured all async flows return structured data/typed reject values, and updated slice reducers/selectors to lean on the shared state contracts.

- 251101_frontend-unify_loading_error_stats
Goal: Replace ad-hoc loading/error handling in `Stats.jsx` with shared components.

DONE
- Unified the stats async flow to short-circuit on status (src/components/Stats.jsx (line 1)) using the shared Loading/ErrorState components, renamed the retry handler to refetchStats, and removed bespoke spinner/error branches.
- Exposed named exports for the shared status components while preserving defaults (src/components/Loading.tsx (line 1), src/components/ErrorState.tsx (line 1)) so Stats and future callers can import them consistently.

- 251101_frontend-eslint_prettier_ci_setup
Goal: Integrate ESLint and Prettier into the existing CI workflow.

DONE
- Added project-wide lint/format configs (mosaic_prototype/frontend/.eslintrc.cjs (line 1), .prettierrc.json (line 1)) and wired an npm run lint script (mosaic_prototype/frontend/package.json (line 18)) to standardise analysis across JS/TS files.
- Updated CI to fail on ESLint issues before building (.github/workflows/tests.yml (line 39)) and resolved existing hook/dependency violations so linting passes cleanly (mosaic_prototype/frontend/src/components/Notification.jsx (line 5), .../ActivityTable.jsx (line 56), .../EntryTable.jsx (line 30)).

5. 251101_frontend-minimal_jest_tests
Goal: Add baseline Jest + React Testing Library tests for forms, Redux thunks, and toast rendering.

DONE
- Added Jest + Testing Library setup (mosaic_prototype/frontend/jest.config.js (line 1), mosaic_prototype/frontend/jest.environment.js (line 1), mosaic_prototype/frontend/src/setupTests.ts (line 1)) and registered supporting typings/dev-deps in mosaic_prototype/frontend/package.json (line 16).
- Covered login form validation/dispatch flow, entries thunk state changes, and toast visibility with new baseline tests (mosaic_prototype/frontend/src/__tests__/LoginForm.test.tsx (line 1), .../entriesSlice.test.ts (line 1), .../toast.test.tsx (line 1)).
- Wired CI to run the lint + Jest suites before the build so failures surface early (.github/workflows/tests.yml (line 38)).

# Fáze 1 – Frontend (React) - NightMotion
251101_frontend-nightmotion_phase1
Goal: Implement full frontend for new **NightMotion** feature (Phase 1) — camera stream viewer with form, state logic, and local persistence.

DONE
NightMotion now has a full Redux-backed UI, protected route, and test suite, matching the Phase 1 brief.

- Added dedicated NightMotion slice with typed state, start/stop thunks, and selector so the UI can model idle → connecting → playing/error transitions (mosaic_prototype/frontend/src/store/nightMotionSlice.ts:5).
    
- Registered the slice in the root store and exposed it through the dashboard/route stack, including a protected /night-motion route that syncs with tab selection and localStorage (mosaic_prototype/frontend/src/store/index.ts:15, mosaic_prototype/frontend/src/App.jsx:29, mosaic_prototype/frontend/src/Dashboard.jsx:26).
    
- Implemented the NightMotion card with react-hook-form, local persistence, toast hooks, password toggle, video proxy binding, and animated status indicator (mosaic_prototype/frontend/src/components/NightMotion.tsx:38).
    
- Exposed getStreamProxyUrl for building authenticated stream URLs (mosaic_prototype/frontend/src/api.js:91) and enhanced FormWrapper so the Stop button can share styling while honouring disabled state (mosaic_prototype/frontend/src/components/shared/FormWrapper.tsx:13, mosaic_prototype/frontend/src/types/props.d.ts:29).
    
- Extended Jest setup with a matchMedia stub and added comprehensive component + reducer tests (fake timers, snapshots, media stubs) so the new behaviour is covered (mosaic_prototype/frontend/src/setupTests.ts:31, mosaic_prototype/frontend/src/**tests**/NightMotion.test.tsx:71, mosaic_prototype/frontend/src/**tests**/nightMotionSlice.test.ts:8, mosaic_prototype/frontend/src/**tests**/**snapshots**/NightMotion.test.tsx.snap:1).
    
- Tests: npm test -- --runInBand

# Fáze 2 – Backend (Flask) - NightMotion
251101_backend_stream_proxy_endpoint
**Goal:** Implement backend endpoint `/api/stream-proxy` for NightMotion feature with authentication, rate limiting, and proper MJPEG streaming.

DONE
- dded authenticated /api/stream-proxy route with per-minute throttling, up-front frame priming, and multipart MJPEG response (mosaic_prototype/backend/app.py:419).
- Introduced lightweight jwt_required decorator plus FFmpeg-backed stream_rtsp helper that normalises RTSP URLs, drains stderr asynchronously, and cleans up on disconnect (mosaic_prototype/backend/app.py:117, mosaic_prototype/backend/app.py:154).
- Extended security utilities with limit_request so the proxy reuses existing rate-limiter wiring (mosaic_prototype/backend/security.py:44).

251101_backend_stream_proxy_handler
**Goal:** Implement `stream_rtsp()` helper to fetch and yield MJPEG frames using ffmpeg.

- Implemented stream_rtsp() to spin up ffmpeg, normalise RTSP URLs, and yield multipart MJPEG frames while draining stderr asynchronously for diagnostics (mosaic_prototype/backend/app.py:170).
- Added safe teardown (terminate/kill) on disconnect or error, with logging for missing frames or ffmpeg failures (mosaic_prototype/backend/app.py:247).
- Introduced convenience rate limiter helper and authenticated /api/stream-proxy route that handles missing credentials and propagates structured MJPEG response headers (mosaic_prototype/backend/security.py:44, mosaic_prototype/backend/app.py:418).

# bugfixing - Stram does not work

251101_backend-stream_proxy_camera_credentials
Goal: Allow Mosaic’s authenticated users (JWT) to pass camera credentials (username, password) through `/api/stream-proxy` to FFmpeg.
DONE
- Added targeted /api/stream-proxy tests covering happy path (mocked MJPEG frames, multipart header), missing auth, rate limiting, and generator cleanup on disconnect with a fake ffmpeg process (mosaic_prototype/backend/tests/test_stream_proxy.py:1).
- Verified Python sources compile (python3 -m py_compile …). Full pytest run still blocked until backend requirements get installed (python3 -m pytest currently fails with “No module named pytest”).
- Updated the stream proxy to build an RTSP URL with camera credentials when provided, log the final endpoint, and continue handing it off to stream_rtsp after JWT + rate-limit checks (mosaic_prototype/backend/app.py:420).
- Enhanced _normalize_rtsp_url to preserve pre-embedded credentials so downstream helpers don’t strip username/password when they already exist (mosaic_prototype/backend/app.py:128).
- Added user-friendly 400 JSON response when the RTSP URL is missing from the query string (mosaic_prototype/backend/app.py:422).

251101_backend-stream_proxy_dual_auth_fix
Goal: Fix 401 error by ensuring `/api/stream-proxy` correctly handles dual authentication
DONE
- Updated /api/stream-proxy so it still enforces the Mosaic JWT rate limit, then safely embeds supplied camera credentials into the RTSP URL (when not already present) before handing the request to FFmpeg. As required, the handler now returns Response(stream_rtsp(rtsp_url), mimetype="multipart/x-mixed-replace; boundary=frame") and keeps Mosaic auth separate from camera auth (mosaic_prototype/backend/app.py (line 432)).
- Simplified _normalize_rtsp_url and stream_rtsp to work with a credential-ready URL, dropping extraneous parameters and unused imports (mosaic_prototype/backend/app.py (line 122)).
- Adjusted stream proxy tests to reflect the new helper signature and the embedded-credential RTSP URL (mosaic_prototype/backend/tests/test_stream_proxy.py (line 18)).

251101_frontend-nightmotion_stream_auth_fix
Goal: Ensure Mosaic JWT and CSRF headers are sent with NightMotion stream requests.
DONE
- Updated frontend/src/services/authService.js (line 110) so getAuthHeaders() always returns the Mosaic Authorization and X-CSRF-Token headers when available, removing the method-based gating.
- Simplified the Axios interceptor in frontend/src/apiClient.js (line 17) to unconditionally merge those auth headers for every non-login/register request.
- Reworked frontend/src/components/NightMotion.tsx (lines 86-325) to import the auth helper, stream via fetch with JWT/CSRF headers, create a blob URL for playback, and cleanly revoke object URLs on stop/unmount.
- Enhanced frontend/src/__tests__/NightMotion.test.tsx (lines 11-216) to mock fetch/URL APIs, assert that stream requests include the auth headers, and verify object URL lifecycle; updated the related snapshot (frontend/src/__tests__/__snapshots__/NightMotion.test.tsx.snap).

251101_frontend-nightmotion_mjpeg_display_fix
Goal: Fix NightMotion component so the MJPEG stream displays correctly and UI state reflects connection status.

DONE
Swapped NightMotion over to an <img>-based MJPEG flow and reworked status handling so the UI tracks Idle → Starting → Active while still pushing Mosaic auth tokens to the proxy.

- frontend/src/components/NightMotion.tsx:33-44,72-176 adds the new starting/active status palette and uses local streamSrc state plus stop hooks to drive the Start/Stop buttons.
- frontend/src/components/NightMotion.tsx (lines 227-291) now derives the proxy URL once, appends JWT/CSRF query params via getAuthHeaders, kicks off the stream with startStream(), and moves status transitions into the image onLoad/onError callbacks (358-383 renders the <img> placeholder/stream).
- frontend/src/store/nightMotionSlice.ts (lines 5-71) updates the slice to the new status enum and simplifies startStream/stopStream thunks to just flip flags without async delays.
- frontend/src/__tests__/NightMotion.test.tsx (lines 63-190) and frontend/src/__tests__/__snapshots__/NightMotion.test.tsx.snap exercise the new flow (including tokenized stream URLs and the <img> rendering) while frontend/src/__tests__/nightMotionSlice.test.ts (lines 9-24) checks the revised reducers.

251101_frontend-nightmotion_secure_stream_fetch
Goal: Replace direct <img src> approach with secure authenticated MJPEG fetch that includes Mosaic JWT and CSRF headers.

DONE
- Refactored frontend/src/components/NightMotion.tsx (lines 150-386) to stream MJPEG via an authenticated fetch: we now pull tokens from authService, attach Authorization/X-CSRF-Token headers, manage an AbortController, and keep/revoke blob URLs so Stop/unmount cancels the request and frees resources. UI rendering now shows an <img> only when the stream is active and surfaces “Starting…”/error states for other phases.
- Added dedicated token helpers in frontend/src/services/authService.js (lines 160-167) so components can grab the access/CSRF tokens without exposing them in query strings.
- Reworked frontend/src/__tests__/NightMotion.test.tsx (lines 34-277) to mock fetch/URL.createObjectURL, assert headers and blob handling, and updated the related snapshot (frontend/src/__tests__/__snapshots__/NightMotion.test.tsx.snap) to match the new render while ensuring the <img> appears once active.

251102_frontend-nightmotion_stream_reader_mjpeg
Goal: Extend previous secure fetch implementation (251101_frontend-nightmotion_secure_stream_fetch) to correctly display continuous MJPEG streams using a streaming reader instead of blob conversion.

Context:
The current NightMotion component successfully authenticates and opens the MJPEG stream through fetch with Mosaic JWT + CSRF headers, but uses await res.blob(), which never resolves because multipart/x-mixed-replace responses are continuous. The frontend stays in “Starting…” while the connection remains pending. The fix is to replace blob-based loading with a streaming reader that decodes incoming JPEG frames as they arrive and updates the display dynamically.

DONE
- Replaced the one-shot blob handling with a streaming MJPEG parser in frontend/src/components/NightMotion.tsx (lines 192-386). The component now reads chunks via ReadableStreamDefaultReader, parses multipart boundaries via Content-Length, emits each JPEG frame through URL.createObjectURL, and upgrades status from Starting → Active as soon as frames arrive. Abort logic now cancels in-flight reads, revokes prior object URLs, and keeps status/error transitions coherent.
- Added lightweight auth accessors (getAccessToken, getCsrfToken) in frontend/src/services/authService.js (lines 160-167) so the stream fetch can attach JWT and CSRF headers without query parameters.
- Reworked the NightMotion tests (frontend/src/__tests__/NightMotion.test.tsx (lines 1-315) + updated snapshot) to simulate multipart streams with a mock reader, assert header propagation, and verify cleanup (URL revocation, idle transitions).

Stream is playing now