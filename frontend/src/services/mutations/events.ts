/**
 * Mutation Events System
 * 
 * Provides a centralized event system for mutation completions.
 * Allows different parts of the app to react to data changes without tight coupling.
 * 
 * This is the foundation for the listener architecture described in the roadmap.
 */

export type MutationType = 
  | "entry.created"
  | "entry.updated"
  | "entry.deleted"
  | "entry.finalized"
  | "activity.created"
  | "activity.updated"
  | "activity.activated"
  | "activity.deactivated"
  | "activity.deleted";

export interface MutationEvent {
  type: MutationType;
  payload?: any;
  timestamp: number;
  metadata?: {
    source?: string;
    userId?: number;
    [key: string]: any;
  };
}

export type MutationListener = (event: MutationEvent) => void;

class MutationEventEmitter {
  private listeners: Map<MutationType, Set<MutationListener>> = new Map();
  private globalListeners: Set<MutationListener> = new Set();

  /**
   * Subscribe to a specific mutation type
   */
  on(type: MutationType, listener: MutationListener): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.get(type)?.delete(listener);
    };
  }

  /**
   * Subscribe to all mutation events
   */
  onAny(listener: MutationListener): () => void {
    this.globalListeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.globalListeners.delete(listener);
    };
  }

  /**
   * Emit a mutation event
   */
  emit(type: MutationType, payload?: any, metadata?: MutationEvent["metadata"]): void {
    const event: MutationEvent = {
      type,
      payload,
      timestamp: Date.now(),
      metadata,
    };

    // Notify type-specific listeners
    const typeListeners = this.listeners.get(type);
    if (typeListeners) {
      typeListeners.forEach((listener) => {
        try {
          listener(event);
        } catch (error) {
          console.error(`Error in mutation listener for ${type}:`, error);
        }
      });
    }

    // Notify global listeners
    this.globalListeners.forEach((listener) => {
      try {
        listener(event);
      } catch (error) {
        console.error("Error in global mutation listener:", error);
      }
    });
  }

  /**
   * Remove all listeners (useful for testing)
   */
  clear(): void {
    this.listeners.clear();
    this.globalListeners.clear();
  }

  /**
   * Get count of listeners for debugging
   */
  getListenerCount(type?: MutationType): number {
    if (type) {
      return this.listeners.get(type)?.size ?? 0;
    }
    let total = this.globalListeners.size;
    this.listeners.forEach((listeners) => {
      total += listeners.size;
    });
    return total;
  }
}

// Singleton instance
export const mutationEvents = new MutationEventEmitter();

/**
 * Helper to emit mutation completed event
 */
export function emitMutationCompleted(
  type: MutationType,
  payload?: any,
  metadata?: MutationEvent["metadata"]
): void {
  mutationEvents.emit(type, payload, metadata);
}

/**
 * Helper to subscribe to mutation events
 */
export function onMutationCompleted(
  type: MutationType,
  listener: MutationListener
): () => void {
  return mutationEvents.on(type, listener);
}

/**
 * Helper to subscribe to all mutations
 */
export function onAnyMutation(listener: MutationListener): () => void {
  return mutationEvents.onAny(listener);
}
