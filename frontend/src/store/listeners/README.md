# Listener Middleware Architecture

## Overview

The listener middleware replaces hard-coded cascading dispatches with a centralized, event-driven approach to data synchronization. This aligns with the T9 roadmap architecture and provides a foundation for future improvements.

## Architecture

```
Mutation Thunks
    ↓ (emit event)
Mutation Event Emitter
    ↓ (notify)
Daily Tracking Listeners Middleware
    ↓ (dispatch)
Load Thunks (loadToday, loadEntries, loadStats, loadActivities)
```

### Key Components

1. **Mutation Services** (`services/mutations/`)
   - `entries.ts`: Entry mutation operations (create, update, delete, finalize)
   - `activities.ts`: Activity mutation operations (create, update, activate, deactivate, delete)
   - `events.ts`: Event emitter singleton and type definitions

2. **Listeners Middleware** (`store/listeners/`)
   - `dailyTrackingListeners.ts`: Central orchestration for refresh logic
   - Subscribes to all mutation events
   - Routes events to appropriate handlers
   - Dispatches refresh actions based on mutation type

3. **Redux Slices** (`store/`)
   - `entriesSlice.ts`: Entry state management
   - `activitiesSlice.ts`: Activity state management
   - Thunks emit events after successful mutations
   - No longer contain hard-coded refresh cascades

## Event Flow

### Entry Mutations

```javascript
// User saves entry
saveDirtyTodayRows() 
  → entriesMutations.createOrUpdateEntry()
  → emitMutationCompleted("entry.created", payload)
  → dailyTrackingListeners hears event
  → dispatch(loadStats())
  → dispatch(loadToday()) // if date matches
  → dispatch(loadEntries())
```

### Activity Mutations

```javascript
// User creates activity
createActivity()
  → activitiesMutations.createActivity()
  → emitMutationCompleted("activity.created", payload)
  → dailyTrackingListeners hears event
  → dispatch(loadActivities())
  → dispatch(loadToday())
  → dispatch(loadEntries())
```

## Mutation Types

### Entry Events
- `entry.created`: New entry added
- `entry.updated`: Existing entry modified
- `entry.deleted`: Entry removed
- `entry.finalized`: Day finalized

### Activity Events
- `activity.created`: New activity added
- `activity.updated`: Activity details changed
- `activity.activated`: Activity reactivated
- `activity.deactivated`: Activity deactivated
- `activity.deleted`: Activity removed

## Refresh Logic

### Entry Mutations
- **Always**: `loadStats()` (stats depend on all entries)
- **Conditional**: `loadToday(date)` (only if mutation affects today's date)
- **Always**: `loadEntries(filters)` (table needs to stay in sync)

### Activity Mutations
- **Always**: `loadActivities()` (affects activity lists)
- **Always**: `loadToday(date)` (affects available rows)
- **Always**: `loadEntries(filters)` (affects display and filtering)

## Benefits

### 1. Centralized Orchestration
- All refresh logic in one place (`dailyTrackingListeners.ts`)
- Easy to understand which mutations trigger which refreshes
- No need to hunt through multiple files to trace refresh cascades

### 2. Decoupled Architecture
- Mutation thunks don't need to know about refresh logic
- Listeners can be added/removed without modifying thunks
- Multiple listeners can respond to the same event

### 3. Testability
- Handlers can be tested in isolation
- Mock dispatch to verify correct refreshes
- No need to test entire thunk chains

### 4. Maintainability
- Single source of truth for refresh rules
- Easy to add new mutation types
- Clear separation of concerns

### 5. Extensibility
- Foundation for optimistic updates
- Can add retry logic
- Can add debouncing/throttling
- Can add cross-tab synchronization

## Testing

Tests are located in `store/listeners/dailyTrackingListeners.test.ts`.

### Test Coverage
- ✅ Date extraction from events
- ✅ Entry mutation handling
- ✅ Activity mutation handling
- ✅ Event routing
- ✅ Integration scenarios

### Running Tests
```bash
npm test -- --testPathPattern=dailyTrackingListeners
```

## Migration Notes

### Before (Hard-coded Cascades)
```typescript
export const deleteEntry = createAsyncThunk(
  "entries/deleteEntry",
  async (id, { dispatch, getState }) => {
    await deleteEntryApi(id);
    
    // Hard-coded refreshes
    const state = getState();
    dispatch(loadStats({ date: state.entries.stats.date }));
    dispatch(loadToday(state.entries.today.date));
    
    return id;
  }
);
```

### After (Event-driven)
```typescript
export const deleteEntry = createAsyncThunk(
  "entries/deleteEntry",
  async (id) => {
    const result = await entriesMutations.deleteEntry(id);
    
    if (!result.success) {
      throw result.error;
    }
    
    // Emit event - listeners handle refreshes
    emitMutationCompleted("entry.deleted", { id });
    
    return id;
  }
);
```

## Future Improvements

### Phase 1: Optimistic Updates
- Update local state immediately
- Emit event with `optimistic: true` flag
- Revert on error

### Phase 2: Smart Refreshes
- Track dependencies (which views depend on which data)
- Only refresh affected views
- Batch multiple refreshes

### Phase 3: Offline Resilience
- Queue events when offline
- Replay on reconnect
- Conflict resolution

### Phase 4: Cross-tab Sync
- Broadcast events to other tabs via BroadcastChannel
- Keep all tabs in sync
- Handle race conditions

## Temporary Fallbacks

### Offline Queue
- Still using `submitOfflineMutation()` for offline support
- Will be replaced by proper offline event queue in future

### Import Operations
- `importEntries()` doesn't emit events (bulk operation)
- Manual refreshes remain for now
- Future: emit batch events or single "entries.imported" event

## Performance Considerations

### Debouncing
- Not currently implemented
- Future: debounce multiple mutations within short time window
- Prevents excessive refreshes

### Selective Updates
- Currently refreshes entire datasets
- Future: partial updates based on affected data
- Use event metadata to determine scope

## Troubleshooting

### Refreshes Not Happening
1. Check event is being emitted in thunk
2. Verify listener middleware is registered in store
3. Check console for listener errors
4. Verify mutation type matches expected format

### Too Many Refreshes
1. Check for duplicate event emissions
2. Verify listener isn't registered multiple times
3. Check for cascading mutations triggering events

### State Not Updating
1. Verify thunk actually succeeds before emitting event
2. Check load thunks are working correctly
3. Verify Redux DevTools shows dispatches

## Related Documentation

- [Mutation Services](../services/mutations/README.md) (to be created)
- [Redux Architecture](./REDUX.md) (to be updated)
- [T9 Roadmap](../../docs/ROADMAP.md) (to be created)
