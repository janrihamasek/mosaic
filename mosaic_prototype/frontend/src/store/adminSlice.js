import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

import {
  fetchActivityLogs,
  fetchHealth,
  fetchMetrics,
  fetchRuntimeLogs,
  fetchWearableRaw,
  fetchWearableSummary,
} from "../api";

const buildInitialSectionState = () => ({
  status: "idle",
  error: null,
  data: null,
  lastFetched: null,
});

const initialState = {
  health: buildInitialSectionState(),
  metrics: buildInitialSectionState(),
  activityLogs: buildInitialSectionState(),
  runtimeLogs: buildInitialSectionState(),
  wearableInspector: {
    status: "idle",
    error: null,
    summary: null,
    raw: [],
    lastFetched: null,
  },
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

export const loadActivityLogs = createAsyncThunk(
  "admin/loadActivityLogs",
  async (params = {}) => {
    const response = await fetchActivityLogs(params);
    return response;
  }
);

export const loadRuntimeLogs = createAsyncThunk(
  "admin/loadRuntimeLogs",
  async (params = {}) => {
    const response = await fetchRuntimeLogs(params);
    return response;
  }
);

export const loadWearableSummary = createAsyncThunk(
  "admin/loadWearableSummary",
  async (params = {}) => {
    const [summary, raw] = await Promise.all([fetchWearableSummary(params), fetchWearableRaw(params)]);
    return { summary, raw };
  }
);

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
      })
      .addCase(loadActivityLogs.pending, (state) => {
        state.activityLogs.status = "loading";
        state.activityLogs.error = null;
      })
      .addCase(loadActivityLogs.fulfilled, (state, action) => {
        state.activityLogs.status = "succeeded";
        state.activityLogs.data = action.payload;
        state.activityLogs.lastFetched = Date.now();
        state.activityLogs.error = null;
      })
      .addCase(loadActivityLogs.rejected, (state, action) => {
        state.activityLogs.status = "failed";
        state.activityLogs.error = resolveErrorMessage(action, "Failed to load activity logs");
      })
      .addCase(loadRuntimeLogs.pending, (state) => {
        state.runtimeLogs.status = "loading";
        state.runtimeLogs.error = null;
      })
      .addCase(loadRuntimeLogs.fulfilled, (state, action) => {
        state.runtimeLogs.status = "succeeded";
        state.runtimeLogs.data = action.payload;
        state.runtimeLogs.lastFetched = Date.now();
        state.runtimeLogs.error = null;
      })
      .addCase(loadRuntimeLogs.rejected, (state, action) => {
        state.runtimeLogs.status = "failed";
        state.runtimeLogs.error = resolveErrorMessage(action, "Failed to load runtime logs");
      })
      .addCase(loadWearableSummary.pending, (state) => {
        state.wearableInspector.status = "loading";
        state.wearableInspector.error = null;
      })
      .addCase(loadWearableSummary.fulfilled, (state, action) => {
        state.wearableInspector.status = "succeeded";
        state.wearableInspector.summary = action.payload.summary;
        state.wearableInspector.raw = action.payload.raw;
        state.wearableInspector.lastFetched = Date.now();
        state.wearableInspector.error = null;
      })
      .addCase(loadWearableSummary.rejected, (state, action) => {
        state.wearableInspector.status = "failed";
        state.wearableInspector.error = resolveErrorMessage(action, "Failed to load wearable summary");
      });
  },
});

export const selectHealthState = (state) => state.admin.health;
export const selectMetricsState = (state) => state.admin.metrics;
export const selectActivityLogsState = (state) => state.admin.activityLogs;
export const selectRuntimeLogsState = (state) => state.admin.runtimeLogs;
export const selectWearableInspectorState = (state) => state.admin.wearableInspector;

export default adminSlice.reducer;
