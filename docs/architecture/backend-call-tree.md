# Mosaic Backend Call Tree

Every Flask endpoint follows the same layered pattern: authentication and API-key guards, rate limiting, payload validation, service/database work, cache invalidation, and structured responses. This document enumerates each endpoint’s execution tree using indented arrows (`→`), along with dedicated sections for shared subsystems.

## Global Request Hooks
- `before_request`
  - `_start_request_timer` → bind request ID/route for metrics + logging
  - `_enforce_api_key` → `require_api_key()` (rejects when missing/invalid)
  - `_enforce_jwt_authentication`
    - Skip public endpoints / OPTIONS
    - Parse `Authorization` header
    - `_decode_access_token()` → attach `g.current_user`
- `after_request`
  - `_log_request()` → log `request.completed`, update metrics counters, bind user_id
- `teardown_request`
  - On unhandled exception, `_record_request_metrics(..., is_error=True)`

## Auth & User Management

### `POST /register`
```
request → rate_limit("register") → validate_register_payload
  → hash password (werkzeug) → db_transaction
    → INSERT INTO users
    → log_event("auth.register")
  → jsonify 201
```

### `POST /login`
```
request → rate_limit("login") → validate_login_payload
  → lookup user (SELECT users) → check_password_hash
  → _create_access_token → log_event("auth.login")
  → jsonify tokens (includes display_name/is_admin)
```

### `GET /user`
```
jwt_required → fetch current user row → jsonify profile
```

### `PATCH /user`
```
jwt_required → validate_user_update_payload
  → build UPDATE list → db_transaction (UPDATE users)
  → fetch updated row → invalidate_cache("today"/"stats") → jsonify
```

### `DELETE /user`
```
jwt_required → db_transaction DELETE users WHERE id=current
  → invalidate_cache("today"/"stats") → jsonify({ message })
```

### Admin-only Users (`GET /users`, `DELETE /users/<id>`)
```
require_admin → SELECT users ORDER BY username → jsonify list
```
```
require_admin → prevent self-delete → db_transaction DELETE
  → invalidate_cache("today"/"stats") → jsonify({ message })
```

## Activity Endpoints

### `GET /activities`
```
jwt_required → parse `all` flag + pagination → SELECT activities (scoped by user/admin)
  → jsonify rows (normalise booleans)
```

### `POST /add_activity`
```
jwt_required → rate_limit("add_activity") → check idempotency key
  → validate_activity_create_payload → db_transaction INSERT
      ↳ on IntegrityError and X-Overwrite-Existing → UPDATE existing row
  → invalidate_cache("today"), invalidate_cache("stats")
  → log_event("activity.create" / "activity.create_failed") → jsonify
```

### `PUT /activities/<id>` (update metadata)
```
jwt_required → rate_limit("update_activity") → validate payload
  → db_transaction
      → SELECT activity, enforce ownership unless admin
      → UPDATE activities set fields
      → UPDATE entries matching activity name to propagate description/category/goal
  → invalidate_cache("today"/"stats") → jsonify
```

### `PATCH /activities/<id>/deactivate` / `activate`
```
jwt_required → rate_limit("activity_status") → db_transaction UPDATE active flag
  → invalidate_cache("today"/"stats") → jsonify message
```

### `DELETE /activities/<id>`
```
jwt_required → rate_limit("delete_activity") → ensure activity is inactive
  → db_transaction DELETE row → invalidate_cache("today"/"stats")
  → jsonify
```

## Entry / Today / Stats Endpoints

### `GET /entries`
```
jwt_required → parse filters (dates/activity/category) → validate date formats
  → build SQL WHERE clauses (respect user/admin scope) + pagination
  → SELECT entries LEFT JOIN activities → jsonify list
```

### `POST /add_entry`
```
jwt_required → rate_limit("add_entry") → idempotency lookup (X-Idempotency-Key)
  → validate_entry_payload
  → db_transaction
      → lookup matching activity (user-owned or shared)
      → upsert entry (UPDATE existing user row → fallback to shared row → INSERT new)
      → auto-create activity if missing (INSERT activities)
  → invalidate_cache("today"/"stats") → store idempotency response → jsonify
```

### `DELETE /entries/<id>`
```
jwt_required → rate_limit("delete_entry") → db_transaction DELETE (scoped to user unless admin)
  → log_event("entry.delete")
  → invalidate_cache("today"/"stats") → jsonify
```

### `GET /today`
```
jwt_required → parse date + pagination → build cache scope key (CacheScope(user_id,is_admin))
  → cache_get("today", key)
    ↳ MISS → build JOIN query (activities LEFT JOIN entries for date)
      → SELECT rows, normalise booleans
      → cache_set("today", key, TTL=60)
  → jsonify cached/new data
```

