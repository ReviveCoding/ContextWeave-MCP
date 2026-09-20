"""Separate metadata, context, and result caches with authorization and freshness binding."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class CacheIdentity:
    tenant_id: str
    account_ids: tuple[str, ...]
    scopes: tuple[str, ...]
    source_version: str
    schema_version: str
    metric_version: str
    data_watermark: int
    sensitivity: str
    cache_scope: str


@dataclass
class CacheEntry:
    identity: CacheIdentity
    value: Any
    valid_from: float
    valid_until: float


class GovernedCache:
    def __init__(self, system: str) -> None:
        if system not in {"KA", "KB", "KC"}:
            raise ValueError("cache system must be KA, KB, or KC")
        self.system = system
        self._entries: dict[str, CacheEntry] = {}

    def put(self, key: str, identity: CacheIdentity, value: Any, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
        now = time()
        self._entries[key] = CacheEntry(identity, value, now, now + ttl_seconds)

    def get(self, key: str, identity: CacheIdentity, now: float | None = None) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        at = time() if now is None else now
        if not (entry.valid_from <= at < entry.valid_until):
            return None
        # Full identity match prevents cross-tenant, revoked-scope, version, and watermark reuse.
        if entry.identity != identity:
            return None
        return entry.value
