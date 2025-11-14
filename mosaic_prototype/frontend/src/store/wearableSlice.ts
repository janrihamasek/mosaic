import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchWearableDay as fetchWearableDayApi, fetchWearableTrends as fetchWearableTrendsApi } from "../api";

type FetchStatus = "idle" | "loading" | "succeeded" | "failed";

export const fetchWearableDay = createAsyncThunk("wearable/fetchDay", async () => {
  return await fetchWearableDayApi();
});

export const fetchWearableTrends = createAsyncThunk(
  "wearable/fetchTrends",
  async (params: { metric: string; window: number }) => {
    return await fetchWearableTrendsApi(params);
  }
);

type WearableState = {
  day: Record<string, unknown> | null;
  trends: Record<string, any>;
  status: FetchStatus;
  error: string | null;
};

const initialState: WearableState = {
  day: null,
  trends: {},
  status: "idle",
  error: null,
};

const trendKey = (metric: string, window: number) => `${metric}:${window}`;

const wearableSlice = createSlice({
  name: "wearable",
  initialState,
  reducers: {
    resetWearableState(state) {
      state.day = null;
      state.trends = {};
      state.status = "idle";
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWearableDay.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchWearableDay.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.day = action.payload;
      })
      .addCase(fetchWearableDay.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Unable to load wearable day data";
      })
      .addCase(fetchWearableTrends.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchWearableTrends.fulfilled, (state, action) => {
        state.status = "succeeded";
        const payload = action.payload as { metric: string; window: number };
        const key = trendKey(payload.metric, payload.window);
        state.trends[key] = payload;
      })
      .addCase(fetchWearableTrends.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Unable to load wearable trends";
      });
  },
});

export const { resetWearableState } = wearableSlice.actions;

export default wearableSlice.reducer;

export const selectWearableDay = (state: { wearable: WearableState }) => state.wearable.day;
export const selectWearableTrend = (state: { wearable: WearableState }, metric: string, window: number) =>
  state.wearable.trends[trendKey(metric, window)] as {
    metric: string;
    window: number;
    values: Array<{ date: string; value: number | null }>;
    average?: number | null;
  } | null;
export const selectWearableStatus = (state: { wearable: WearableState }) => state.wearable.status;
export const selectWearableError = (state: { wearable: WearableState }) => state.wearable.error;