### `GET /stats/progress`
```
jwt_required → parse optional `date`
  → cache_get("stats", ("dashboard", date))
    ↳ MISS → compute metrics window (SQL queries for totals, streaks, categories)
      → build payload (goal_completion, streak_length, distributions, etc.)
      → cache_set("stats", key, TTL=300)
  → jsonify
```

### `POST /finalize_day`
```
jwt_required → rate_limit("finalize_day") → validate_finalize_day_payload
  → db_transaction
      → SELECT active activities for date → SELECT existing entries for date
      → INSERT missing entries with value 0
  → invalidate_cache("today"/"stats") → jsonify({ message })
```

### `POST /import_csv`
```
jwt_required → rate_limit("import_csv") → validate_csv_import_payload(request.files)
  → save temp file → run_import_csv(tmp_path, user_id)
  → cleanup temp file → invalidate_cache("today"/"stats")
  → log_event("import.csv") → jsonify summary
```

## Export Endpoints

### `GET /export/json` / `GET /export/csv`
```
jwt_required → stream DB export (send_file) via api layer (no cache touches)
```

## Backup Manager Endpoints

### `GET /backup/status`
```
jwt_required → backup_manager.get_status()
  → (reads `backup_settings`, lists backups directory) → jsonify
```

### `POST /backup/run`
```
jwt_required → backup_manager.create_backup(initiated_by="api")
  → log_event("backup.run") → jsonify({ backup })
```

### `POST /backup/toggle`
```
jwt_required → parse payload → backup_manager.toggle(enabled?, interval?)
  → log_event("backup.toggle") → jsonify status
```

### `GET /backup/download/<filename>`
```
jwt_required → backup_manager.get_backup_path(filename) → send_file(zip)
```

**Backup Manager internal flow**
```
call → BackupManager.create_backup
  → acquire lock → _fetch_database_payload (SELECT entries + activities)
  → write JSON + CSV dumps → zip files → _update_last_run
  → release lock → return metadata
```
```
call → BackupManager.toggle
  → transactional_connection → upsert backup_settings row (enabled + interval)
  → return get_status()
```
```
daemon thread → _scheduler_loop
  → poll backup_settings
  → if enabled and interval elapsed → create_backup(initiated_by="scheduler")
```

## NightMotion Stream Proxy

### `GET /api/stream-proxy`
```
jwt_required → limit_request("stream_proxy", per_minute=2)
  → read RTSP url/user/pass from query → normalize via _normalize_rtsp_url
  → insert credentials into URL if needed
  → log start → Response(stream_with_context(stream_rtsp()))
```
**`stream_rtsp` pipeline**
```
call → _normalize_rtsp_url → subprocess.Popen(ffmpeg ... -f mjpeg)
  → spawn stderr reader thread (collect logs)
  → read stdout chunks → accumulate frame buffers
  → emit multipart MJPEG frames ("--frame" boundaries)
  → on failure → inspect stderr to raise PermissionError/RuntimeError
  → ensure process termination + cleanup on exit
```

## Wearable Ingest

### `POST /ingest/wearable/batch`
```
jwt_required → rate_limit("wearable_ingest") → validate_wearable_batch_payload
  → iterate records
      → write wearable_sources / wearable_raw rows
  → call process_wearable_raw_by_dedupe_keys (Wearable ETL)
  → jsonify summary (accepted/duplicates/errors)
```

## Logging & Metrics Endpoints

### `GET /metrics`
```
no auth required → format snapshot
  → if ?format=json → get_metrics_json
  → else → get_metrics_text (Prometheus format)
```

### `GET /healthz`
```
no auth required → _build_health_summary
  → check DB connection (SELECT 1)
  → check cache lock usability
  → gather metrics snapshot → jsonify + 503 if unhealthy
```

### `/logs/activity` & `/logs/runtime`
```
(jwt_required via blueprint) → fetch structured logs via audit/routes modules → jsonify
```

## Cache & Rate Limit Helpers

- `rate_limit(name, limit, window)`
  - Tracks hits per user/IP; returns `error_response("too_many_requests")` when exceeded.
- `CacheScope(user_id, is_admin)`
  - `cache_get(prefix, key_parts, scope)` → namespaced keys `prefix::user:ID::role:admin::...`
  - `cache_set` stores TTL + deep-copied payloads.
  - `invalidate_cache(prefix)` removes all entries matching the prefix.

Understanding these call trees makes it easier to add new endpoints or services without skipping required guards, rate limits, cache invalidations, or logging hooks.
