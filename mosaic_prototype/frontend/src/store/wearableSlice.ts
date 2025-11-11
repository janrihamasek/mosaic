import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchWearableDay, fetchWearableTrends } from "../api";

export const loadWearableDay = createAsyncThunk("wearable/loadDay", async () => {
  const data = await fetchWearableDay();
  return data;
});

export const loadWearableTrends = createAsyncThunk("wearable/loadTrends", async () => {
  const data = await fetchWearableTrends();
  return data;
});

type WearableState = {
  day: Record<string, any> | null;
  trends: Record<string, any> | null;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
};

const initialState: WearableState = {
  day: null,
  trends: null,
  status: "idle",
  error: null,
};

const wearableSlice = createSlice({
  name: "wearable",
  initialState,
  reducers: {
    resetWearableState(state) {
      state.day = null;
      state.trends = null;
      state.status = "idle";
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadWearableDay.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loadWearableDay.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.day = action.payload;
      })
      .addCase(loadWearableDay.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Unable to load wearable day data";
      })
      .addCase(loadWearableTrends.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loadWearableTrends.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.trends = action.payload;
      })
      .addCase(loadWearableTrends.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Unable to load wearable trends";
      });
  },
});

export const { resetWearableState } = wearableSlice.actions;

export default wearableSlice.reducer;

export const selectWearableDay = (state: { wearable: WearableState }) => state.wearable.day;
export const selectWearableTrends = (state: { wearable: WearableState }) => state.wearable.trends;
export const selectWearableStatus = (state: { wearable: WearableState }) => state.wearable.status;
export const selectWearableError = (state: { wearable: WearableState }) => state.wearable.error;
