"""
Centralized in-memory cache with TTL support.

All services use this singleton instead of maintaining local dicts.
Keys are namespaced strings (e.g. "stock:df:RELIANCE.NS", "analytics:report").
"""

from __future__ import annotations

import time
from typing import Any, Optional


class CacheManager:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.time() + ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        keys = [k for k in list(self._store) if k.startswith(prefix)]
        for k in keys:
            self._store.pop(k, None)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def size(self) -> int:
        return len(self._store)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        return [k for k in self._store if k.startswith(prefix)]


# Module-level singleton — import this everywhere
cache = CacheManager()
