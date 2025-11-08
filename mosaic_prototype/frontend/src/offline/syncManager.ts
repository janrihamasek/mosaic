import type { Store } from "@reduxjs/toolkit";
import { drainPendingWrites, getPendingCount, startQueueMonitor, subscribeQueue } from "./queue";
import { setLastSyncAt, setOnlineStatus, setPendingCount, setSyncing } from "../store/offlineSlice";

const SYNC_INTERVAL_MS = 60_000;

let storeRef: Store | null = null;
let syncTimer: number | undefined;
let unsubscribeQueueWatcher: (() => void) | null = null;

const isNavigatorOnline = () => (typeof navigator === "undefined" ? true : navigator.onLine);

async function runSync() {
  if (!storeRef) {
    return;
  }
  if (!isNavigatorOnline()) {
    storeRef.dispatch(setOnlineStatus(false));
    return;
  }
  storeRef.dispatch(setOnlineStatus(true));
  storeRef.dispatch(setSyncing(true));
  const result = await drainPendingWrites();
  storeRef.dispatch(setSyncing(false));
  storeRef.dispatch(setPendingCount(result.remaining));
  if (result.synced > 0) {
    storeRef.dispatch(setLastSyncAt(new Date().toISOString()));
  }
}

function scheduleSync() {
  if (typeof window === "undefined") {
    return;
  }
  if (syncTimer) {
    window.clearInterval(syncTimer);
  }
  syncTimer = window.setInterval(() => {
    void runSync();
  }, SYNC_INTERVAL_MS);
}

export function initOfflineSync(store: Store): void {
  if (storeRef) {
    return;
  }
  storeRef = store;
  if (typeof window !== "undefined") {
    window.addEventListener("online", () => {
      store.dispatch(setOnlineStatus(true));
      void runSync();
    });
    window.addEventListener("offline", () => {
      store.dispatch(setOnlineStatus(false));
    });
  }
  unsubscribeQueueWatcher = subscribeQueue(async () => {
    if (storeRef) {
      storeRef.dispatch(setPendingCount(await getPendingCount()));
    }
  });
  void (async () => {
    store.dispatch(setPendingCount(await getPendingCount()));
    await runSync();
  })();
  scheduleSync();
  startQueueMonitor(() => {
    void runSync();
  });
}

export function stopOfflineSync() {
  if (typeof window !== "undefined" && syncTimer) {
    window.clearInterval(syncTimer);
    syncTimer = undefined;
  }
  if (unsubscribeQueueWatcher) {
    unsubscribeQueueWatcher();
    unsubscribeQueueWatcher = null;
  }
  storeRef = null;
}
