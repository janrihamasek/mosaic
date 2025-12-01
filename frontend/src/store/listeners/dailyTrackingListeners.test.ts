/**
 * Tests for Daily Tracking Listeners Middleware
 * 
 * Verifies that mutation events trigger the correct data refreshes
 */

import { testExports } from "./dailyTrackingListeners";
import type { MutationEvent } from "../../services/mutations/events";
import type { AppDispatch, RootState } from "../index";

const { handleEntryMutation, handleActivityMutation, handleMutationEvent, extractDate } = testExports;

// Mock dispatch and getState
const createMockDispatch = (): { dispatch: AppDispatch; calls: any[] } => {
  const calls: any[] = [];
  const dispatch = jest.fn((thunk: any) => {
    // Thunks are functions that receive dispatch and getState
    // For testing purposes, we just track what was dispatched
    // In real Redux, thunks return promises
    calls.push(thunk);
    // Return a resolved promise to match async thunk behavior
    return Promise.resolve({ type: thunk.type || 'unknown', payload: {} });
  }) as unknown as AppDispatch;
  return { dispatch, calls };
};

const createMockGetState = (overrides?: Partial<RootState>): (() => RootState) => {
  return () => ({
    entries: {
      items: [],
      filters: {
        startDate: "2025-01-01",
        endDate: "2025-01-31",
        activity: "all",
        category: "all",
      },
      status: "idle",
      deletingId: null,
      error: null,
      importStatus: "idle",
      today: {
        date: "2025-01-15",
        rows: [],
        status: "idle",
        error: null,
        dirty: {},
        savingStatus: "idle",
        saveError: null,
      },
      stats: {
        date: "2025-01-15",
        snapshot: null,
        status: "idle",
        error: null,
      },
    },
    activities: {
      active: [],
      all: [],
      status: "idle",
      error: null,
    },
    auth: {
      user: null,
      token: null,
      status: "idle",
      error: null,
    },
    nightMotion: {
      dates: [],
      data: {},
      status: "idle",
      error: null,
    },
    backup: {
      status: "idle",
      error: null,
      lastBackup: null,
    },
    admin: {
      users: [],
      stats: null,
      status: "idle",
      error: null,
    },
    offline: {
      isOffline: false,
      queue: [],
      syncStatus: "idle",
    },
    wearable: {
      devices: [],
      data: [],
      status: "idle",
      error: null,
    },
    ...overrides,
  } as RootState);
};

