import { createAsyncThunk, createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import {
  fetchActivities,
  addActivity as addActivityApi,
  updateActivity as updateActivityApi,
  activateActivity as activateActivityApi,
  deactivateActivity as deactivateActivityApi,
  deleteActivity as deleteActivityApi,
} from "../api";
import { loadEntries, loadToday } from "./entriesSlice";
import type { RootState, AppDispatch } from "./index";
import type { ActivitiesState, FriendlyError } from "../types/store";
import type { Activity } from "../types/api";

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
    return { active: (active || []) as Activity[], all: (all || []) as Activity[] };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const createActivity = createAsyncThunk<
  { ok: boolean },
  ActivityMutationPayload,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("activities/createActivity", async (payload, { dispatch, rejectWithValue, getState }) => {
  try {
    await addActivityApi(payload);
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
    await updateActivityApi(id, payload);
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
    await activateActivityApi(id);
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
    await deactivateActivityApi(id);
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
    await deleteActivityApi(id);
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

export const { selectActivity, clearActivitiesError } = activitiesSlice.actions;

export const selectActivitiesState = (state: RootState) => state.activities;
export const selectAllActivities = (state: RootState) => state.activities.all;
export const selectActiveActivities = (state: RootState) => state.activities.active;
export const selectSelectedActivityId = (state: RootState) => state.activities.selectedActivityId;

export default activitiesSlice.reducer;
