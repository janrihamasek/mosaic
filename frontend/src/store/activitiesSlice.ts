import { createAsyncThunk, createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import { batchActivities, fetchActivities } from "../api";
import { markEntriesStale, markStatsStale, markTodayStale } from "./entriesSlice";
import type { RootState, AppDispatch } from "./index";
import type { ActivitiesState, FriendlyError } from "../types/store";
import type { Activity, ActivityType } from "../types/api";
import { isOfflineError, submitOfflineMutation } from "../offline/queue";
import { readActivitiesSnapshot, saveActivitiesSnapshot } from "../offline/snapshots";
import { emitMutationCompleted } from "../services/mutations/events";

type ActivityMutationPayload = Record<string, unknown>;

const initialState: ActivitiesState = {
  all: [],
  active: [],
  status: "idle",
  error: null,
  mutationStatus: "idle",
  mutationError: null,
  selectedActivityId: null,
  lastFetchTime: null,
  stale: true,
};

function serialiseError(error: unknown): FriendlyError | null {
  if (!error) return null;
  const err = error as FriendlyError & { message?: string };
  return {
    code: err.code,
    message: err.message,
    friendlyMessage: err.friendlyMessage,
    details: err.details,
  };
}

const normaliseReject = (error: unknown): FriendlyError => serialiseError(error) ?? {};

type ActivityLists = {
  active: Activity[];
  all: Activity[];
};

const cloneLists = (state: ActivitiesState): ActivityLists => ({
  active: [...(state.active || [])],
  all: [...(state.all || [])],
});

const tempId = () => -Math.floor(Math.random() * 1_000_000 + Date.now());
const toActivityType = (value: unknown): ActivityType => {
  if (value === "negative") return "negative";
  if (value === "neutral") return "neutral";
  return "positive";
};

async function applyAndPersistActivitiesSnapshot(
  getState: () => RootState,
  transformer: (lists: ActivityLists) => ActivityLists
): Promise<ActivityLists> {
  const state = getState();
  const current = cloneLists(state.activities);
  const next = transformer(current);
  await saveActivitiesSnapshot(next.active, next.all);
  return next;
}

async function updateLocalActivities(
  dispatch: AppDispatch,
  getState: () => RootState,
  transformer: (lists: ActivityLists) => ActivityLists
): Promise<void> {
  const next = await applyAndPersistActivitiesSnapshot(getState, transformer);
  dispatch(setActivitiesFromSnapshot(next));
}

export const loadActivities = createAsyncThunk<
  { active: Activity[]; all: Activity[] },
  void,
  { rejectValue: FriendlyError }
>("activities/loadActivities", async (_, { rejectWithValue }) => {
  try {
    const [active, all] = await Promise.all([
      fetchActivities({ all: false }),
      fetchActivities({ all: true }),
    ]);
    const normalize = (items: Activity[] = []): Activity[] =>
      items.map((item) => ({
        ...item,
        activity_type: toActivityType(item.activity_type),
      }));
    const payload = {
      active: normalize((active || []) as Activity[]),
      all: normalize((all || []) as Activity[]),
    };
    await saveActivitiesSnapshot(payload.active, payload.all);
    return payload;
  } catch (error) {
    const cached = await readActivitiesSnapshot();
    if (cached) {
      const normalize = (items: Activity[] = []): Activity[] =>
        items.map((item) => ({
          ...item,
          activity_type: toActivityType(item.activity_type),
        }));
      return {
        active: normalize(cached.active),
        all: normalize(cached.all),
      };
    }
    return rejectWithValue(normaliseReject(error));
  }
});

export const createActivity = createAsyncThunk<
  { ok: boolean },
  ActivityMutationPayload,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/createActivity", async (payload, { dispatch, rejectWithValue, getState }) => {
  try {
    // Still use offline queue for offline support (temporary fallback)
    const result = await submitOfflineMutation({
      action: "add_activity",
      endpoint: "/add_activity",
      method: "POST",
      payload,
    });
    if (result.queued) {
      await updateLocalActivities(dispatch, getState, (lists) => {
        const activity: Activity = {
          id: tempId(),
          name: String(payload.name) || "Activity",
          category: String(payload.category ?? ""),
          goal: Number(payload.goal ?? 0),
          active: true,
          activity_type: toActivityType(payload.activity_type),
        };
        const nextAll = [...lists.all.filter((item) => item.name !== activity.name), activity];
        const nextActive = activity.active === false ? lists.active : [...lists.active, activity];
        return { active: nextActive, all: nextAll };
      });
    }

    // Emit mutation event
    emitMutationCompleted("activity.created", payload, {
      source: "createActivity",
    });
    return { ok: true };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const updateActivityDetails = createAsyncThunk<
  { id: number },
  { id: number; payload: ActivityMutationPayload },
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/updateActivityDetails", async ({ id, payload }, { dispatch, rejectWithValue, getState }) => {
  try {
    // Still use offline queue for offline support (temporary fallback)
    const result = await submitOfflineMutation({
      action: "update_activity",
      endpoint: `/activities/${id}`,
      method: "PUT",
      payload,
    });
    if (result.queued) {
      await updateLocalActivities(dispatch, getState, (lists) => {
        const mapper = (items: Activity[]) =>
          items.map((item) => (item.id === id ? { ...item, ...payload } : item));
        return { active: mapper(lists.active), all: mapper(lists.all) };
      });
    }

    // Emit mutation event
    emitMutationCompleted("activity.updated", { id, ...payload }, {
      source: "updateActivityDetails",
    });
    return { id };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const activateActivity = createAsyncThunk<
  { id: number },
  number,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/activateActivity", async (id, { dispatch, rejectWithValue, getState }) => {
  try {
    // Still use offline queue for offline support (temporary fallback)
    const result = await submitOfflineMutation({
      action: "activate_activity",
      endpoint: `/activities/${id}/activate`,
      method: "PATCH",
    });
    if (result.queued) {
      await updateLocalActivities(dispatch, getState, (lists) => {
        const mapper = (items: Activity[]) =>
          items.map((item) =>
            item.id === id ? { ...item, active: true, deactivated_at: null } : item
          );
        return { active: mapper(lists.active), all: mapper(lists.all) };
      });
    }

    // Emit mutation event
    emitMutationCompleted("activity.activated", { id }, {
      source: "activateActivity",
    });
    return { id };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const deactivateActivity = createAsyncThunk<
  { id: number },
  number,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/deactivateActivity", async (id, { dispatch, rejectWithValue, getState }) => {
  try {
    // Still use offline queue for offline support (temporary fallback)
    const result = await submitOfflineMutation({
      action: "deactivate_activity",
      endpoint: `/activities/${id}/deactivate`,
      method: "PATCH",
    });
    if (result.queued) {
      const today = new Date().toISOString().slice(0, 10);
      await updateLocalActivities(dispatch, getState, (lists) => {
        const mapper = (items: Activity[]) =>
          items.map((item) =>
            item.id === id ? { ...item, active: false, deactivated_at: today } : item
          );
        return { active: mapper(lists.active), all: mapper(lists.all) };
      });
    }

    // Emit mutation event
    emitMutationCompleted("activity.deactivated", { id }, {
      source: "deactivateActivity",
    });
    return { id };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const removeActivity = createAsyncThunk<
  { id: number },
  number,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/removeActivity", async (id, { dispatch, rejectWithValue, getState }) => {
  try {
    const result = await submitOfflineMutation({
      action: "delete_activity",
      endpoint: `/activities/${id}`,
      method: "DELETE",
    });
    if (result.queued) {
      await updateLocalActivities(dispatch, getState, (lists) => ({
        active: lists.active.filter((item) => item.id !== id),
        all: lists.all.filter((item) => item.id !== id),
      }));
    }
    
    // Emit mutation event
    emitMutationCompleted("activity.deleted", { id }, {
      source: "removeActivity",
    });
    return { id };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export type BatchAction = "activate" | "deactivate" | "delete";

export const batchUpdateActivities = createAsyncThunk<
  { processed: number[]; skipped: { id: number; reason: string }[]; action: BatchAction },
  { action: BatchAction; ids: number[] },
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/batchUpdateActivities", async ({ action, ids }, { dispatch, rejectWithValue }) => {
  try {
    let summary;
    try {
      summary = await batchActivities({ action, ids });
    } catch (error) {
      if (isOfflineError(error)) {
        await submitOfflineMutation({
          action: "activities_batch",
          endpoint: "/activities/batch",
          method: "POST",
          payload: { action, ids },
        });
        summary = { processed: [], skipped: [], queued: true };
      } else {
        throw error;
      }
    }

    // Mark slices stale so Dashboard refreshes on next tab switch/timeout
    dispatch(markActivitiesStale());
    dispatch(markTodayStale());
    dispatch(markEntriesStale());
    dispatch(markStatsStale());

    // Emit mutation event for listeners (reuse updated event)
    emitMutationCompleted("activity.updated", { action, ids }, { source: "batchUpdateActivities" });

    return {
      action,
      processed: summary?.processed || [],
      skipped: summary?.skipped || [],
    };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

const mutationThunks = [createActivity, updateActivityDetails, activateActivity, deactivateActivity, removeActivity, batchUpdateActivities];

const activitiesSlice = createSlice({
  name: "activities",
  initialState,
  reducers: {
    selectActivity(state, action: PayloadAction<number | null | undefined>) {
      state.selectedActivityId = action.payload ?? null;
    },
    clearActivitiesError(state) {
      state.error = null;
      state.mutationError = null;
    },
    setActivitiesFromSnapshot(state, action: PayloadAction<ActivityLists>) {
      state.active = action.payload.active;
      state.all = action.payload.all;
    },
    markActivitiesStale(state) {
      state.stale = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadActivities.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loadActivities.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.active = action.payload.active || [];
        state.all = action.payload.all || [];
        state.error = null;
        state.lastFetchTime = Date.now();
        state.stale = false;
      })
      .addCase(loadActivities.rejected, (state, action) => {
        state.status = "failed";
        state.active = [];
        state.all = [];
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(removeActivity.fulfilled, (state, action) => {
        const removedId = action.payload?.id;
        if (removedId && state.selectedActivityId === removedId) {
          state.selectedActivityId = null;
        }
      })
      .addMatcher(
        isAnyOf(...mutationThunks.map((thunk) => thunk.pending)),
        (state) => {
          state.mutationStatus = "loading";
          state.mutationError = null;
        }
      )
      .addMatcher(
        isAnyOf(...mutationThunks.map((thunk) => thunk.fulfilled)),
        (state) => {
          state.mutationStatus = "succeeded";
        }
      )
      .addMatcher(
        isAnyOf(...mutationThunks.map((thunk) => thunk.rejected)),
        (state, action) => {
          state.mutationStatus = "failed";
          state.mutationError = action.payload ?? serialiseError(action.error) ?? null;
        }
      );
  },
});

export const { selectActivity, clearActivitiesError, setActivitiesFromSnapshot, markActivitiesStale } = activitiesSlice.actions;

export const selectActivitiesState = (state: RootState) => state.activities;
export const selectAllActivities = (state: RootState) => state.activities.all;
export const selectActiveActivities = (state: RootState) => state.activities.active;
export const selectSelectedActivityId = (state: RootState) => state.activities.selectedActivityId;

export default activitiesSlice.reducer;
