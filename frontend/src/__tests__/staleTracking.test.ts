import { configureStore } from "@reduxjs/toolkit";
import entriesReducer, {
  markEntriesStale,
  markTodayStale,
  markStatsStale,
  markAllStale,
  loadEntries,
  loadToday,
  loadStats,
} from "../store/entriesSlice";

describe("Stale tracking in entriesSlice", () => {
  let store;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        entries: entriesReducer,
      },
    });
  });

  it("marks entries as stale", () => {
    const initialState = store.getState().entries;
    expect(initialState.stale).toBe(true); // Initial state

    store.dispatch(markEntriesStale());
    const state = store.getState().entries;
    
    expect(state.stale).toBe(true);
  });

  it("marks today as stale", () => {
    store.dispatch(markTodayStale());
    const state = store.getState().entries.today;
    
    expect(state.stale).toBe(true);
  });

  it("marks stats as stale", () => {
    store.dispatch(markStatsStale());
    const state = store.getState().entries.stats;
    
    expect(state.stale).toBe(true);
  });

  it("marks all as stale", () => {
    store.dispatch(markAllStale());
    const entriesState = store.getState().entries;
    
    expect(entriesState.stale).toBe(true);
    expect(entriesState.today.stale).toBe(true);
    expect(entriesState.stats.stale).toBe(true);
  });

  it("sets lastFetchTime on successful load", () => {
    const beforeTime = Date.now();
    
    store.dispatch(loadEntries.fulfilled(
      { 
        filters: { 
          startDate: "2024-01-01", 
          endDate: "2024-01-01",
          activity: "all",
          category: "all"
        }, 
        items: [] 
      },
      "requestId",
      { startDate: "2024-01-01", endDate: "2024-01-01" }
    ));
    
    const state = store.getState().entries;
    const afterTime = Date.now();
    
    expect(state.lastFetchTime).toBeGreaterThanOrEqual(beforeTime);
    expect(state.lastFetchTime).toBeLessThanOrEqual(afterTime);
    expect(state.stale).toBe(false);
  });

  it("sets stale to false on successful today load", () => {
    store.dispatch(loadToday.fulfilled(
      { date: "2024-01-01", rows: [] },
      "requestId",
      "2024-01-01"
    ));
    
    const state = store.getState().entries.today;
    
    expect(state.stale).toBe(false);
    expect(state.lastFetchTime).toBeTruthy();
  });

  it("sets stale to false on successful stats load", () => {
    store.dispatch(loadStats.fulfilled(
      { 
        snapshot: null, 
        date: "2024-01-01"
      },
      "requestId",
      { date: "2024-01-01" }
    ));
    
    const state = store.getState().entries.stats;
    
    expect(state.stale).toBe(false);
    expect(state.lastFetchTime).toBeTruthy();
  });
});
