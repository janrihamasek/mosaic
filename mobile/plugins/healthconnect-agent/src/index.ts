import { registerPlugin } from '@capacitor/core';

import type { HealthConnectAgentPlugin } from './definitions';
import type { AgentInitOptions, CanonicalWearableReading, ReadOptions, SyncParams, SyncResult, WearableType } from './types';
import { enqueueReadings, getCheckpoint, setCheckpoint } from './storage';
import { syncPendingReadings } from './sync';

const plugin = registerPlugin<HealthConnectAgentPlugin>('HealthConnectAgent', {
  web: () => import('./web').then((module) => new module.HealthConnectAgentWeb())
});

const readMethodMap: Record<WearableType, keyof HealthConnectAgentPlugin> = {
  steps: 'readSteps',
  heart_rate: 'readHeartRate',
  sleep: 'readSleepSessions'
};

const hasWindow = typeof window !== 'undefined';
const hasNavigator = typeof navigator !== 'undefined';

let agentConfig: AgentInitOptions | null = null;
let autoSyncHandle: ReturnType<typeof setInterval> | null = null;
let onlineListenerRegistered = false;

async function readAndQueue(type: WearableType, options?: ReadOptions): Promise<CanonicalWearableReading[]> {
  const method = readMethodMap[type];
  const checkpoint = await getCheckpoint(type);
  const pluginOptions: ReadOptions = {};
  const startCandidate = options?.start ?? (checkpoint > 0 ? checkpoint : undefined);

  if (typeof startCandidate === 'number') {
    pluginOptions.start = startCandidate;
  }
  if (typeof options?.end === 'number') {
    pluginOptions.end = options.end;
  }
  if (typeof options?.limit === 'number') {
    pluginOptions.limit = options.limit;
  }

  const result = await plugin[method](pluginOptions);
  const readings = result?.readings ?? [];

  await enqueueReadings(readings);

  const highestTimestamp = readings.reduce((acc, current) => {
    const timestamp = Date.parse(current.end ?? current.start);
    return Number.isNaN(timestamp) ? acc : Math.max(acc, timestamp);
  }, checkpoint);

  if (highestTimestamp > checkpoint) {
    await setCheckpoint(type, highestTimestamp);
  }

  return readings;
}

function isOnline(): boolean {
  return hasNavigator ? navigator.onLine : true;
}

function registerOnlineHandler(): void {
  if (onlineListenerRegistered || !hasWindow || !hasNavigator) {
    return;
  }

  window.addEventListener('online', () => {
    if (isOnline()) {
      void HealthConnectAgent.syncPending();
    }
  });
  onlineListenerRegistered = true;
}

function setupAutoSync(): void {
  if (autoSyncHandle) {
    clearInterval(autoSyncHandle);
    autoSyncHandle = null;
  }
  if (!agentConfig?.autoSyncIntervalMs || !hasWindow) {
    return;
  }

  autoSyncHandle = window.setInterval(() => {
    if (isOnline()) {
      void HealthConnectAgent.syncPending();
    }
  }, agentConfig.autoSyncIntervalMs);
}

async function ensureSyncParams(overrides?: Partial<SyncParams>): Promise<SyncParams> {
  if (!agentConfig) {
    throw new Error('HealthConnectAgent is not initialized');
  }

  const jwt = overrides?.jwt ?? (await agentConfig.jwtProvider());
  return {
    backendUrl: overrides?.backendUrl ?? agentConfig.backendUrl,
    deviceId: overrides?.deviceId ?? agentConfig.deviceId,
    jwt
  };
}

export const HealthConnectAgent = {
  initialize(config: AgentInitOptions): void {
    agentConfig = config;
    setupAutoSync();
    registerOnlineHandler();
  },

  async readSteps(options?: ReadOptions): Promise<CanonicalWearableReading[]> {
    return readAndQueue('steps', options);
  },

  async readHeartRate(options?: ReadOptions): Promise<CanonicalWearableReading[]> {
    return readAndQueue('heart_rate', options);
  },

  async readSleepSessions(options?: ReadOptions): Promise<CanonicalWearableReading[]> {
    return readAndQueue('sleep', options);
  },

  async syncPending(overrides?: Partial<SyncParams>): Promise<SyncResult> {
    try {
      const params = await ensureSyncParams(overrides);
      const result = await syncPendingReadings(params);
      agentConfig?.onSync?.(result);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const result: SyncResult = { success: false, error: message };
      agentConfig?.onSync?.(result);
      return result;
    }
  }
};

export { HealthConnectAgentPlugin } from './definitions';
