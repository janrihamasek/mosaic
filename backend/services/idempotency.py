import os
import time
from threading import Lock
from typing import Dict, Optional, Tuple

_IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("IDEMPOTENCY_TTL_SECONDS", "600"))
_idempotency_lock = Lock()
_idempotency_store: Dict[Tuple[int, str], Tuple[float, dict, int]] = {}


def lookup(user_id: int, key: Optional[str]) -> Optional[Tuple[dict, int]]:
    if not key:
        return None
    now = time.time()
    with _idempotency_lock:
        entry = _idempotency_store.get((user_id, key))
        if not entry:
            return None
        created_at, payload, status = entry
        if now - created_at > _IDEMPOTENCY_TTL_SECONDS:
            _idempotency_store.pop((user_id, key), None)
            return None
        return payload, status


def store_response(
    user_id: int, key: Optional[str], payload: dict, status: int
) -> None:
    if not key:
        return
    now = time.time()
    with _idempotency_lock:
        _idempotency_store[(user_id, key)] = (now, payload, status)
