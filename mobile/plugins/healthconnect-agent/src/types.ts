export type WearableType = 'steps' | 'heart_rate' | 'sleep';

export interface CanonicalWearableReading {
  type: WearableType;
  start: string;
  end?: string;
  fields: Record<string, unknown>;
  dedupe_key: string;
}

export interface ReadOptions {
  start?: number;
  end?: number;
  limit?: number;
}

export interface AgentInitOptions {
  backendUrl: string;
  deviceId: string;
  jwtProvider: () => Promise<string>;
  autoSyncIntervalMs?: number;
  onSync?: (result: SyncResult) => void;
}

export interface SyncParams {
  backendUrl: string;
  deviceId: string;
  jwt: string;
}

export interface SyncResult {
  success: boolean;
  synced?: number;
  error?: string;
}
