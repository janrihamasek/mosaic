import { createAsyncThunk, createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import { fetchActivities } from "../api";
import { loadEntries, loadToday } from "./entriesSlice";
import type { RootState, AppDispatch } from "./index";
import type { ActivitiesState, FriendlyError } from "../types/store";
import type { Activity } from "../types/api";
import { submitOfflineMutation } from "../offline/queue";
import { readActivitiesSnapshot, saveActivitiesSnapshot } from "../offline/snapshots";

type ActivityMutationPayload = Record<string, unknown>;

const initialState: ActivitiesState = {
  all: [],
  active: [],
  status: "idle",
  error: null,
  mutationStatus: "idle",
  mutationError: null,
  selectedActivityId: null,
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
    const payload = { active: (active || []) as Activity[], all: (all || []) as Activity[] };
    await saveActivitiesSnapshot(payload.active, payload.all);
    return payload;
  } catch (error) {
    const cached = await readActivitiesSnapshot();
    if (cached) {
      return cached;
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
        };
        const nextAll = [...lists.all.filter((item) => item.name !== activity.name), activity];
        const nextActive = activity.active === false ? lists.active : [...lists.active, activity];
        return { active: nextActive, all: nextAll };
      });
    }
    dispatch(loadActivities());
    dispatch(loadToday(undefined));
    dispatch(loadEntries(getState().entries.filters));
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
    dispatch(loadActivities());
    dispatch(loadToday(undefined));
    dispatch(loadEntries(getState().entries.filters));
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
    dispatch(loadActivities());
    dispatch(loadToday(undefined));
    dispatch(loadEntries(getState().entries.filters));
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
    dispatch(loadActivities());
    dispatch(loadToday(undefined));
    dispatch(loadEntries(getState().entries.filters));
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
    dispatch(loadActivities());
    dispatch(loadToday(undefined));
    dispatch(loadEntries(getState().entries.filters));
    return { id };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

const mutationThunks = [createActivity, updateActivityDetails, activateActivity, deactivateActivity, removeActivity];

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

export const { selectActivity, clearActivitiesError, setActivitiesFromSnapshot } = activitiesSlice.actions;

export const selectActivitiesState = (state: RootState) => state.activities;
export const selectAllActivities = (state: RootState) => state.activities.all;
export const selectActiveActivities = (state: RootState) => state.activities.active;
export const selectSelectedActivityId = (state: RootState) => state.activities.selectedActivityId;

export default activitiesSlice.reducer;
