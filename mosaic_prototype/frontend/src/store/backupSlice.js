import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import {
  fetchBackupStatus,
  runBackup,
  toggleBackupSettings,
} from "../api";

const initialState = {
  status: "idle",
  enabled: false,
  intervalMinutes: 60,
  lastRun: null,
  backups: [],
  running: false,
  toggling: false,
  error: null,
  lastBackup: null,
};

const normalizeError = (error) => {
  if (!error) return "Unexpected error";
  if (error?.friendlyMessage) return error.friendlyMessage;
  if (error?.message) return error.message;
  return String(error);
};

export const loadBackupStatus = createAsyncThunk(
  "backup/loadStatus",
  async (_, { rejectWithValue }) => {
    try {
      return await fetchBackupStatus();
    } catch (error) {
      return rejectWithValue(normalizeError(error));
    }
  }
);

export const toggleBackup = createAsyncThunk(
  "backup/toggle",
  async ({ enabled, intervalMinutes } = {}, { rejectWithValue }) => {
    try {
      const payload = {};
      if (typeof enabled === "boolean") {
        payload.enabled = enabled;
      }
      if (typeof intervalMinutes === "number") {
        payload.interval_minutes = intervalMinutes;
      }
      const response = await toggleBackupSettings(payload);
      return response.status;
    } catch (error) {
      return rejectWithValue(normalizeError(error));
    }
  }
);

export const runBackupNow = createAsyncThunk(
  "backup/run",
  async (_, { rejectWithValue }) => {
    try {
      const result = await runBackup();
      const status = await fetchBackupStatus();
      return {
        backup: result.backup,
        status,
      };
    } catch (error) {
      return rejectWithValue(normalizeError(error));
    }
  }
);

const backupSlice = createSlice({
  name: "backup",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(loadBackupStatus.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loadBackupStatus.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.enabled = Boolean(action.payload.enabled);
        state.intervalMinutes = action.payload.interval_minutes ?? 60;
        state.lastRun = action.payload.last_run || null;
        state.backups = action.payload.backups || [];
        state.error = null;
      })
      .addCase(loadBackupStatus.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload || "Failed to load backup status";
      })
      .addCase(toggleBackup.pending, (state) => {
        state.toggling = true;
        state.error = null;
      })
      .addCase(toggleBackup.fulfilled, (state, action) => {
        state.toggling = false;
        state.enabled = Boolean(action.payload.enabled);
        state.intervalMinutes = action.payload.interval_minutes ?? state.intervalMinutes;
        state.lastRun = action.payload.last_run || null;
        state.backups = action.payload.backups || state.backups;
        state.error = null;
      })
      .addCase(toggleBackup.rejected, (state, action) => {
        state.toggling = false;
        state.error = action.payload || "Failed to update backup settings";
      })
      .addCase(runBackupNow.pending, (state) => {
        state.running = true;
        state.error = null;
      })
      .addCase(runBackupNow.fulfilled, (state, action) => {
        state.running = false;
        const { status, backup } = action.payload;
        state.enabled = Boolean(status.enabled);
        state.intervalMinutes = status.interval_minutes ?? state.intervalMinutes;
        state.lastRun = status.last_run || null;
        state.backups = status.backups || [];
        state.lastBackup = backup;
        state.error = null;
      })
      .addCase(runBackupNow.rejected, (state, action) => {
        state.running = false;
        state.error = action.payload || "Backup run failed";
      });
  },
});

export const selectBackupState = (state) => state.backup;
export const selectLatestBackup = (state) =>
  (state.backup.backups && state.backup.backups[0]) || null;

export default backupSlice.reducer;
