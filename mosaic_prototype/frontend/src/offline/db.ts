/**
 * Lightweight IndexedDB wrapper with in-memory fallback for environments where
 * IndexedDB is not available (tests, legacy browsers).
 */

export interface PendingWriteRecord {
  id?: number;
  action: string;
  endpoint: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  payload: Record<string, unknown>;
  createdAt: number;
  idempotencyKey: string;
  metadata?: Record<string, unknown>;
}

export interface SnapshotRecord<T = unknown> {
  key: string;
  data: T;
  updatedAt: number;
}

const DB_NAME = "mosaic_offline";
const DB_VERSION = 1;
const PENDING_STORE = "pendingWrites";
const SNAPSHOT_STORE = "snapshots";

type IDBDatabaseLike = IDBDatabase;

let dbPromise: Promise<IDBDatabaseLike> | null = null;
const inMemoryPending: PendingWriteRecord[] = [];
const inMemorySnapshots = new Map<string, SnapshotRecord>();

const hasIndexedDb =
  typeof window !== "undefined" &&
  typeof window.indexedDB !== "undefined" &&
  typeof window.indexedDB.open === "function";

function openDb(): Promise<IDBDatabaseLike> {
  if (!hasIndexedDb) {
    return Promise.reject(new Error("IndexedDB not supported"));
  }
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(PENDING_STORE)) {
          const pendingStore = db.createObjectStore(PENDING_STORE, {
            keyPath: "id",
            autoIncrement: true,
          });
          pendingStore.createIndex("byCreatedAt", "createdAt");
        }
        if (!db.objectStoreNames.contains(SNAPSHOT_STORE)) {
          db.createObjectStore(SNAPSHOT_STORE, { keyPath: "key" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error ?? new Error("Failed to open IndexedDB"));
    });
  }
  return dbPromise;
}

function isIDBRequest(value: unknown): value is IDBRequest {
  return !!value && typeof (value as IDBRequest).onsuccess === "function" && "result" in (value as IDBRequest);
}

async function withStore<T>(
  storeName: string,
  mode: IDBTransactionMode,
  callback: (store: IDBObjectStore) => T | IDBRequest
): Promise<T> {
  const db = await openDb();
  return await new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const store = tx.objectStore(storeName);
    let resolved = false;
    try {
      const outcome = callback(store);
      if (isIDBRequest(outcome)) {
        outcome.onsuccess = () => {
          resolved = true;
          resolve(outcome.result as T);
        };
        outcome.onerror = () => reject(outcome.error ?? new Error("IndexedDB request failed"));
      } else {
        resolved = true;
        resolve(outcome as T);
      }
    } catch (error) {
      reject(error);
    }
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed"));
    tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted"));
    tx.oncomplete = () => {
      if (!resolved) {
        resolve(undefined as T);
      }
    };
  });
}

export async function addPendingWrite(record: PendingWriteRecord): Promise<PendingWriteRecord> {
  if (!hasIndexedDb) {
    const id = Date.now() + Math.random();
    const next = { ...record, id };
    inMemoryPending.push(next);
    return next;
  }
  const id = await withStore(PENDING_STORE, "readwrite", (store) => store.add(record));
  return { ...record, id: Number(id) };
}

export async function listPendingWrites(): Promise<PendingWriteRecord[]> {
  if (!hasIndexedDb) {
    return [...inMemoryPending].sort((a, b) => a.createdAt - b.createdAt);
  }
  return withStore<PendingWriteRecord[]>(PENDING_STORE, "readonly", (store) =>
    store.index("byCreatedAt").getAll()
  );
}

export async function deletePendingWrite(id: number): Promise<void> {
  if (!hasIndexedDb) {
    const index = inMemoryPending.findIndex((item) => item.id === id);
    if (index >= 0) {
      inMemoryPending.splice(index, 1);
    }
    return;
  }
  await withStore(PENDING_STORE, "readwrite", (store) => {
    store.delete(id);
  });
}

export async function pendingWritesCount(): Promise<number> {
  if (!hasIndexedDb) {
    return inMemoryPending.length;
  }
  return withStore<number>(PENDING_STORE, "readonly", (store) => store.count());
}

export async function clearPendingWrites(): Promise<void> {
  if (!hasIndexedDb) {
    inMemoryPending.splice(0, inMemoryPending.length);
    return;
  }
  await withStore(PENDING_STORE, "readwrite", (store) => store.clear());
}

export async function saveSnapshot<T>(key: string, data: T): Promise<void> {
  const record: SnapshotRecord<T> = {
    key,
    data,
    updatedAt: Date.now(),
  };
  if (!hasIndexedDb) {
    inMemorySnapshots.set(key, record);
    return;
  }
  await withStore(SNAPSHOT_STORE, "readwrite", (store) => store.put(record));
}

export async function readSnapshot<T>(key: string): Promise<SnapshotRecord<T> | null> {
  if (!hasIndexedDb) {
    return (inMemorySnapshots.get(key) as SnapshotRecord<T>) ?? null;
  }
  const record = (await withStore<SnapshotRecord<T> | undefined>(
    SNAPSHOT_STORE,
    "readonly",
    (store) => store.get(key)
  )) as SnapshotRecord<T> | undefined;
  return record ?? null;
}

export async function deleteSnapshot(key: string): Promise<void> {
  if (!hasIndexedDb) {
    inMemorySnapshots.delete(key);
    return;
  }
  await withStore(SNAPSHOT_STORE, "readwrite", (store) => store.delete(key));
}

export async function listSnapshots(): Promise<SnapshotRecord[]> {
  if (!hasIndexedDb) {
    return Array.from(inMemorySnapshots.values());
  }
  return withStore<SnapshotRecord[]>(SNAPSHOT_STORE, "readonly", (store) => store.getAll());
}
