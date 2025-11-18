import copy
import time
from threading import Lock
from typing import Callable, Dict, NamedTuple, Optional, Tuple


class CacheScope(NamedTuple):
    user_id: Optional[int]
    is_admin: bool


CacheEntry = Tuple[float, object, Optional[CacheScope]]

_cache_storage: Dict[str, CacheEntry] = {}
_cache_lock = Lock()
_time_provider: Callable[[], float] = time.time

TODAY_CACHE_TTL = 60
STATS_CACHE_TTL = 300


def _cache_scope_key_parts(scope: Optional[CacheScope]) -> Tuple[str, ...]:
    if scope is None:
        return tuple()
    user_component = (
        f"user:{scope.user_id}" if scope.user_id is not None else "user:anonymous"
    )
    role_component = "role:admin" if scope.is_admin else "role:user"
    return (user_component, role_component)


def build_cache_key(
    prefix: str, key_parts: Tuple, *, scope: Optional[CacheScope] = None
) -> str:
    namespaced_parts = _cache_scope_key_parts(scope) + key_parts
    key_str = "::".join(str(part) for part in namespaced_parts)
    return f"{prefix}::{key_str}"


def cache_get(prefix: str, key_parts: Tuple, *, scope: Optional[CacheScope] = None):
    key = build_cache_key(prefix, key_parts, scope=scope)
    with _cache_lock:
        entry = _cache_storage.get(key)
        if not entry:
            return None
        expires_at, value, entry_scope = entry
        if expires_at <= _time_provider():
            del _cache_storage[key]
            return None
        if scope and entry_scope and scope != entry_scope:
            return None
        return copy.deepcopy(value)


def cache_set(
    prefix: str,
    key_parts: Tuple,
    value: object,
    ttl: int,
    *,
    scope: Optional[CacheScope] = None,
) -> None:
    key = build_cache_key(prefix, key_parts, scope=scope)
    with _cache_lock:
        _cache_storage[key] = (_time_provider() + ttl, copy.deepcopy(value), scope)


def invalidate_cache(prefix: str) -> None:
    key_prefix = prefix + "::"
    with _cache_lock:
        for key in list(_cache_storage.keys()):
            if key.startswith(key_prefix):
                del _cache_storage[key]


def cache_health() -> bool:
    try:
        with _cache_lock:
            _ = len(_cache_storage)
        return True
    except Exception:
        return False


def set_time_provider(func: Callable[[], float]) -> None:
    """Override time provider (used in tests)."""
    global _time_provider
    _time_provider = func
