import type { CanonicalWearableReading, WearableType } from './types';

const DB_NAME = 'healthconnect-agent-db';
const DB_VERSION = 1;
const STORE_READINGS = 'pending_readings';
const STORE_CHECKPOINTS = 'checkpoints';

let cachedDb: Promise<IDBDatabase> | null = null;

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_READINGS)) {
        db.createObjectStore(STORE_READINGS, { keyPath: 'dedupe_key' });
      }
      if (!db.objectStoreNames.contains(STORE_CHECKPOINTS)) {
        db.createObjectStore(STORE_CHECKPOINTS, { keyPath: 'type' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function getDb(): Promise<IDBDatabase> {
  if (!cachedDb) {
    cachedDb = openDatabase();
  }
  return cachedDb;
}

function transactionResult(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function enqueueReadings(readings: CanonicalWearableReading[]): Promise<void> {
  if (!readings.length) {
    return;
  }
  const db = await getDb();
  const tx = db.transaction(STORE_READINGS, 'readwrite');
  const store = tx.objectStore(STORE_READINGS);
  readings.forEach((reading) => store.put(reading));
  await transactionResult(tx);
}

export async function getPendingBatch(limit = 250): Promise<CanonicalWearableReading[]> {
  const db = await getDb();
  const tx = db.transaction(STORE_READINGS, 'readonly');
  const store = tx.objectStore(STORE_READINGS);
  return new Promise((resolve, reject) => {
    const items: CanonicalWearableReading[] = [];
    const request = store.openCursor();

    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result as IDBCursorWithValue | null;
      if (cursor && items.length < limit) {
        items.push(cursor.value as CanonicalWearableReading);
        cursor.continue();
      } else {
        resolve(items);
      }
    };

    request.onerror = () => reject(request.error);
  });
}

export async function removeReadings(keys: string[]): Promise<void> {
  if (!keys.length) {
    return;
  }
  const db = await getDb();
  const tx = db.transaction(STORE_READINGS, 'readwrite');
  const store = tx.objectStore(STORE_READINGS);
  keys.forEach((key) => store.delete(key));
  await transactionResult(tx);
}

export async function getCheckpoint(type: WearableType): Promise<number> {
  const db = await getDb();
  const tx = db.transaction(STORE_CHECKPOINTS, 'readonly');
  const request = tx.objectStore(STORE_CHECKPOINTS).get(type);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const value = request.result;
      resolve(typeof value?.value === 'number' ? value.value : 0);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function setCheckpoint(type: WearableType, value: number): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(STORE_CHECKPOINTS, 'readwrite');
  tx.objectStore(STORE_CHECKPOINTS).put({ type, value });
  await transactionResult(tx);
}
