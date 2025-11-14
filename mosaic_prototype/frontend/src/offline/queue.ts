import apiClient from "../apiClient";
import {
  addPendingWrite,
  deletePendingWrite,
  listPendingWrites,
  pendingWritesCount,
  PendingWriteRecord,
} from "./db";

export type OfflineMethod = "POST" | "PUT" | "PATCH" | "DELETE";

export interface OfflineMutationInput {
  action: string;
  endpoint: string;
  method?: OfflineMethod;
  payload?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  idempotencyKey?: string;
}

export interface SubmitResult {
  queued: boolean;
}

const ONLINE_CHECK_INTERVAL = 60_000;

const OFFLINE_ERROR_CODES = new Set(["ERR_NETWORK", "ECONNABORTED", "FETCH_ERROR"]);

let syncInFlight = false;
let intervalId: number | undefined;
let listeners: Array<() => void> = [];

const getNavigatorOnline = () => (typeof navigator === "undefined" ? true : navigator.onLine);

const randomKey = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
};

export function isOfflineError(error: unknown): boolean {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return true;
  }
  if (!error || typeof error !== "object") {
    return false;
  }
  const err = error as { code?: string; message?: string; response?: unknown };
  if (!("response" in err) || !err.response) {
    if (err.code && OFFLINE_ERROR_CODES.has(err.code)) {
      return true;
    }
    if (err.message && /network\s*error/i.test(err.message)) {
      return true;
    }
  }
  return false;
}

async function sendWrite(
  record: PendingWriteRecord,
  { forceOverwrite = false }: { forceOverwrite?: boolean } = {}
): Promise<void> {
  const headers: Record<string, string> = {
    "X-Idempotency-Key": record.idempotencyKey,
  };
  if (forceOverwrite) {
    headers["X-Overwrite-Existing"] = "1";
  }
  await apiClient.request(
    {
      url: record.endpoint,
      method: record.method,
      data: record.payload,
      headers,
      skipErrorNotification: true,
    } as Record<string, unknown>
  );
}

async function queueWrite(record: PendingWriteRecord): Promise<void> {
  await addPendingWrite(record);
  notifyListeners();
}

function notifyListeners() {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch (error) {
      console.error("offline queue listener failed", error);
    }
  });
}

export function subscribeQueue(listener: () => void): () => void {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((cb) => cb !== listener);
  };
}

export async function submitOfflineMutation(input: OfflineMutationInput): Promise<SubmitResult> {
  const record: PendingWriteRecord = {
    action: input.action,
    endpoint: input.endpoint,
    method: input.method ?? "POST",
    payload: input.payload ?? {},
    metadata: input.metadata,
    idempotencyKey: input.idempotencyKey || randomKey(),
    createdAt: Date.now(),
  };

  try {
    if (!getNavigatorOnline()) {
      throw new Error("offline");
    }
    await sendWrite(record);
    return { queued: false };
  } catch (error) {
    if (isOfflineError(error)) {
      await queueWrite(record);
      return { queued: true };
    }
    throw error;
  }
}

async function processRecord(record: PendingWriteRecord): Promise<boolean> {
  try {
    await sendWrite(record);
    await deletePendingWrite(record.id!);
    return true;
  } catch (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status && (status === 409 || status === 422)) {
      await sendWrite(record, { forceOverwrite: true });
      await deletePendingWrite(record.id!);
      return true;
    }
    if (isOfflineError(error)) {
      return false;
    }
    console.error("Failed to replay offline mutation", error);
    // Leave record in queue for a later retry.
    return false;
  }
}

export async function drainPendingWrites(): Promise<{ synced: number; remaining: number }> {
  if (syncInFlight) {
    return { synced: 0, remaining: await pendingWritesCount() };
  }
  syncInFlight = true;
  let processed = 0;
  try {
    const queue = await listPendingWrites();
    for (const record of queue) {
      const ok = await processRecord(record);
      if (!ok) {
        break;
      }
      processed += 1;
    }
  } finally {
    syncInFlight = false;
    notifyListeners();
  }
  return { synced: processed, remaining: await pendingWritesCount() };
}

export async function getPendingCount(): Promise<number> {
  return pendingWritesCount();
}

export function startQueueMonitor(callback: () => void): () => void {
  if (intervalId === undefined && typeof window !== "undefined") {
    intervalId = window.setInterval(callback, ONLINE_CHECK_INTERVAL);
  }
  return () => {
    if (intervalId !== undefined && typeof window !== "undefined") {
      window.clearInterval(intervalId);
      intervalId = undefined;
    }
  };
}
