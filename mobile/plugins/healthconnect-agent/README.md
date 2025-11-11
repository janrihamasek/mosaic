# HealthConnect Agent Plugin

`@mosaic/healthconnect-agent` is a Capacitor plugin that bridges Android Health Connect to the Mosaic wearable ingestion pipeline. It keeps a local IndexedDB queue of normalized steps, heart rate, and sleep sessions, supports delta-syncing new data, and posts batches to `/ingest/wearable/batch` with JWT + `X-Device-Id` headers.

## Installation

```bash
npm install @mosaic/healthconnect-agent
npx cap sync android
```

Then add the plugin module to your Android build settings (e.g., include `:healthconnect-agent` in `settings.gradle` and add it as a dependency in your app module). The plugin ships with an Android library in `android/` that pulls in the Health Connect and Capacitor runtimes.

## Initialization

Call `HealthConnectAgent.initialize` as early as possible once you know your JWT and device identity:

```ts
import { HealthConnectAgent } from '@mosaic/healthconnect-agent';

HealthConnectAgent.initialize({
  backendUrl: 'https://api.mosaic.example',
  deviceId: await deviceInfo.getId(),
  jwtProvider: async () => authStore.tokens.accessToken,
  autoSyncIntervalMs: 1000 * 60 * 5,
  onSync: (result) => {
    if (!result.success) {
      console.warn('Sync failure', result.error);
    }
  }
});
```

`jwtProvider` is invoked before each sync so you can refresh the token automatically.

## Reading Wearables Data

Each `read*` call queries Health Connect and enqueues the normalized output:

```ts
await HealthConnectAgent.readSteps();
await HealthConnectAgent.readHeartRate({ limit: 50 });
await HealthConnectAgent.readSleepSessions({ start: Date.now() - 86_400_000 });
```

Readings conform to the canonical shape:

```json
{
  "type": "steps",
  "start": "2025-11-03T06:00:00Z",
  "end": "2025-11-03T07:00:00Z",
  "fields": { "count": 850 },
  "dedupe_key": "steps::1700...::...::{}"
}
```

The built-in checkpointing logic keeps track of the latest timestamp per type so each read only fetches deltas.

## Syncing to Mosaic

`syncPending` drains the IndexedDB queue with exponential backoff, attaches `Authorization: Bearer <JWT>` and `X-Device-Id` headers, and POSTs to `/ingest/wearable/batch`:

```ts
await HealthConnectAgent.syncPending();
```

Automatic syncs run when the device regains connectivity (`window`/`navigator` must be available) and every `autoSyncIntervalMs` if configured. Errors are surfaced via the optional `onSync` handler.

## Web Fallback

When executed in a non-Android web context the plugin returns empty arrays and leaves the ingest queue untouched.

## Types and Intentions

TypeScript consumers can import `AgentInitOptions`, `ReadOptions`, and `SyncResult` from `src/types.ts`. The plugin also re-exports the Capacitor bridge interface (`HealthConnectAgentPlugin`).

## Android Notes

- Request the Health Connect permission scopes before calling `read*` (Capacitor `requestPermissions` + Jetpack Health Connect SDK). This implementation expects the client to already have consent.
- The Java module in `android/src/main/java/com/mosaic/healthconnectagent/HealthConnectAgentPlugin.java` normalizes `StepsRecord`, `HeartRateRecord`, and `SleepSessionRecord` to the canonical shape and wires them to the Capacitor bridge.
- The plugin bundle requires `capcitor.properties` (if used) and the `androidx.health.connect` dependency already declared in `android/build.gradle`.

This plugin completes the ingestion chain by letting your mobile app read Health Connect metrics, persist them locally, and reliably push batches into the Mosaic backend.
