import { getPendingBatch, removeReadings } from './storage';
import type { SyncParams, SyncResult } from './types';

const BASE_DELAY_MS = 600;
const MAX_RETRIES = 4;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function postWithRetry(url: string, init: RequestInit): Promise<Response> {
  let attempt = 0;
  let delay = BASE_DELAY_MS;

  while (true) {
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        const details = await response.text();
        throw new Error(`HTTP ${response.status}: ${details}`);
      }
      return response;
    } catch (error) {
      attempt += 1;
      if (attempt > MAX_RETRIES) {
        throw error;
      }
      await sleep(delay);
      delay *= 2;
    }
  }
}

export async function syncPendingReadings(params: SyncParams): Promise<SyncResult> {
  const pending = await getPendingBatch();
  if (!pending.length) {
    return { success: true, synced: 0 };
  }

  const endpoint = new URL('/ingest/wearable/batch', params.backendUrl).toString();
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${params.jwt}`,
    'X-Device-Id': params.deviceId,
    'Content-Type': 'application/json'
  };

  await postWithRetry(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify({ readings: pending })
  });

  await removeReadings(pending.map((reading) => reading.dedupe_key));
  return { success: true, synced: pending.length };
}
