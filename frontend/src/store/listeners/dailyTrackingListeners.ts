/**
 * Daily Tracking Listeners Middleware
 * 
 * Centralized orchestration for data refreshes after mutations.
 * Replaces hard-coded cascading dispatches in individual thunks.
 * 
 * Architecture:
 * - Listens to mutation events from services/mutations/events
 * - Dispatches appropriate load actions based on mutation type
 * - Decouples mutation logic from refresh orchestration
 * 
 * Benefits:
 * - Single source of truth for refresh logic
 * - Easy to trace which mutations trigger which refreshes
 * - Testable in isolation
 * - Aligned with T9 roadmap architecture
 */

import type { Middleware } from "@reduxjs/toolkit";
import type { AppDispatch, RootState } from "../index";
import { onAnyMutation, type MutationEvent } from "../../services/mutations/events";

// Import thunks that need to be dispatched
import { 
  loadToday, 
  loadEntries, 
  loadStats,
} from "../entriesSlice";
import { loadActivities } from "../activitiesSlice";

/**
 * Extract date from mutation event payload
 */
function extractDate(event: MutationEvent): string | null {
  const payload = event.payload;
  
  if (!payload || typeof payload !== "object") {
    return null;
  }
  
  // Direct date property
  if ("date" in payload && typeof payload.date === "string") {
    return payload.date;
  }
  
  // Nested in entry object
  if ("entry" in payload) {
    const entry = payload.entry as any;
    if (entry && typeof entry === "object" && "date" in entry && typeof entry.date === "string") {
      return entry.date;
    }
  }
  
  return null;
}

/**
 * Handles entry mutations (create, update, delete, finalize)
 * Marks data as stale instead of immediately reloading
 */
async function handleEntryMutation(
  event: MutationEvent,
  dispatch: AppDispatch,
  getState: () => RootState
): Promise<void> {
  const state = getState();
  const eventDate = extractDate(event);
  const todayDate = state.entries.today.date;
  const statsDate = state.entries.stats.date;
  const filters = state.entries.filters;

  // Always refresh stats and entries
  dispatch(loadStats({ date: statsDate }));
  dispatch(loadEntries(filters));

  // Refresh Today only if mutation affects the current day
  if (eventDate && todayDate && eventDate === todayDate) {
    dispatch(loadToday(todayDate));
  }
}

/**
 * Handles activity mutations (create, update, activate, deactivate, delete)
 * Marks data as stale instead of immediately reloading
 */
async function handleActivityMutation(
  event: MutationEvent,
  dispatch: AppDispatch,
  getState: () => RootState
): Promise<void> {
  const state = getState();
  const todayDate =
    state.entries.today.date ||
    new Date(new Date().getTime() - new Date().getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
  const statsDate = state.entries.stats.date;
  const filters = state.entries.filters;

  dispatch(loadActivities());
  dispatch(loadToday(todayDate));
  dispatch(loadEntries(filters));
  dispatch(loadStats({ date: statsDate || todayDate }));
}

/**
 * Main mutation event handler
 * Routes events to appropriate handlers based on resource type
 */
async function handleMutationEvent(
  event: MutationEvent,
  dispatch: AppDispatch,
  getState: () => RootState
): Promise<void> {
  const { type } = event;

  // Route to appropriate handler based on mutation type
  if (type.startsWith("entry.")) {
    await handleEntryMutation(event, dispatch, getState);
  } else if (type.startsWith("activity.")) {
    await handleActivityMutation(event, dispatch, getState);
  }
}

/**
 * Redux middleware that subscribes to mutation events
 * and orchestrates data refreshes
 */
export const dailyTrackingListenersMiddleware: Middleware = 
  (storeAPI) => {
    // Subscribe to all mutation events when middleware is initialized
    // Note: We don't unsubscribe because the middleware lives for the lifetime of the store
    onAnyMutation((event) => {
      handleMutationEvent(
        event,
        storeAPI.dispatch as AppDispatch,
        storeAPI.getState
      ).catch((error) => {
        console.error("Error handling mutation event:", event.type, error);
      });
    });

    return (next) => (action) => {
      return next(action);
    };
  };

/**
 * Export handler functions for testing
 */
export const testExports = {
  handleEntryMutation,
  handleActivityMutation,
  handleMutationEvent,
  extractDate,
};
