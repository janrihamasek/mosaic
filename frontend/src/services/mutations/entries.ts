/**
 * Entries Mutation Service
 * 
 * Centralized service for all entry write operations in the daily loop.
 * Wraps API calls and provides a consistent interface for mutations.
 */

import * as api from "../../api";

export interface EntryPayload {
  date: string;
  activity: string;
  value: number;
  note?: string;
}

export interface EntryMutationResult {
  success: boolean;
  data?: any;
  error?: Error;
}

/**
 * Create or update an entry
 * Maps to POST /add_entry endpoint
 */
export async function createOrUpdateEntry(
  payload: EntryPayload
): Promise<EntryMutationResult> {
  try {
    const data = await api.addEntry(payload);
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }
}

/**
 * Delete an entry by ID
 * Maps to DELETE /entries/:id endpoint
 */
export async function deleteEntry(id: number): Promise<EntryMutationResult> {
  try {
    const data = await api.deleteEntry(id);
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }
}

/**
 * Finalize a day (marks all goals as complete for the day)
 * Maps to POST /finalize_day endpoint
 */
export async function finalizeDay(date: string): Promise<EntryMutationResult> {
  try {
    const data = await api.finalizeDay(date);
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }
}

/**
 * Batch create/update multiple entries
 * Useful for saving multiple dirty rows at once
 */
export async function batchCreateOrUpdateEntries(
  entries: EntryPayload[]
): Promise<EntryMutationResult> {
  try {
    const results = await Promise.all(
      entries.map((entry) => api.addEntry(entry))
    );
    return {
      success: true,
      data: results,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error : new Error(String(error)),
    };
  }
}
