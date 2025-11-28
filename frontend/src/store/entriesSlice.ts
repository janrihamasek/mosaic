import { createAsyncThunk, createSelector, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
  fetchEntries,
  deleteEntry as deleteEntryApi,
  fetchToday as fetchTodayApi,
  finalizeDay as finalizeDayApi,
  fetchProgressStats,
  importEntriesCsv,
} from "../api";
import { submitOfflineMutation } from "../offline/queue";
import { readTodaySnapshot, saveTodaySnapshot } from "../offline/snapshots";
import * as entriesMutations from "../services/mutations/entries";
import { emitMutationCompleted } from "../services/mutations/events";
import type { RootState, AppDispatch } from "./index";
import type {
  EntriesFilters,
  EntriesState,
  FriendlyError,
  TodayRow,
} from "../types/store";
import type { ActivityType, Entry, StatsSnapshot } from "../types/api";

type FiltersInput = Partial<EntriesFilters> | undefined;

const DEFAULT_FILTERS: EntriesFilters = {
  startDate: null,
  endDate: null,
  activity: "all",
  category: "all",
};

const initialTodayDate = toLocalDateString(new Date());

const initialState: EntriesState = {
  items: [],
  filters: { ...DEFAULT_FILTERS },
  status: "idle",
  deletingId: null,
  error: null,
  importStatus: "idle",
  lastFetchTime: null,
  stale: true,
  today: {
    date: initialTodayDate,
    rows: [],
    status: "idle",
    error: null,
    dirty: {},
    savingStatus: "idle",
    saveError: null,
    lastFetchTime: null,
    stale: true,
  },
  stats: {
    snapshot: null,
    status: "idle",
    error: null,
    date: null,
    lastFetchTime: null,
    stale: true,
  },
  finalizeStatus: "idle",
};

