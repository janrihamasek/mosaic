import { createAsyncThunk, createSlice, isAnyOf } from '@reduxjs/toolkit';
import {
  fetchActivities,
  addActivity as addActivityApi,
  updateActivity as updateActivityApi,
  activateActivity as activateActivityApi,
  deactivateActivity as deactivateActivityApi,
  deleteActivity as deleteActivityApi,
} from '../api';
import { loadEntries, loadToday } from './entriesSlice';

const initialState = {
  all: [],
  active: [],
  status: 'idle',
  error: null,
  mutationStatus: 'idle',
  mutationError: null,
  selectedActivityId: null,
};

function serialiseError(error) {
  if (!error) return null;
  return {
    code: error.code,
    message: error.message,
    friendlyMessage: error.friendlyMessage,
    details: error.details,
  };
}

export const loadActivities = createAsyncThunk(
  'activities/loadActivities',
  async (_, { rejectWithValue }) => {
    try {
      const [active, all] = await Promise.all([
        fetchActivities({ all: false }),
        fetchActivities({ all: true }),
      ]);
      return { active, all };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const createActivity = createAsyncThunk(
  'activities/createActivity',
  async (payload, { dispatch, rejectWithValue, getState }) => {
    try {
      await addActivityApi(payload);
      dispatch(loadActivities());
      dispatch(loadToday());
      dispatch(loadEntries(getState().entries.filters));
      return { ok: true };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const updateActivityDetails = createAsyncThunk(
  'activities/updateActivityDetails',
  async ({ id, payload }, { dispatch, rejectWithValue, getState }) => {
    try {
      await updateActivityApi(id, payload);
      dispatch(loadActivities());
      dispatch(loadToday());
      dispatch(loadEntries(getState().entries.filters));
      return { id };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const activateActivity = createAsyncThunk(
  'activities/activateActivity',
  async (id, { dispatch, rejectWithValue, getState }) => {
    try {
      await activateActivityApi(id);
      dispatch(loadActivities());
      dispatch(loadToday());
      dispatch(loadEntries(getState().entries.filters));
      return { id };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const deactivateActivity = createAsyncThunk(
  'activities/deactivateActivity',
  async (id, { dispatch, rejectWithValue, getState }) => {
    try {
      await deactivateActivityApi(id);
      dispatch(loadActivities());
      dispatch(loadToday());
      dispatch(loadEntries(getState().entries.filters));
      return { id };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const removeActivity = createAsyncThunk(
  'activities/removeActivity',
  async (id, { dispatch, rejectWithValue, getState }) => {
    try {
      await deleteActivityApi(id);
      dispatch(loadActivities());
      dispatch(loadToday());
      dispatch(loadEntries(getState().entries.filters));
      return { id };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

const mutationThunks = [
  createActivity,
  updateActivityDetails,
  activateActivity,
  deactivateActivity,
  removeActivity,
];

const activitiesSlice = createSlice({
  name: 'activities',
  initialState,
  reducers: {
    selectActivity(state, action) {
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
        state.status = 'loading';
        state.error = null;
      })
      .addCase(loadActivities.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.active = action.payload.active || [];
        state.all = action.payload.all || [];
        state.error = null;
      })
      .addCase(loadActivities.rejected, (state, action) => {
        state.status = 'failed';
        state.active = [];
        state.all = [];
        state.error = action.payload || serialiseError(action.error);
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
          state.mutationStatus = 'loading';
          state.mutationError = null;
        }
      )
      .addMatcher(
        isAnyOf(...mutationThunks.map((thunk) => thunk.fulfilled)),
        (state) => {
          state.mutationStatus = 'succeeded';
        }
      )
      .addMatcher(
        isAnyOf(...mutationThunks.map((thunk) => thunk.rejected)),
        (state, action) => {
          state.mutationStatus = 'failed';
          state.mutationError = action.payload || serialiseError(action.error);
        }
      );
  },
});

export const { selectActivity, clearActivitiesError } = activitiesSlice.actions;

export const selectActivitiesState = (state) => state.activities;
export const selectAllActivities = (state) => state.activities.all;
export const selectActiveActivities = (state) => state.activities.active;
export const selectSelectedActivityId = (state) => state.activities.selectedActivityId;

export default activitiesSlice.reducer;
