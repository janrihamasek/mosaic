# Daily Log – 2024-10-30

- Date: 2024-10-30
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 30_10_mosaic.md

## Notes (raw import)


1. State Management Migration

Replaced local state and AuthContext with Redux Toolkit.

- Added centralized store (src/store/index.js) and slices for auth, entries, and activities.
- Connected components to selectors and async thunks instead of local state.
- Entries slice triggers /today and /stats refresh after mutations.
- Updated src/index.jsx and App.jsx to use Redux Provider.
- All UI components now dispatch actions and read from store (Today, Stats, Entry/Activity forms and tables, Login/Register).
- CSV import now triggers cache refresh through Redux.
- Added @reduxjs/toolkit and react-redux dependencies; removed obsolete AuthContext.

DONE by Codex

Moved authentication, entries, and activities into Redux Toolkit slices and wired the UI to selectors/thunks instead of local state.

- src/store/index.js:1 introduces the centralized store, wiring auth storage updates into Redux.
- src/store/authSlice.js:1, src/store/entriesSlice.js:1, src/store/activitiesSlice.js:1 define slices with async thunks (entries slice also refreshes /today and /stats after mutations).
- src/index.jsx:1 and src/App.jsx:1 swap AuthContext for the Redux provider and rework Dashboard navigation around store data.
- src/components/{Today.jsx,Stats.jsx,EntryForm.jsx,EntryTable.jsx,ActivityForm.jsx,ActivityTable.jsx,ActivityDetail.jsx,LoginForm.jsx,RegisterForm.jsx,LogoutButton.jsx}:1 each use selectors/dispatch to keep component logic minimal while still firing user notifications.
- src/components/CsvImportButton.jsx:1 now dispatches the CSV import thunk so related caches refresh automatically.
- package.json:1 adds @reduxjs/toolkit and react-redux; removed the old context provider (src/context/AuthContext.jsx).

2. Form Validation

Goal: Add react-hook-form validation to all user-facing forms.

Instructions:
Apply react-hook-form to ActivityForm, EntryForm, and LoginForm.
Add inline validation messages and red borders for invalid inputs.
Use same validation logic as backend (string length, numeric range).
On submit, prevent sending invalid data to API.
Ensure user experience is consistent across forms.

- [x] 2.1 Integrace knihovny a základní validace
Goal: Integrate react-hook-form and apply it to LoginForm.jsx as a test case.

DONE by Codex

Integrated react-hook-form into the login flow so the form state, validation, and submit gating are all handled by the hook.

- mosaic_prototype/frontend/package.json (line 12) added the react-hook-form dependency so the hook is available in the app bundle.
- mosaic_prototype/frontend/src/components/LoginForm.jsx (line 1) refactored to initialize useForm, replace local field state, enforce trimmed required validation, surface inline error messaging with red borders, and keep the Redux login thunk dispatch in the submit handler while disabling the button until the form is valid or the request finishes.

---

- [x] 2.2 Migrace EntryForm.jsx
Goal: Apply react-hook-form validation to EntryForm.jsx.

DONE by Codex
- Replaced local state with useForm so all EntryForm fields register through react-hook-form, providing live validity tracking and submission gating (mosaic_prototype/frontend/src/components/EntryForm.jsx (lines 29-109)).
- Synced form defaults with Redux filters while re-validating dependent fields to keep /today and /stats refresh logic in step with existing filters (mosaic_prototype/frontend/src/components/EntryForm.jsx (lines 62-110)).
- Added granular validation: required rules and length limits on every control, numeric year range checks for month mode, and cross-field date-order guards for range mode, surfacing inline errors under each input (mosaic_prototype/frontend/src/components/EntryForm.jsx (lines 217-348)).
- Styled inputs to highlight invalid state and disabled the submit button until the form passes validation, while preserving the loadEntries dispatch and error handling (mosaic_prototype/frontend/src/components/EntryForm.jsx:143-194,350-359).

---

- [x] 2.3 Migrace ActivityForm.jsx
Goal: Apply react-hook-form validation to ActivityForm.jsx.

DONE by Codex

Replaced ActivityForm state with useForm, wired validation, and kept the Redux flow intact.

- mosaic_prototype/frontend/src/components/ActivityForm.jsx (lines 28-66) initializes react-hook-form, watches frequency inputs, computes the goal, and submits via the existing createActivity thunk (still trimming values and resetting after success).
- mosaic_prototype/frontend/src/components/ActivityForm.jsx (lines 73-162) registers name, category, description, and frequency fields with required/min/max/length rules, highlights invalid inputs, and renders inline error text plus the computed avg/day preview.
- mosaic_prototype/frontend/src/components/ActivityForm.jsx (lines 179-188) disables the submit button while saving, submitting, or when the form is invalid to block bad requests.

