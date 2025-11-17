import threading
import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque, Optional

_rate_limit_storage: DefaultDict[str, Deque[float]] = defaultdict(deque)
_rate_limit_lock = threading.Lock()


def check_rate_limit(key: str, remote_addr: Optional[str], limit: int, window: int) -> bool:
    identifier = remote_addr or "anonymous"
    storage_key = f"{identifier}:{key}"
    now = time.time()

    with _rate_limit_lock:
        entries = _rate_limit_storage[storage_key]
        cutoff = now - window
        while entries and entries[0] <= cutoff:
            entries.popleft()
        if len(entries) >= limit:
            return True
        entries.append(now)
        return False


def reset() -> None:
    with _rate_limit_lock:
        _rate_limit_storage.clear()
