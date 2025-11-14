# Mosaic Dependency Graphs

This document complements `docs/architecture/dependency-map.md` with visual diagrams that highlight the primary dependency paths across Mosaic’s frontend and backend. All diagrams use Mermaid syntax for easy inclusion in docs and code reviews.

## Global Flow: Components → Redux → API → Backend

```mermaid
graph TD
  classDef hotspot fill:#ffe4e1,stroke:#d33,stroke-width:2px;
  subgraph Frontend
    Components[React Components\n(Dashboard, Today, Stats, Admin, NightMotion)]
    ActivitiesSlice[activitiesSlice]
    EntriesSlice[entriesSlice]
    AuthSlice[authSlice]
    AdminSlice[adminSlice]
    BackupSlice[backupSlice]
    NightMotionSlice[nightMotionSlice]
    AsyncThunks[Async Thunks\n(loadToday, saveDirtyTodayRows, loadStats,\nloadActivities, toggleBackup, loadHealth, startStream, ...)]
    ApiHelpers[API Helpers\n(frontend/src/api.js)]
  end

  subgraph Infrastructure
    ApiClient[apiClient.js\n(Axios + auth headers)]
    FlaskControllers[Flask Controllers\n(app.py endpoints)]
    Services[Service Layer\n(BackupManager, Wearable ETL, import_csv,\nNightMotion proxy, audit/logging)]
    Models[SQLAlchemy Models\n(Activities, Entries, Users, Wearable*, BackupSettings)]
    Cache[(In-memory Cache\n(today, stats))]
    Metrics[(Metrics / Logs\n(structlog + /metrics))]
    Postgres[(PostgreSQL DB)]
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
    TodayThunks[Thunks\n(loadToday, saveDirtyTodayRows, loadEntries, loadStats)]
    ApiToday[api.js helpers\n(fetchToday, fetchEntries, fetchProgressStats, add_entry)]
    ApiClientTES[apiClient]
    EndpointToday[/GET /today\nPOST /add_entry\nGET /entries\nGET /stats/progress/]
    CacheToday[(Cache buckets\n today, stats )]
    ControllerLogic[(Query builders +\nvalidation in app.py)]
    ModelsTES[(Activities + Entries models)]
    PostgresTES[(PostgreSQL)]

    TodayUI --> EntriesSliceTES --> TodayThunks --> ApiToday --> ApiClientTES --> EndpointToday --> ControllerLogic --> ModelsTES --> PostgresTES
    PostgresTES --> ModelsTES --> ControllerLogic --> CacheToday --> ApiClientTES --> EntriesSliceTES
    TodayThunks -- invalidate --> CacheToday
    TodayThunks -- dispatch refresh --> EntriesSliceTES
  end

  subgraph AdminFlows
    direction LR
    AdminUI[Admin UI\n(Health, Logs, NightMotion, Backups)]
    AdminSliceAF[adminSlice]
    BackupSliceAF[backupSlice]
    NightMotionSliceAF[nightMotionSlice]
    AdminThunks[Thunks\n(loadHealth, loadMetrics, loadLogs)]
    BackupThunks[Thunks\n(loadBackupStatus, toggleBackup, runBackupNow)]
    NightMotionClient[Stream fetch\n(getStreamProxyUrl + fetch)]
    ApiAdmin[api.js helpers\n(fetchHealth, fetchMetrics, fetchActivityLogs, fetchRuntimeLogs)]
    ApiBackup[api.js helpers\n(fetchBackupStatus, toggleBackupSettings, runBackup, downloadBackupFile)]
    AdminEndpoints[/GET /healthz\nGET /metrics\nGET /logs/*/]
    BackupEndpoints[/GET /backup/status\nPOST /backup/toggle\nPOST /backup/run\nGET /backup/download/]
    StreamProxy[/GET /api/stream-proxy/]
    BackupManagerSvc[BackupManager\n(thread + ZIP writes)]
    MetricsStore[(In-memory metrics +\nsql health checks)]
    BackupSettings[(backup_settings table)]
    BackupFiles[(backups/*.zip on disk)]
    NightMotionSvc[(FFmpeg proxy + RTSP feed)]

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
