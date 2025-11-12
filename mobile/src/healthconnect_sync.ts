import { HealthConnectAgent } from "@mosaic/healthconnect-agent";

export interface HealthConnectInitOptions {
  backendUrl: string;
  deviceId: string;
  jwtProvider: () => Promise<string>;
  autoSyncIntervalMs?: number;
}

let initialized = false;

export function initHealthConnect(options: HealthConnectInitOptions): void {
  if (initialized) {
    return;
  }
  initialized = true;

  HealthConnectAgent.initialize({
    backendUrl: options.backendUrl,
    deviceId: options.deviceId,
    jwtProvider: options.jwtProvider,
    autoSyncIntervalMs: options.autoSyncIntervalMs ?? 0,
    onSync: (result) => {
      if (result.success) {
        console.info("[HealthConnect] Sync succeeded", result.synced, "readings");
      } else {
        console.warn("[HealthConnect] Sync failed", result.error);
      }
    },
  });
  console.info("[HealthConnect] Agent initialized");
}

async function hydrateAndSync(): Promise<void> {
  await HealthConnectAgent.readSteps();
  await HealthConnectAgent.readHeartRate();
  await HealthConnectAgent.readSleepSessions();
  const syncResult = await HealthConnectAgent.syncPending();
  console.info("[HealthConnect] syncPending result", syncResult);
}

export async function syncNow(): Promise<void> {
  if (!initialized) {
    console.warn("[HealthConnect] Agent not initialized");
    return;
  }
  try {
    await hydrateAndSync();
  } catch (error) {
    console.error("[HealthConnect] sync failed", error);
  }
}

