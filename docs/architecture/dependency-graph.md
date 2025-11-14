# Mosaic Dependency Graphs

This document complements `docs/architecture/dependency-map.md` with visual diagrams that highlight the primary dependency paths across Mosaic’s frontend and backend. Pair it with the [Redux Flow map](redux-flow.md), [Backend Call Tree](backend-call-tree.md), and [Dependency Matrix](dependency-matrix.md) for text-first perspectives. All diagrams use Mermaid syntax for easy inclusion in docs and code reviews.

## Global Flow: Components → Redux → API → Backend

```mermaid
graph TD
  classDef hotspot fill:#ffe4e1,stroke:#d33,stroke-width:2px;
  subgraph Frontend
    Components["React Components<br/>(Dashboard, Today, Stats, Admin, NightMotion)"]
    ActivitiesSlice[activitiesSlice]
    EntriesSlice[entriesSlice]
    AuthSlice[authSlice]
    AdminSlice[adminSlice]
    BackupSlice[backupSlice]
    NightMotionSlice[nightMotionSlice]
    AsyncThunks["Async Thunks<br/>(loadToday, saveDirtyTodayRows, loadStats,<br/>loadActivities, toggleBackup, loadHealth, startStream, ...)"]
    ApiHelpers["API Helpers<br/>(frontend/src/api.js)"]
  end

  subgraph Infrastructure
    ApiClient["apiClient.js<br/>(Axios + auth headers)"]
    FlaskControllers["Flask Controllers<br/>(app.py endpoints)"]
    Services["Service Layer<br/>(BackupManager, Wearable ETL, import_csv,<br/>NightMotion proxy, audit/logging)"]
    Models["SQLAlchemy Models<br/>(Activities, Entries, Users, Wearable*, BackupSettings)"]
    Cache[("In-memory Cache<br/>(today, stats)")]
    Metrics[("Metrics / Logs<br/>(structlog + /metrics)")]
    Postgres[("PostgreSQL DB")]
  end

  Components --> ActivitiesSlice
  Components --> EntriesSlice
  Components --> AuthSlice
  Components --> AdminSlice
  Components --> BackupSlice
  Components --> NightMotionSlice
  ActivitiesSlice --> AsyncThunks
  EntriesSlice --> AsyncThunks
  AuthSlice --> AsyncThunks
  AdminSlice --> AsyncThunks
  BackupSlice --> AsyncThunks
  NightMotionSlice --> AsyncThunks
  AsyncThunks --> ApiHelpers --> ApiClient:::hotspot --> FlaskControllers:::hotspot --> Services --> Models --> Postgres
  FlaskControllers --> Cache
  Cache --> FlaskControllers
  FlaskControllers --> Metrics
  Metrics --> AdminSlice
  Services --> NightMotionSlice
  Services --> BackupSlice
```

`apiClient.js` and the Flask controllers act as high-coupling nodes (highlighted) because every request crosses those boundaries. They demand extra care when introducing breaking changes.

## Data-Flow Focus: Today/Entries/Stats & Admin/Backup/Metrics

```mermaid
flowchart LR
  subgraph TodayEntriesStats
    direction LR
    TodayUI[Today / Entries / Stats UI]
    EntriesSliceTES[entriesSlice]
    TodayThunks["Thunks<br/>(loadToday, saveDirtyTodayRows, loadEntries, loadStats)"]
    ApiToday["api.js helpers<br/>(fetchToday, fetchEntries, fetchProgressStats, add_entry)"]
    ApiClientTES[apiClient]
    EndpointToday["/GET /today<br/>POST /add_entry<br/>GET /entries<br/>GET /stats/progress/"]
    CacheToday[("Cache buckets<br/>today, stats")]
    ControllerLogic["(Query builders +<br/>validation in app.py)"]
    ModelsTES["(Activities + Entries models)"]
    PostgresTES["(PostgreSQL)"]

    TodayUI --> EntriesSliceTES --> TodayThunks --> ApiToday --> ApiClientTES --> EndpointToday --> ControllerLogic --> ModelsTES --> PostgresTES
    PostgresTES --> ModelsTES --> ControllerLogic --> CacheToday --> ApiClientTES --> EntriesSliceTES
    TodayThunks -- invalidate --> CacheToday
    TodayThunks -- dispatch refresh --> EntriesSliceTES
  end

  subgraph AdminFlows
    direction LR
    AdminUI["Admin UI<br/>(Health, Logs, NightMotion, Backups)"]
    AdminSliceAF[adminSlice]
    BackupSliceAF[backupSlice]
    NightMotionSliceAF[nightMotionSlice]
    AdminThunks["Thunks<br/>(loadHealth, loadMetrics, loadLogs)"]
    BackupThunks["Thunks<br/>(loadBackupStatus, toggleBackup, runBackupNow)"]
    NightMotionClient["Stream fetch<br/>(getStreamProxyUrl + fetch)"]
    ApiAdmin["api.js helpers<br/>(fetchHealth, fetchMetrics, fetchActivityLogs, fetchRuntimeLogs)"]
    ApiBackup["api.js helpers<br/>(fetchBackupStatus, toggleBackupSettings, runBackup, downloadBackupFile)"]
    AdminEndpoints["/GET /healthz<br/>GET /metrics<br/>GET /logs/*/"]
    BackupEndpoints["/GET /backup/status<br/>POST /backup/toggle<br/>POST /backup/run<br/>GET /backup/download/"]
    StreamProxy["/GET /api/stream-proxy/"]
    BackupManagerSvc["BackupManager<br/>(thread + ZIP writes)"]
    MetricsStore[("In-memory metrics +<br/>sql health checks")]
    BackupSettings[("backup_settings table")]
    BackupFiles[("backups/*.zip on disk")]
    NightMotionSvc[("(FFmpeg proxy + RTSP feed)")]

    AdminUI --> AdminSliceAF --> AdminThunks --> ApiAdmin --> AdminEndpoints --> MetricsStore
    MetricsStore --> AdminSliceAF
    AdminUI --> BackupSliceAF --> BackupThunks --> ApiBackup --> BackupEndpoints --> BackupManagerSvc --> BackupSettings
    BackupManagerSvc --> BackupFiles
    BackupSettings --> BackupManagerSvc
    BackupManagerSvc --> BackupSliceAF
    AdminUI --> NightMotionSliceAF --> NightMotionClient --> StreamProxy --> NightMotionSvc --> NightMotionSliceAF
  end
```

**Cycles & Coupling Notes**
- The Today/Entries/Stats cluster includes an intentional feedback loop: writes (`saveDirtyTodayRows`/`add_entry`) immediately invalidate caches and re-dispatch `loadToday`, `loadEntries`, and `loadStats`. This keeps the UI consistent but couples `entriesSlice` tightly to other slices—any new feature should reuse these dispatches to avoid stale state.
- In the Admin cluster, `BackupManager` touches both the database (scheduler state) and the filesystem (ZIP exports), making it a high-coupling service. Similarly, the NightMotion stream proxy depends on external cameras via FFmpeg; failures propagate back to `nightMotionSlice` status updates.
- Metrics flows feedback into the Admin Health UI; because `/metrics` and `/healthz` share the in-memory registry, noisy endpoints can impact operator dashboards. Treat controller additions carefully to preserve metric labeling.
