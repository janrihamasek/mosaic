# Activities Page Specification

## Identification
- Route: `/` with tab `Activities` inside `Dashboard`
- Primary components: `ActivityForm.jsx`, `ActivityTable.jsx`, optional modal `ActivityDetail.jsx`
- Redux slice: `activitiesSlice`
- Supporting slices: `entriesSlice` (refreshes Today/Entries after mutations)
- API endpoints: `/activities`, `/add_activity`, `/activities/:id`, `/activities/:id/(activate|deactivate)`, `/activities/:id` (DELETE)

## Purpose
- Manage catalogue of trackable activities (create, edit metadata, toggle activation, delete)
- Surface active/inactive state, goal targets, and quick actions for operations staff/users
- Provide drill-in editing without leaving context via inline modal

## Layout
- Component hierarchy
  - `Dashboard` ➜ `ActivityForm` | `ActivityDetail?` | `ActivityTable`
    - `ActivityForm`
      - `FormWrapper` shell with stacked inputs for name/category/description plus an `activity_type` selector (`positive` or `negative`). Goal-frequency selectors only render when `activity_type === 'positive'`.
    - `ActivityDetail`
      - `ModalForm` overlay with editable frequency/category/description
    - `ActivityTable`
      - `DataTable` listing with action buttons column
- Layout sequencing: form renders first (creation), table follows; modal overlays when `selectActivity` sets ID
- Responsive behaviour: `FormWrapper` adapts via `useCompactLayout`; action cells flex-wrap for narrow widths

## Interactive Elements
- Create form uses `react-hook-form`
  - Validates min/max lengths, frequency ranges before dispatching `createActivity`
  - Selecting `Negative` hides goal inputs, pins cadence to 1×1, and dispatches `goal: 0`
  - Submit button disabled until `isValid`; label changes to `Saving...`
- Table row interactions
  - Activity name acts as detail trigger (calls `onOpenDetail`, dispatches `selectActivity`)
  - `Activate`/`Deactivate` buttons dispatch respective thunks; disabled while mutation in flight for that row
  - `Delete` removes activity; button shows `Working...` when busy
- Detail modal (`ActivityDetail`)
  - Save on modal close if fields changed; runs `updateActivityDetails`
  - Offers “Not Save” button to discard changes when dirty
  - Validates frequency ranges client-side before dispatch
- Toast notifications delivered via `onNotify` from parent `Dashboard`

## Data Bindings
- `selectActivitiesState` exposes `{ status, error, mutationStatus, mutationError, selectedActivityId }`
  - `status === 'loading'` drives table-level `Loading` banner
  - `error` triggers `ErrorState` with `loadActivities` retry
- `selectAllActivities` populates table rows; entries sorted active-first then by category/name
  - Columns bind to `activity.name`, `activity.category`, `activity.goal` (formatted), `activity.activity_type`, `activity.active`
  - Action column uses `activity.id` for dispatch and disabled states
- `ActivityForm` dispatches `createActivity` payload matching backend schema (frequency fields in snake_case)
- `ActivityDetail` initialises state from selected activity; on submit calls `updateActivityDetails`
- All mutation thunks refresh `loadActivities`, `loadToday`, `loadEntries` to propagate catalogue changes across tabs

## Styles
- Reuses `styles.input`, `styles.button`, `styles.card`, etc. from `styles/common.js`
- `DataTable` provides consistent table typography, hover, empty state styling
- Action buttons recolor via inline overrides (`#29442f` activate, `#8b1e3f` destructive) for quick affordance
- Modal inherits `ModalForm` base with overlay dimming and stacked layout

## Notes
- Backend computes `goal` from frequency inputs; client intentionally omits sending `goal` on create unless the user selects a negative activity, in which case it forces `goal: 0`
- Negative activities always render with a red row tint and automatically keep their cadence at 1×1; positive activities keep the historic green tint
- Table currently lacks pagination; rely on backend default until dataset grows—consider virtualisation if counts spike
- `mutationStatus` can be used to surface global error banner in future (currently only toasts)
- When deleting an activity that is selected in modal, reducer clears `selectedActivityId` to close detail safely
- Ensure internationalisation/localisation if field labels change from English/Czech mix