Removed the extra goal field from the create-activity payload so it matches the Flask schema.

- mosaic_prototype/frontend/src/components/ActivityForm.jsx (lines 48-62) now dispatches only the fields allowed by ActivityCreatePayload (name, category, frequency_per_day, frequency_per_week, description) and adds a brief comment noting that the backend derives goal on its own. Previously we sent goal, which Pydantic (configured with extra="forbid") rejected as “Extra inputs are not permitted,” triggering the 400 response.

---

- [x] 2.4 Migrace RegisterForm.jsx
Goal: Add react-hook-form validation to RegisterForm.jsx.

IDONE by Codex
Integrated react-hook-form into the registration flow and tightened client-side validation while keeping the backend contract intact.

- mosaic_prototype/frontend/src/components/RegisterForm.jsx (lines 25-65) wires useForm, tracks password confirmation, and submits only the username/password pair to the Redux auth thunk (email stays client-side per backend schema).
- mosaic_prototype/frontend/src/components/RegisterForm.jsx (lines 68-165) registers username, email, password, and confirmation inputs with required/length/pattern rules, surfaces inline error text, and styles invalid fields with a red border.
- mosaic_prototype/frontend/src/components/RegisterForm.jsx (lines 167-176) disables the submit button whenever the form is invalid or mid-submit so the auth registration only fires on valid data.

---

- [x] 2.5 Validace importu CSV (bonus)
Goal: Add simple validation for CSV import before dispatch.

DONE by Codex

Added lightweight client-side guards before kicking off the CSV import.

- mosaic_prototype/frontend/src/components/CsvImportButton.jsx (lines 16-66) now resets the hidden file input, checks for .csv extension and non-empty files, and short-circuits with a user notification when the selection is invalid. This keeps bad uploads from hitting the /import_csv endpoint and explains validation in a brief comment.

---

- [x] 2.6 Konsolidace a testy
Goal: Verify all react-hook-form integrations and error handling consistency.

**React Hook Form Coverage**

- mosaic_prototype/frontend/src/components/LoginForm.jsx (lines 25-114) renders inline errors for username/password, flips the input border to red, and keeps the submit button disabled while the form is invalid or mid-dispatch—the Redux login thunk still fires on valid submit.
- mosaic_prototype/frontend/src/components/RegisterForm.jsx (lines 25-176) validates trimmed username, email pattern, password length, and confirmation match, surfaces messages under each field, and only dispatches registerUser when the form passes.
- mosaic_prototype/frontend/src/components/EntryForm.jsx (lines 25-360) wraps all filters in useForm, enforces required/range/date ordering rules across modes, highlights invalid inputs, and continues to dispatch loadEntries when validation succeeds.
- mosaic_prototype/frontend/src/components/ActivityForm.jsx (lines 28-188) keeps Redux createActivity intact, but validates required strings, lengths, and frequency ranges; the button stays disabled until the form is valid and not saving.
- mosaic_prototype/frontend/src/components/CsvImportButton.jsx (lines 16-66) guards CSV uploads, showing errors (via onNotify) before dispatching importEntries.
3.
Goal: Add consistent loading and error handling to all API-driven views.

DONE by Codex

- Added reusable animated status feedback (frontend/src/components/Loading.jsx (line 1), frontend/src/components/ErrorState.jsx (line 1)) backed by a shared keyframe injector so every view gets the same fade/ spinner treatment (frontend/src/utils/animations.js (line 1)).
- Updated the activities, entries, and today screens to short-circuit into the new components, retry failed loads, and still show inline refresh hints during background fetches (frontend/src/components/ActivityTable.jsx (line 12), frontend/src/components/EntryTable.jsx (line 6), frontend/src/components/Today.jsx (line 11)).
- Hooked the axios interceptor to emit a global mosaic-api-error event for real failures and taught the dashboard notification system to listen for it, producing consistent error toasts without duplicating validation messaging (frontend/src/apiClient.js (line 40), frontend/src/App.jsx (line 44)).

4.
Goal: Make all major views responsive for mobile.

1. TASK:  

Goal: Introduce a unified responsive design system.

DONE by Codex

Added rem-based viewport constants, structured breakpoints, and reusable media query helpers to centralize responsive logic (mosaic_prototype/frontend/src/styles/common.js (lines 1-46)).  
Introduced responsiveStyles tokens for container, card, form, button, table, input, and text so each breakpoint override is defined once (mosaic_prototype/frontend/src/styles/common.js (lines 48-183)).  
Refactored the exported styles object to consume the new tokens via the helpers, keeping the dark theme values while unifying responsive variants (mosaic_prototype/frontend/src/styles/common.js (lines 185-386)).

No automated tests were run (style-only change).  
Next: 1) Spot-check key screens at mobile/tablet/desktop widths. 2) Commit with feat(styles): add responsive design tokens and media query helpers.