describe("dailyTrackingListeners", () => {
  describe("extractDate", () => {
    it("should extract date from direct payload", () => {
      const event: MutationEvent = {
        type: "entry.created",
        payload: { date: "2025-01-15" },
        timestamp: Date.now(),
      };
      expect(extractDate(event)).toBe("2025-01-15");
    });

    it("should extract date from nested entry object", () => {
      const event: MutationEvent = {
        type: "entry.updated",
        payload: { entry: { date: "2025-01-20" } },
        timestamp: Date.now(),
      };
      expect(extractDate(event)).toBe("2025-01-20");
    });

    it("should return null for payload without date", () => {
      const event: MutationEvent = {
        type: "entry.deleted",
        payload: { id: 123 },
        timestamp: Date.now(),
      };
      expect(extractDate(event)).toBeNull();
    });

    it("should return null for null payload", () => {
      const event: MutationEvent = {
        type: "entry.created",
        payload: null,
        timestamp: Date.now(),
      };
      expect(extractDate(event)).toBeNull();
    });
  });

  describe("handleEntryMutation", () => {
    it("should dispatch loadStats, loadToday, and loadEntries for entry affecting today", async () => {
      const { dispatch, calls } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "entry.created",
        payload: { date: "2025-01-15" }, // matches today.date
        timestamp: Date.now(),
      };

      await handleEntryMutation(event, dispatch, getState);

      // Should dispatch 3 actions: loadStats, loadToday, loadEntries
      expect(dispatch).toHaveBeenCalledTimes(3);
      expect(calls).toHaveLength(3);
    });

    it("should dispatch loadStats and loadEntries (but not loadToday) for entry not affecting today", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "entry.created",
        payload: { date: "2025-01-10" }, // does not match today.date (2025-01-15)
        timestamp: Date.now(),
      };

      await handleEntryMutation(event, dispatch, getState);

      // Should dispatch 2 actions: loadStats, loadEntries (no loadToday since date doesn't match)
      expect(dispatch).toHaveBeenCalledTimes(2);
    });

    it("should dispatch refreshes for entry.deleted", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "entry.deleted",
        payload: { id: 123 },
        timestamp: Date.now(),
      };

      await handleEntryMutation(event, dispatch, getState);

      // Should dispatch 2 actions: loadStats, loadEntries (no date, so no loadToday)
      expect(dispatch).toHaveBeenCalledTimes(2);
    });

    it("should dispatch refreshes for entry.finalized", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "entry.finalized",
        payload: { date: "2025-01-15" },
        timestamp: Date.now(),
      };

      await handleEntryMutation(event, dispatch, getState);

      // Should dispatch 3 actions: loadStats, loadToday, loadEntries
      expect(dispatch).toHaveBeenCalledTimes(3);
    });
  });

  describe("handleActivityMutation", () => {
    it("should dispatch loadActivities, loadToday, loadEntries, and loadStats for activity.created", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.created",
        payload: { name: "New Activity" },
        timestamp: Date.now(),
      };

      await handleActivityMutation(event, dispatch, getState);

      // Should dispatch 4 actions: loadActivities, loadToday, loadEntries, loadStats
      expect(dispatch).toHaveBeenCalledTimes(4);
    });

    it("should dispatch refreshes for activity.updated", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.updated",
        payload: { id: 1, name: "Updated Activity" },
        timestamp: Date.now(),
      };

      await handleActivityMutation(event, dispatch, getState);

      // Should dispatch 4 actions: loadActivities, loadToday, loadEntries, loadStats
      expect(dispatch).toHaveBeenCalledTimes(4);
    });

    it("should dispatch refreshes for activity.activated", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.activated",
        payload: { id: 1 },
        timestamp: Date.now(),
      };

      await handleActivityMutation(event, dispatch, getState);

      // Should dispatch 4 actions: loadActivities, loadToday, loadEntries, loadStats
      expect(dispatch).toHaveBeenCalledTimes(4);
    });

    it("should dispatch refreshes for activity.deactivated", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.deactivated",
        payload: { id: 1 },
        timestamp: Date.now(),
      };

      await handleActivityMutation(event, dispatch, getState);

      // Should dispatch 4 actions: loadActivities, loadToday, loadEntries, loadStats
      expect(dispatch).toHaveBeenCalledTimes(4);
    });

    it("should dispatch refreshes for activity.deleted", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.deleted",
        payload: { id: 1 },
        timestamp: Date.now(),
      };

      await handleActivityMutation(event, dispatch, getState);

      // Should dispatch 4 actions: loadActivities, loadToday, loadEntries, loadStats
      expect(dispatch).toHaveBeenCalledTimes(4);
    });
  });

  describe("handleMutationEvent", () => {
    it("should route entry events to handleEntryMutation", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "entry.created",
        payload: { date: "2025-01-15" },
        timestamp: Date.now(),
      };

      await handleMutationEvent(event, dispatch, getState);

      // Should dispatch entry-related refreshes (loadStats, loadToday, loadEntries)
      expect(dispatch).toHaveBeenCalled();
      expect(dispatch).toHaveBeenCalledTimes(3);
    });

    it("should route activity events to handleActivityMutation", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "activity.created",
        payload: { name: "Test" },
        timestamp: Date.now(),
      };

      await handleMutationEvent(event, dispatch, getState);

      // Should dispatch activity-related refreshes (loadActivities, loadToday, loadEntries, loadStats)
      expect(dispatch).toHaveBeenCalled();
      expect(dispatch).toHaveBeenCalledTimes(4);
    });

    it("should handle unknown event types gracefully", async () => {
      const { dispatch, calls } = createMockDispatch();
      const getState = createMockGetState();
      const event: MutationEvent = {
        type: "unknown.type" as any,
        payload: {},
        timestamp: Date.now(),
      };

      await handleMutationEvent(event, dispatch, getState);

      // Should not dispatch anything for unknown types
      expect(calls).toHaveLength(0);
    });
  });

  describe("integration scenarios", () => {
    it("should handle multiple entry mutations correctly", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const dispatchMock = dispatch as jest.Mock;

      // Create entry
      await handleEntryMutation(
        {
          type: "entry.created",
          payload: { date: "2025-01-15" },
          timestamp: Date.now(),
        },
        dispatch,
        getState
      );

      const firstCallCount = dispatchMock.mock.calls.length;

      // Update entry
      await handleEntryMutation(
        {
          type: "entry.updated",
          payload: { id: 1, date: "2025-01-15" },
          timestamp: Date.now(),
        },
        dispatch,
        getState
      );

      const secondCallCount = dispatchMock.mock.calls.length;

      // Delete entry
      await handleEntryMutation(
        {
          type: "entry.deleted",
          payload: { id: 1 },
          timestamp: Date.now(),
        },
        dispatch,
        getState
      );

      // Each mutation should trigger appropriate refreshes
      expect(dispatch).toHaveBeenCalled();
      // First two mutations dispatch 3 calls each (date matches today), last one dispatches 2 (no date)
      expect(firstCallCount).toBe(3);
      expect(secondCallCount - firstCallCount).toBe(3);
      expect(dispatchMock.mock.calls.length - secondCallCount).toBe(2);
    });

    it("should handle mixed entry and activity mutations", async () => {
      const { dispatch } = createMockDispatch();
      const getState = createMockGetState();
      const dispatchMock = dispatch as jest.Mock;

      // Activity mutation
      await handleActivityMutation(
        {
          type: "activity.created",
          payload: { name: "Test Activity" },
          timestamp: Date.now(),
        },
        dispatch,
        getState
      );

      const afterActivity = dispatchMock.mock.calls.length;

      // Entry mutation
      await handleEntryMutation(
        {
          type: "entry.created",
          payload: { date: "2025-01-15" },
          timestamp: Date.now(),
        },
        dispatch,
        getState
      );

      // Activity mutation should have dispatched 3 calls
      expect(afterActivity).toBe(3);
      // Entry mutation should have added 3 more calls
      expect(dispatchMock.mock.calls.length).toBe(6);
    });
  });
});
