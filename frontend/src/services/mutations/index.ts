/**
 * Mutation Services Index
 * 
 * Central export point for all mutation services and events.
 */

// Entries mutations
export {
  createOrUpdateEntry,
  deleteEntry,
  finalizeDay,
  batchCreateOrUpdateEntries,
  type EntryPayload,
  type EntryMutationResult,
} from "./entries";

// Activities mutations
export {
  createActivity,
  updateActivity,
  activateActivity,
  deactivateActivity,
  deleteActivity,
  type ActivityPayload,
  type ActivityUpdatePayload,
  type ActivityMutationResult,
} from "./activities";

// Mutation events
export {
  mutationEvents,
  emitMutationCompleted,
  onMutationCompleted,
  onAnyMutation,
  type MutationType,
  type MutationEvent,
  type MutationListener,
} from "./events";
