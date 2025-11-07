import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

import { fetchHealth, fetchMetrics } from "../api";

const buildInitialSectionState = () => ({
  status: "idle",
  error: null,
  data: null,
  lastFetched: null,
});

const initialState = {
  health: buildInitialSectionState(),
  metrics: buildInitialSectionState(),
};

const resolveErrorMessage = (action, fallback) =>
  action?.error?.message || fallback || "Request failed";

export const loadHealth = createAsyncThunk("admin/loadHealth", async () => {
  const response = await fetchHealth();
  return response;
});

export const loadMetrics = createAsyncThunk("admin/loadMetrics", async () => {
  const response = await fetchMetrics();
  return response;
});

const adminSlice = createSlice({
  name: "admin",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(loadHealth.pending, (state) => {
        state.health.status = "loading";
        state.health.error = null;
      })
      .addCase(loadHealth.fulfilled, (state, action) => {
        state.health.status = "succeeded";
        state.health.data = action.payload;
        state.health.lastFetched = Date.now();
        state.health.error = null;
      })
      .addCase(loadHealth.rejected, (state, action) => {
        state.health.status = "failed";
        state.health.error = resolveErrorMessage(action, "Failed to load health data");
      })
      .addCase(loadMetrics.pending, (state) => {
        state.metrics.status = "loading";
        state.metrics.error = null;
      })
      .addCase(loadMetrics.fulfilled, (state, action) => {
        state.metrics.status = "succeeded";
        state.metrics.data = action.payload;
        state.metrics.lastFetched = Date.now();
        state.metrics.error = null;
      })
      .addCase(loadMetrics.rejected, (state, action) => {
        state.metrics.status = "failed";
        state.metrics.error = resolveErrorMessage(action, "Failed to load metrics");
      });
  },
});

export const selectHealthState = (state) => state.admin.health;
export const selectMetricsState = (state) => state.admin.metrics;

export default adminSlice.reducer;