2. TASK:  
Goal: Apply the new responsive design system to all major views.

DONE by Codex

**Responsive Updates**

- frontend/src/utils/useBreakpoints.js (line 1) introduces normalized matchMedia helpers plus useBreakpoints/useCompactLayout so components can react to the shared token breakpoints.
- mosaic_prototype/frontend/src/Dashboard.jsx (line 1) rebuilds the dashboard shell with breakpoint-aware padding, tab, and toast behavior while keeping notification wiring and tab persistence intact.
- mosaic_prototype/frontend/src/components/Today.jsx (line 165) swaps the legacy table for card-based mobile layouts, responsive date controls, and adaptive progress/status blocks to eliminate horizontal scroll on compact screens.
- mosaic_prototype/frontend/src/components/ActivityTable.jsx (line 21), ActivityForm.jsx (line 25), EntryTable.jsx (line 15), and Stats.jsx (line 29) now consume the breakpoint hook to stack content, widen controls, and stretch buttons/selects below tablet widths.
- mosaic_prototype/frontend/src/components/Notification.jsx (line 1) aligns toast sizing with the new compact layout so alerts stay legible on handhelds.

5. Component Refactor
Goal: Extract shared UI logic into reusable components.

Introduced three shared building blocks backed by the existing dark-theme tokens:

- frontend/src/components/shared/FormWrapper.jsx (line 1) now supplies a card-style form container with optional description slot and a responsive submit/cancel action row that flips to full-width buttons on compact layouts.
- frontend/src/components/shared/DataTable.jsx (line 1) centralizes table rendering; it accepts configurable columns, loading/error/empty states, and automatically switches to stacked cards with keyboard-accessible row clicks under the compact breakpoint.
- frontend/src/components/shared/ModalForm.jsx (line 1) wraps any form in a dark-mode modal with backdrop/escape handling, scroll locking, and a responsive header/close control.

Goal: Refactor existing forms and tables to use shared components.

**Refactor Highlights**

- frontend/src/components/ActivityForm.jsx (line 78) and frontend/src/components/EntryForm.jsx (line 200) now delegate layout to FormWrapper, keeping existing validation while unifying submit controls and letting Entry import append via the wrapper’s footer.
- frontend/src/components/ActivityTable.jsx (line 63) and frontend/src/components/EntryTable.jsx (line 46) render through the new DataTable, reusing shared responsive cards/rows, preserving action handlers, and reusing the spinner by passing <Loading> as the loading message.
- frontend/src/components/ActivityDetail.jsx (line 44) wraps the editor in ModalForm, with discard/save flows intact and backdrop/Escape disabled while requests are in-flight; ModalForm (shared/ModalForm.jsx (line 7)) gained isDismissDisabled, and FormWrapper (shared/FormWrapper.jsx (line 9)) now accepts isSubmitDisabled/submitButtonProps.
- frontend/src/components/shared/DataTable.jsx (line 17) accepts React nodes for loading states so tables can show the shared spinner instead of plain text.

6. TypeScript Migration
Goal: Begin incremental migration to TypeScript.
1.
Added mosaic_prototype/frontend/tsconfig.json with the requested compiler options so CRA now picks up the TypeScript settings while keeping JS compilation enabled.
- npm start -- --smoke-test returned exit code 0 and compiled successfully; the ForkTsCheckerWebpackPlugin logs a RpcIpcMessagePortClosedError immediately after exit, which is a known side-effect of the smoke test shutting the checker down early. A normal npm start session should continue running without that message.
- npm run build completed with exit code 0 and produced the optimized bundle. The same checker emitted “Issues checking service aborted” warnings, but the build artifacts were generated successfully.
2.
Converted the Loading, ErrorState, and ModalForm components to TypeScript with explicit prop interfaces while leaving behavior untouched.
**Updates**
- Typed loading state props and wrapped the component in React.FC to keep defaults strongly typed (src/components/Loading.tsx (line 13)).
- Added an ErrorStateProps interface plus React.FC usage so retry handling is typed and optional (src/components/ErrorState.tsx (line 5)).
- Defined modal props, including optional content nodes, and typed the escape key handler while exporting a React.FC version (src/components/shared/ModalForm.tsx (line 7)).
3.
Introduced shared type declarations and wired the converted components to them so we can reuse consistent shapes across the app.
- Added Activity, Entry, and ApiError interfaces for API responses in src/types/api.d.ts (line 1).
- Centralized component prop contracts in src/types/props.d.ts (line 1), including LoadingProps, ErrorStateProps, and ModalFormProps.
- Updated Loading.tsx (line 1), ErrorState.tsx (line 1), and components/shared/ModalForm.tsx (line 1) to import those shared prop types and typed the modal overlay click handler to remove implicit any.