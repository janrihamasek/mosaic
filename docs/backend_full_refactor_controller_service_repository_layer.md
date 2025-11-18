
## Goal
Fully refactor the Mosaic backend into a clean layered architecture where all HTTP controllers become thin wrappers, all domain logic resides in service modules, and all SQL is isolated in repository modules. After completion, the backend must have: controllers → services → repositories → models, with no leftover logic outside these layers.

## Context
backend/app.py currently mixes validation, domain rules, SQL, ETL triggers, cache invalidation, and logging. This prevents modularity, mobile reuse, and predictable maintenance. This task performs a complete extraction into services and repositories as specified in repo-structure.md, layering-rules.md, dependency-matrix.md, backend-call-tree.md. The final state must contain no business logic or SQL in controllers, no Flask imports in services, no service logic or HTTP concerns in repositories, and full test coverage passing.

## Tasks

### Task A – Controllers Package Extraction

- Create backend/controllers package with auth_controller.py, activities_controller.py, entries_controller.py, stats_controller.py, backup_controller.py, nightmotion_controller.py, admin_controller.py, wearable_controller.py.
    
- Move all route functions from app.py into these controllers.
    
- Keep only payload parsing, decorators, service calls, and jsonify in controllers.
    

### Task B – Service Layer Creation

**B1 – Scaffold Services Package**

- Create backend/services/ with empty modules for all services.
    
- Add shared helpers (cache usage wrappers, idempotency helpers, common types).
    

**B2 – Auth & Admin Services**

- Implement register/login/profile update/delete/admin list/admin delete.
    
- Return plain Python data. Update controllers to call these services.
    

**B3 – Activities Service**

- Implement add/update/activate/deactivate/delete.
    
- Include propagation to entries, idempotency handling, cache invalidation.
    

**B4 – Entries Service**

- Implement list/add/delete/finalize_day.
    
- Include upsert/auto-create, idempotency, cache invalidation.
    

**B5 – Stats & Today Service**

- Implement cache-scoped today payload builder.
    
- Implement stats/progress windows and ratios.
    

**B6 – Backup & Export Service**

- Wrap BackupManager operations, scheduler/config toggles.
    
- Implement export builders (json/csv) without Flask types.
    

**B7 – Wearable Service**

- Implement batch ingest (DB writes), dedupe, ETL trigger.
    
- Return only structured payload summary.
    

**B8 – NightMotion Service**

- Implement RTSP URL normalization, FFmpeg proxy process orchestration.
    
- Provide iterator/generator for MJPEG frames.
    

**B9 – Controller Rewire for Services**

- Update all controllers to call the new service functions.
    
- Controllers perform only: parse, decorate, call, jsonify.
    

**B10 – Test & Documentation Updates**

- Add unit tests for all services.
    
- Update controller tests to mock services.
    
- Align layering comments where necessary.
    

### Task C – Repository Layer Creation – Repository Layer Creation

- Create backend/repositories with activities_repo.py, entries_repo.py, users_repo.py, wearable_repo.py, backup_repo.py, stats_repo.py.
    
- Move all SQL from controllers/services into repository methods.

- Repositories must use transactional_connection and contain only DB access.
    

### Task D – Infra Consolidation

- Move cache logic into backend/infra/cache_manager.py; services must use it.
    
- Move rate_limit, metrics, auth helpers into backend/infra/.
    
- Restore metrics/health helpers removed from app.py using new infra modules.
    
- Ensure health endpoint calls cache/metrics helpers correctly.
    
- Update controllers and services to use the new infra modules.
    
- Move cache logic into backend/infra/cache_manager.py; services must use it.
    
- Move rate_limit, metrics, auth helpers into backend/infra/.
    
- Update controllers and services to use the new infra modules.
    

### Task E – Import Cleanup & Layer Enforcement

- Update all imports throughout backend.
    
- Remove SQL, domain logic, ETL, cache calls from app.py.
    
- Replace all remaining _current_user_id/_is_admin_user/parse_pagination with controllers.helpers equivalents.
    
- Maintain app.stream_rtsp re-export if tests require it.
    
- Ensure no cross-layer import violations.
    
- Update all imports throughout backend.
    
- Remove SQL, domain logic, ETL, cache calls from app.py.
    
- Ensure no cross-layer import violations.
    

### Task F – Backup & Wearable Integration Fix

- Ensure BackupManager and wearable ETL run exclusively through services.
    
- Remove any direct controller → ETL or controller → BackupManager paths.
    

### Task G – NightMotion Streaming Isolation

- Ensure full FFmpeg/RTSP orchestration resides in nightmotion_service.
    
- Controller performs only HTTP wrapping.
    

### Task H – Repository Structure Alignment

- Ensure folder structure matches repo-structure.md.
    
- Add **init**.py files where required.
    

### Task I – Test Suite Realignment

- Update unit tests to target services and repositories.
    
- Update controller tests to mock services only.
    
- Ensure pytest suite passes.
    

### Task J – Cleanup & Documentation Notes

- Remove dead code, TODOs, obsolete helpers from app.py.
    
- Adjust inline documentation to match new structure.
    
Output
Complete backend refactor with: fully modular controllers package; fully implemented service layer; fully isolated repository layer; unified infra modules; cleaned app.py; updated tests; no SQL or domain logic left in controllers; no HTTP concerns in services; no business logic in repositories; 100% passing test suite; architecture consistent with layering-rules.md, dependency-matrix.md, and repo-structure.md.