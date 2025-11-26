/**
 * Activities Mutation Service
 * 
 * Centralized service for activity write operations that affect the daily loop.
 * Wraps API calls and provides a consistent interface for mutations.
 */

import * as api from "../../api";

export interface ActivityPayload {
  name: string;
  category: string;
  goal: number;
  activity_type: "positive" | "negative" | "neutral";
  description?: string;
  frequency_per_day?: number;
  frequency_per_week?: number;
}

export interface ActivityUpdatePayload {
  name?: string;
  category?: string;
  goal?: number;
  activity_type?: "positive" | "negative" | "neutral";
  description?: string;
  frequency_per_day?: number;
  frequency_per_week?: number;
  active?: boolean;
}

export interface ActivityMutationResult {
  success: boolean;
  data?: any;
  error?: Error;
}

/**
 * Create a new activity
 * Maps to POST /add_activity endpoint
 */
export async function createActivity(
  payload: ActivityPayload
): Promise<ActivityMutationResult> {
  try {
    const data = await api.addActivity(payload);
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
 * Update an existing activity
 * Maps to PUT /activities/:id endpoint
 */
export async function updateActivity(
  id: number,
  payload: ActivityUpdatePayload
): Promise<ActivityMutationResult> {
  try {
    const data = await api.updateActivity(id, payload);
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
 * Activate an activity (makes it appear in daily loop)
 * Maps to PATCH /activities/:id/activate endpoint
 */
export async function activateActivity(
  id: number
): Promise<ActivityMutationResult> {
  try {
    const data = await api.activateActivity(id);
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
 * Deactivate an activity (removes it from daily loop)
 * Maps to PATCH /activities/:id/deactivate endpoint
 */
export async function deactivateActivity(
  id: number
): Promise<ActivityMutationResult> {
  try {
    const data = await api.deactivateActivity(id);
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
 * Delete an activity permanently
 * Maps to DELETE /activities/:id endpoint
 */
export async function deleteActivity(
  id: number
): Promise<ActivityMutationResult> {
  try {
    const data = await api.deleteActivity(id);
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
