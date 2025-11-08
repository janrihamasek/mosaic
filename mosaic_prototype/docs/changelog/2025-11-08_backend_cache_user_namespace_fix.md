### 251108_backend_cache_user_namespace_fix

The Flask cache helpers now accept a `CacheScope` that namespaces keys with `user_id` and role details. `/today` and `/stats/progress` wrap their cache lookups with this scope so multi-tenant payloads are isolated per user while keeping invalidation semantics unchanged. Cache entries also record the originating scope and emit a `cache.cross_user_hit` warning if a request ever resolves to a payload produced for a different user, giving observability into future regressions.

New pytest coverage (`tests/test_cache_namespace.py`) creates two users, warms the cache for the first user, and confirms the second continues to see empty summaries for both `/today` and `/stats/progress`. The `docs/changelog` entry tracks the regression fix so releases highlight the tenant-safety hardening.
