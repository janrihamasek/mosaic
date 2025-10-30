import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  fetchEntries,
  deleteEntry as deleteEntryApi,
  addEntry as addEntryApi,
  fetchToday as fetchTodayApi,
  finalizeDay as finalizeDayApi,
  fetchProgressStats,
  importEntriesCsv,
} from '../api';

const DEFAULT_FILTERS = {
  startDate: null,
  endDate: null,
  activity: 'all',
  category: 'all',
};

const initialTodayDate = toLocalDateString(new Date());

const initialState = {
  items: [],
  filters: { ...DEFAULT_FILTERS },
  status: 'idle',
  deletingId: null,
  error: null,
  importStatus: 'idle',
  today: {
    date: initialTodayDate,
    rows: [],
    status: 'idle',
    error: null,
    dirty: {},
    savingStatus: 'idle',
    saveError: null,
  },
  stats: {
    data: [],
    status: 'idle',
    error: null,
    options: {
      group: 'activity',
      period: 30,
      date: null,
    },
    range: {
      start: null,
      end: null,
    },
  },
  finalizeStatus: 'idle',
};

function toLocalDateString(dateObj) {
  const tzOffset = dateObj.getTimezoneOffset();
  const adjusted = new Date(dateObj.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
}

function normalizeFilters(filters = {}) {
  return {
    startDate: filters.startDate ?? null,
    endDate: filters.endDate ?? null,
    activity: filters.activity ?? 'all',
    category: filters.category ?? 'all',
  };
}

function serialiseError(error) {
  if (!error) return null;
  return {
    code: error.code,
    message: error.message,
    friendlyMessage: error.friendlyMessage,
    details: error.details,
  };
}

function normalizeTodayRows(list) {
  return sortRows(
    list.map((row) => {
      const goalValue = Number(row.goal ?? row.activity_goal ?? 0) || 0;
      return {
        ...row,
        category: row.category ?? '',
        value: row.value ?? 0,
        note: row.note ?? '',
        goal: goalValue,
      };
    })
  );
}

function sortRows(list) {
  return [...list].sort((a, b) => {
    const aDone = Number(a.value) > 0 ? 1 : 0;
    const bDone = Number(b.value) > 0 ? 1 : 0;
    if (aDone !== bDone) {
      return aDone - bDone;
    }
    const catCompare = (a.category || '').localeCompare(b.category || '', undefined, {
      sensitivity: 'base',
    });
    if (catCompare !== 0) {
      return catCompare;
    }
    return (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
  });
}

export const loadEntries = createAsyncThunk(
  'entries/loadEntries',
  async (filters, { getState, rejectWithValue }) => {
    const state = getState();
    const effectiveFilters = normalizeFilters(filters ?? state.entries.filters);
    try {
      const items = await fetchEntries(effectiveFilters);
      return { filters: effectiveFilters, items };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const loadStats = createAsyncThunk(
  'entries/loadStats',
  async (options, { getState, rejectWithValue }) => {
    const state = getState();
    const current = state.entries.stats.options;
    const effective = {
      group: options?.group ?? current.group,
      period: options?.period ?? current.period,
      date: options?.date ?? current.date ?? null,
    };
    try {
      const payload = await fetchProgressStats({
        group: effective.group,
        period: effective.period,
        date: effective.date || undefined,
      });
      return {
        data: payload?.data || [],
        options: effective,
        range: {
          start: payload?.start_date ?? null,
          end: payload?.end_date ?? null,
        },
      };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const loadToday = createAsyncThunk(
  'entries/loadToday',
  async (date, { getState, rejectWithValue }) => {
    const state = getState();
    const currentDate = state.entries.today.date || initialTodayDate;
    const effectiveDate = date || currentDate;
    try {
      const data = await fetchTodayApi(effectiveDate);
      return {
        date: effectiveDate,
        rows: normalizeTodayRows(data || []),
      };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const saveDirtyTodayRows = createAsyncThunk(
  'entries/saveDirtyTodayRows',
  async (_, { getState, rejectWithValue, dispatch }) => {
    const state = getState();
    const { today, filters, stats } = state.entries;
    const entriesToSave = Object.values(today.dirty || {});
    if (!entriesToSave.length) {
      return { saved: 0, date: today.date };
    }
    try {
      await Promise.all(
        entriesToSave.map((row) =>
          addEntryApi({
            date: today.date,
            activity: row.name,
            value: Number(row.value) || 0,
            note: row.note || '',
          })
        )
      );
      dispatch(loadToday(today.date));
      dispatch(loadEntries(filters));
      dispatch(loadStats(stats.options));
      return { saved: entriesToSave.length, date: today.date };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const deleteEntry = createAsyncThunk(
  'entries/deleteEntry',
  async (id, { rejectWithValue, dispatch, getState }) => {
    try {
      await deleteEntryApi(id);
      const state = getState();
      dispatch(loadStats(state.entries.stats.options));
      dispatch(loadToday(state.entries.today.date));
      return id;
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const importEntries = createAsyncThunk(
  'entries/importEntries',
  async (file, { getState, dispatch, rejectWithValue }) => {
    try {
      const response = await importEntriesCsv(file);
      const state = getState();
      dispatch(loadEntries(state.entries.filters));
      dispatch(loadStats(state.entries.stats.options));
      dispatch(loadToday(state.entries.today.date));
      return response;
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

export const finalizeToday = createAsyncThunk(
  'entries/finalizeToday',
  async (date, { rejectWithValue }) => {
    try {
      await finalizeDayApi(date);
      return { date };
    } catch (error) {
      return rejectWithValue(serialiseError(error));
    }
  }
);

const entriesSlice = createSlice({
  name: 'entries',
  initialState,
  reducers: {
    setTodayDate(state, action) {
      state.today.date = action.payload;
    },
    updateTodayRow(state, action) {
      const { name, changes } = action.payload || {};
      if (!name) return;
      const currentRows = state.today.rows || [];
      const index = currentRows.findIndex((row) => row.name === name);
      if (index === -1) return;
      const updatedRow = { ...currentRows[index], ...changes };
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
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadEntries.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(loadEntries.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.items = action.payload.items;
        state.filters = action.payload.filters;
        state.error = null;
      })
      .addCase(loadEntries.rejected, (state, action) => {
        state.status = 'failed';
        state.items = [];
        state.error = action.payload || serialiseError(action.error);
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
        state.error = action.payload || serialiseError(action.error);
      })
      .addCase(loadToday.pending, (state, action) => {
        state.today.status = 'loading';
        state.today.error = null;
        if (action.meta.arg) {
          state.today.date = action.meta.arg;
        }
      })
      .addCase(loadToday.fulfilled, (state, action) => {
        state.today.status = 'succeeded';
        state.today.date = action.payload.date;
        state.today.rows = action.payload.rows;
        state.today.dirty = {};
        state.today.error = null;
        state.today.saveError = null;
      })
      .addCase(loadToday.rejected, (state, action) => {
        state.today.status = 'failed';
        state.today.rows = [];
        state.today.dirty = {};
        state.today.error = action.payload || serialiseError(action.error);
      })
      .addCase(saveDirtyTodayRows.pending, (state) => {
        state.today.savingStatus = 'loading';
        state.today.saveError = null;
      })
      .addCase(saveDirtyTodayRows.fulfilled, (state) => {
        state.today.savingStatus = 'succeeded';
        state.today.dirty = {};
        state.today.saveError = null;
      })
      .addCase(saveDirtyTodayRows.rejected, (state, action) => {
        state.today.savingStatus = 'failed';
        state.today.saveError = action.payload || serialiseError(action.error);
      })
      .addCase(importEntries.pending, (state) => {
        state.importStatus = 'loading';
        state.error = null;
      })
      .addCase(importEntries.fulfilled, (state) => {
        state.importStatus = 'succeeded';
      })
      .addCase(importEntries.rejected, (state, action) => {
        state.importStatus = 'failed';
        state.error = action.payload || serialiseError(action.error);
      })
      .addCase(loadStats.pending, (state) => {
        state.stats.status = 'loading';
        state.stats.error = null;
      })
      .addCase(loadStats.fulfilled, (state, action) => {
        state.stats.status = 'succeeded';
        state.stats.data = action.payload.data;
        state.stats.options = action.payload.options;
        state.stats.range = action.payload.range;
        state.stats.error = null;
      })
      .addCase(loadStats.rejected, (state, action) => {
        state.stats.status = 'failed';
        state.stats.data = [];
        state.stats.error = action.payload || serialiseError(action.error);
      })
      .addCase(finalizeToday.pending, (state) => {
        state.finalizeStatus = 'loading';
      })
      .addCase(finalizeToday.fulfilled, (state) => {
        state.finalizeStatus = 'succeeded';
      })
      .addCase(finalizeToday.rejected, (state, action) => {
        state.finalizeStatus = 'failed';
        state.today.error = state.today.error || action.payload || serialiseError(action.error);
      });
  },
});

export const { setTodayDate, updateTodayRow, clearTodayDirty, clearEntriesError } = entriesSlice.actions;

export const selectEntriesState = (state) => state.entries;
export const selectEntriesList = (state) => state.entries.items;
export const selectEntriesFilters = (state) => state.entries.filters;
export const selectTodayState = (state) => state.entries.today;
export const selectStatsState = (state) => state.entries.stats;

export default entriesSlice.reducer;