function toLocalDateString(dateObj: Date): string {
  const tzOffset = dateObj.getTimezoneOffset();
  const adjusted = new Date(dateObj.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
}

function normalizeFilters(filters: FiltersInput = {}): EntriesFilters {
  return {
    startDate: filters?.startDate ?? null,
    endDate: filters?.endDate ?? null,
    activity: filters?.activity ?? "all",
    category: filters?.category ?? "all",
  };
}

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

const toActivityType = (value: unknown): ActivityType =>
  value === "negative" ? "negative" : "positive";

type TodayRowInput = Partial<TodayRow> & {
  activity_goal?: number;
  name: string;
  activity_type?: string;
};

function normalizeTodayRows(list: TodayRowInput[]): TodayRow[] {
  return sortRows(
    list.map((row) => {
      const goalValue = Number(row.goal ?? row.activity_goal ?? 0) || 0;
      return {
        ...row,
        category: row.category ?? "",
        value: Number(row.value ?? 0),
        note: row.note ?? "",
        goal: goalValue,
        activity_type: toActivityType(row.activity_type),
      } as TodayRow;
    })
  );
}

function sortRows(list: TodayRow[]): TodayRow[] {
  return [...list].sort((a, b) => {
    const aDone = Number(a.value) > 0 ? 1 : 0;
    const bDone = Number(b.value) > 0 ? 1 : 0;
    if (aDone !== bDone) {
      return aDone - bDone;
    }
    const catCompare = (a.category || "").localeCompare(b.category || "", undefined, {
      sensitivity: "base",
    });
    if (catCompare !== 0) {
      return catCompare;
    }
    return (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" });
  });
}

const normaliseReject = (error: unknown): FriendlyError => serialiseError(error) ?? {};

export const loadEntries = createAsyncThunk<
  { filters: EntriesFilters; items: Entry[] },
  FiltersInput,
  { state: RootState; rejectValue: FriendlyError }
>("entries/loadEntries", async (filters, { getState, rejectWithValue }) => {
  const state = getState();
  const effectiveFilters = normalizeFilters(filters ?? state.entries.filters);
  try {
    const items = (await fetchEntries(effectiveFilters)) as Entry[];
    const normalizedItems = (items || []).map((entry) => ({
      ...entry,
      activity_type: toActivityType(entry.activity_type),
    }));
    return { filters: effectiveFilters, items: normalizedItems };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const loadStats = createAsyncThunk<
  { snapshot: StatsSnapshot | null; date: string | null },
  { date?: string | null } | undefined,
  { state: RootState; rejectValue: FriendlyError }
>("entries/loadStats", async (options, { getState, rejectWithValue }) => {
  const state = getState();
  const currentDate = state.entries.stats.date;
  const effectiveDate = options?.date ?? currentDate ?? null;
  try {
    const snapshot = (await fetchProgressStats({
      date: effectiveDate || undefined,
    })) as StatsSnapshot | null;
    return {
      snapshot: snapshot || null,
      date: effectiveDate,
    };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const loadToday = createAsyncThunk<
  { date: string; rows: TodayRow[] },
  string | undefined,
  { state: RootState; rejectValue: FriendlyError }
>("entries/loadToday", async (date, { getState, rejectWithValue }) => {
  const state = getState();
  const currentDate = state.entries.today.date || initialTodayDate;
  const effectiveDate = date || currentDate;
  try {
    const data = (await fetchTodayApi(effectiveDate)) as TodayRowInput[] | null;
    const rows = normalizeTodayRows(data || []);
    await saveTodaySnapshot(effectiveDate, rows);
    return {
      date: effectiveDate,
      rows,
    };
  } catch (error) {
    const cachedRows = await readTodaySnapshot(effectiveDate);
    if (cachedRows) {
      return {
        date: effectiveDate,
        rows: normalizeTodayRows(cachedRows),
      };
    }
    return rejectWithValue(normaliseReject(error));
  }
});

export const saveDirtyTodayRows = createAsyncThunk<
  { saved: number; date: string },
  void,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("entries/saveDirtyTodayRows", async (_, { getState, rejectWithValue, dispatch }) => {
  const state = getState();
  const { today, filters, stats } = state.entries;
  const entriesToSave = Object.values(today.dirty || {});
  if (!entriesToSave.length) {
    return { saved: 0, date: today.date };
  }
  try {
    // Use mutation service for batch create/update
    const entryPayloads = entriesToSave.map((row) => ({
      date: today.date,
      activity: row.name,
      value: Number(row.value) || 0,
      note: row.note || "",
    }));

    // Still use offline queue for offline support (temporary fallback)
    for (const payload of entryPayloads) {
      await submitOfflineMutation({
        action: "add_entry",
        endpoint: "/add_entry",
        method: "POST",
        payload,
      });
    }

    // Save snapshot
    await saveTodaySnapshot(today.date, today.rows);

    // Emit mutation event for each entry
    entryPayloads.forEach((payload) => {
      emitMutationCompleted("entry.created", payload, {
        source: "saveDirtyTodayRows",
      });
    });
    
    return { saved: entriesToSave.length, date: today.date };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const deleteEntry = createAsyncThunk<
  number,
  number,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("entries/deleteEntry", async (id, { rejectWithValue, dispatch, getState }) => {
  try {
    // Use mutation service
    const result = await entriesMutations.deleteEntry(id);
    
    if (!result.success) {
      throw result.error || new Error("Failed to delete entry");
    }

    // Emit mutation event
    emitMutationCompleted("entry.deleted", { id }, {
      source: "deleteEntry",
    });
    
    return id;
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const importEntries = createAsyncThunk<
  unknown,
  File,
  { state: RootState; dispatch: AppDispatch; rejectValue: FriendlyError }
>("entries/importEntries", async (file, { getState, dispatch, rejectWithValue }) => {
  try {
    const response = await importEntriesCsv(file);
    // Note: Import is a bulk operation that doesn't emit individual mutation events
    // We manually refresh here because emitting events for each entry would be inefficient
    const state = getState();
    dispatch(loadEntries(state.entries.filters));
    dispatch(loadStats({ date: state.entries.stats.date }));
    dispatch(loadToday(state.entries.today.date));
    return response;
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

export const finalizeToday = createAsyncThunk<
  { date: string },
  string,
  { rejectValue: FriendlyError }
>("entries/finalizeToday", async (date, { rejectWithValue }) => {
  try {
    // Use mutation service
    const result = await entriesMutations.finalizeDay(date);
    
    if (!result.success) {
      throw result.error || new Error("Failed to finalize day");
    }

    // Emit mutation event
    emitMutationCompleted("entry.finalized", { date }, {
      source: "finalizeToday",
    });

    return { date };
  } catch (error) {
    return rejectWithValue(normaliseReject(error));
  }
});

const entriesSlice = createSlice({
  name: "entries",
  initialState,
  reducers: {
    setTodayDate(state, action: PayloadAction<string>) {
      state.today.date = action.payload;
    },
    updateTodayRow(state, action: PayloadAction<{ name: string; changes: Partial<TodayRow> }>) {
      const { name, changes } = action.payload || {};
      if (!name) return;
      const currentRows = state.today.rows || [];
      const index = currentRows.findIndex((row) => row.name === name);
      if (index === -1) return;
      const updatedRow: TodayRow = { ...currentRows[index], ...changes };
      const nextRows = [...currentRows];
      nextRows[index] = updatedRow;
      state.today.rows = sortRows(nextRows);
      state.today.dirty = {
        ...state.today.dirty,
        [name]: {
          ...updatedRow,
        },
      };
    },
    clearTodayDirty(state) {
      state.today.dirty = {};
    },
    clearEntriesError(state) {
      state.error = null;
      state.today.error = null;
      state.today.saveError = null;
      state.stats.error = null;
    },
    markEntriesStale(state) {
      state.stale = true;
    },
    markTodayStale(state) {
      state.today.stale = true;
    },
    markStatsStale(state) {
      state.stats.stale = true;
    },
    markAllStale(state) {
      state.stale = true;
      state.today.stale = true;
      state.stats.stale = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadEntries.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(loadEntries.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.items = action.payload.items;
        state.filters = action.payload.filters;
        state.error = null;
        state.lastFetchTime = Date.now();
        state.stale = false;
      })
      .addCase(loadEntries.rejected, (state, action) => {
        state.status = "failed";
        state.items = [];
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(deleteEntry.pending, (state, action) => {
        state.deletingId = action.meta.arg;
        state.error = null;
      })
      .addCase(deleteEntry.fulfilled, (state, action) => {
        state.deletingId = null;
        state.items = state.items.filter((entry) => entry.id !== action.payload);
      })
      .addCase(deleteEntry.rejected, (state, action) => {
        state.deletingId = null;
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(loadToday.pending, (state, action) => {
        state.today.status = "loading";
        state.today.error = null;
        if (action.meta.arg) {
          state.today.date = action.meta.arg;
        }
      })
      .addCase(loadToday.fulfilled, (state, action) => {
        state.today.status = "succeeded";
        state.today.date = action.payload.date;
        state.today.rows = action.payload.rows;
        state.today.dirty = {};
        state.today.error = null;
        state.today.saveError = null;
        state.today.lastFetchTime = Date.now();
        state.today.stale = false;
      })
      .addCase(loadToday.rejected, (state, action) => {
        state.today.status = "failed";
        state.today.rows = [];
        state.today.dirty = {};
        state.today.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(saveDirtyTodayRows.pending, (state) => {
        state.today.savingStatus = "loading";
        state.today.saveError = null;
      })
      .addCase(saveDirtyTodayRows.fulfilled, (state) => {
        state.today.savingStatus = "succeeded";
        state.today.dirty = {};
        state.today.saveError = null;
      })
      .addCase(saveDirtyTodayRows.rejected, (state, action) => {
        state.today.savingStatus = "failed";
        state.today.saveError = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(importEntries.pending, (state) => {
        state.importStatus = "loading";
        state.error = null;
      })
      .addCase(importEntries.fulfilled, (state) => {
        state.importStatus = "succeeded";
      })
      .addCase(importEntries.rejected, (state, action) => {
        state.importStatus = "failed";
        state.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(loadStats.pending, (state) => {
        state.stats.status = "loading";
        state.stats.error = null;
      })
      .addCase(loadStats.fulfilled, (state, action) => {
        state.stats.status = "succeeded";
        state.stats.snapshot = action.payload.snapshot;
        state.stats.date = action.payload.date ?? null;
        state.stats.error = null;
        state.stats.lastFetchTime = Date.now();
        state.stats.stale = false;
      })
      .addCase(loadStats.rejected, (state, action) => {
        state.stats.status = "failed";
        state.stats.snapshot = null;
        state.stats.error = action.payload ?? serialiseError(action.error) ?? null;
      })
      .addCase(finalizeToday.pending, (state) => {
        state.finalizeStatus = "loading";
      })
      .addCase(finalizeToday.fulfilled, (state) => {
        state.finalizeStatus = "succeeded";
      })
      .addCase(finalizeToday.rejected, (state, action) => {
        state.finalizeStatus = "failed";
        state.today.error = state.today.error || action.payload || serialiseError(action.error) || null;
      });
  },
});

export const { 
  setTodayDate, 
  updateTodayRow, 
  clearTodayDirty, 
  clearEntriesError,
  markEntriesStale,
  markTodayStale,
  markStatsStale,
  markAllStale,
} = entriesSlice.actions;

// ===============================
// Base selectors
// ===============================
export const selectEntriesState = (state: RootState) => state.entries;
export const selectEntriesList = (state: RootState) => state.entries.items;
export const selectEntriesFilters = (state: RootState) => state.entries.filters;
export const selectTodayState = (state: RootState) => state.entries.today;
export const selectStatsState = (state: RootState) => state.entries.stats;

// ===============================
// Memoized derived selectors
// ===============================

/**
 * Select today's date
 */
export const selectTodayDate = createSelector(
  [selectTodayState],
  (today) => today.date
);

/**
 * Select today's rows (activities + entries for the day)
 */
export const selectTodayRows = createSelector(
  [selectTodayState],
  (today) => today.rows
);

/**
 * Select dirty (unsaved) today rows
 */
export const selectDirtyTodayRows = createSelector(
  [selectTodayState],
  (today) => today.dirty
);

/**
 * Select count of dirty today rows
 */
export const selectDirtyTodayCount = createSelector(
  [selectDirtyTodayRows],
  (dirty) => Object.keys(dirty).length
);

/**
 * Check if there are any unsaved changes in today
 */
export const selectHasDirtyToday = createSelector(
  [selectDirtyTodayCount],
  (count) => count > 0
);

/**
 * Select today's loading status
 */
export const selectTodayStatus = createSelector(
  [selectTodayState],
  (today) => today.status
);

/**
 * Select today's saving status
 */
export const selectTodaySavingStatus = createSelector(
  [selectTodayState],
  (today) => today.savingStatus
);

/**
 * Select if today is loading
 */
export const selectIsTodayLoading = createSelector(
  [selectTodayStatus],
  (status) => status === "loading"
);

/**
 * Select if today is saving
 */
export const selectIsTodaySaving = createSelector(
  [selectTodaySavingStatus],
  (status) => status === "loading"
);

/**
 * Select today's error
 */
export const selectTodayError = createSelector(
  [selectTodayState],
  (today) => today.error
);

/**
 * Select stats snapshot
 */
export const selectStatsSnapshot = createSelector(
  [selectStatsState],
  (stats) => stats.snapshot
);

/**
 * Select stats date
 */
export const selectStatsDate = createSelector(
  [selectStatsState],
  (stats) => stats.date
);

/**
 * Select stats status
 */
export const selectStatsStatus = createSelector(
  [selectStatsState],
  (stats) => stats.status
);

/**
 * Select if stats are loading
 */
export const selectIsStatsLoading = createSelector(
  [selectStatsStatus],
  (status) => status === "loading"
);

/**
 * Select stats error
 */
export const selectStatsError = createSelector(
  [selectStatsState],
  (stats) => stats.error
);

/**
 * Select entries status
 */
export const selectEntriesStatus = createSelector(
  [selectEntriesState],
  (entries) => entries.status
);

/**
 * Select if entries are loading
 */
export const selectIsEntriesLoading = createSelector(
  [selectEntriesStatus],
  (status) => status === "loading"
);

/**
 * Select entry being deleted (ID)
 */
export const selectDeletingEntryId = createSelector(
  [selectEntriesState],
  (entries) => entries.deletingId
);

/**
 * Select entries error
 */
export const selectEntriesError = createSelector(
  [selectEntriesState],
  (entries) => entries.error
);

/**
 * Select import status
 */
export const selectImportStatus = createSelector(
  [selectEntriesState],
  (entries) => entries.importStatus
);

/**
 * Select if import is in progress
 */
export const selectIsImporting = createSelector(
  [selectImportStatus],
  (status) => status === "loading"
);

/**
 * Select finalize status
 */
export const selectFinalizeStatus = createSelector(
  [selectEntriesState],
  (entries) => entries.finalizeStatus
);

/**
 * Select if finalize is in progress
 */
export const selectIsFinalizing = createSelector(
  [selectFinalizeStatus],
  (status) => status === "loading"
);

// ===============================
// Complex derived selectors
// ===============================

/**
 * Compute today's progress statistics from rows
 */
export const selectTodayProgress = createSelector(
  [selectTodayRows],
  (rows) => {
    return rows.reduce(
      (acc, row) => {
        const value = Number(row.value) || 0;
        const goal = Number(row.goal) || 0;
        
        // Skip negative activities for progress calculation
        if (row.activity_type === "negative") {
          return acc;
        }
        
        if (goal > 0) {
          acc.total += goal;
          acc.completed += Math.min(value, goal);
          acc.goalCount += 1;
          if (value >= goal) {
            acc.metCount += 1;
          }
        }
        
        return acc;
      },
      { total: 0, completed: 0, goalCount: 0, metCount: 0 }
    );
  }
);

/**
 * Compute today's completion percentage
 */
export const selectTodayCompletionPercent = createSelector(
  [selectTodayProgress],
  (progress) => {
    if (progress.total === 0) return 0;
    return (progress.completed / progress.total) * 100;
  }
);

/**
 * Count of activities with goals met today
 */
export const selectTodayGoalsMetCount = createSelector(
  [selectTodayProgress],
  (progress) => progress.metCount
);

/**
 * Count of activities with goals defined today
 */
export const selectTodayGoalsCount = createSelector(
  [selectTodayProgress],
  (progress) => progress.goalCount
);

export default entriesSlice.reducer;
