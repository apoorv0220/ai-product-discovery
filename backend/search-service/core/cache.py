"""
Redis cache-aside layer for search and autocomplete.
"""

from typing import Dict, Optional
import json
import re
import hashlib

import redis.asyncio as redis_async

from shared.monitoring.metrics import record_cache_operation


class SearchCache:
    CACHE_VERSION = "v1"
    SEARCH_TTL = 300
    AUTOCOMPLETE_TTL = 300

    def __init__(self, redis_client: redis_async.Redis):
        self.redis = redis_client

    def generate_cache_key(self, cache_type: str, merchant_id: int, query: str, filters: Optional[Dict] = None) -> str:
        normalized_query = self._normalize_query(query)
        filter_hash = self._hash_filters(filters) if filters else ""
        return f"{cache_type}:{self.CACHE_VERSION}:m{merchant_id}:{normalized_query}:{filter_hash}"

    async def get_cached(self, key: str) -> Optional[Dict]:
        data = await self.redis.get(key)
        if data:
            record_cache_operation("get", "hit", "search-service")
            return json.loads(data)
        record_cache_operation("get", "miss", "search-service")
        return None

    async def cache_result(self, key: str, data: Dict, ttl: int) -> None:
        await self.redis.setex(key, ttl, json.dumps(data))
        record_cache_operation("set", "success", "search-service")

    async def invalidate_merchant_cache(self, merchant_id: int) -> None:
        # Simple approach for Phase 1: delete all merchant keys
        pattern = f"*:{self.CACHE_VERSION}:m{merchant_id}:*"
        async for key in self._scan_iter(pattern):
            await self.redis.delete(key)

    async def _scan_iter(self, pattern: str):
        cursor = b"0"
        while cursor:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            for k in keys:
                yield k

    def _normalize_query(self, q: str) -> str:
        q = (q or "").strip().lower()
        q = re.sub(r"\s+", " ", q)
        return q

    def _hash_filters(self, filters: Dict) -> str:
        raw = json.dumps(filters, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]



