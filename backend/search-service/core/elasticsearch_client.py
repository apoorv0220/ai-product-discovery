"""
AI Product Discovery Suite - Elasticsearch Manager

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Any, Dict, Optional
import asyncio
import structlog

from shared.config.settings import SearchServiceSettings
from shared.monitoring.metrics import (
    record_elasticsearch_query,
    elasticsearch_errors_total,
)

logger = structlog.get_logger()

try:
    from elasticsearch import AsyncElasticsearch, ApiError  # type: ignore
    from elasticsearch.helpers import async_bulk  # type: ignore
except Exception:  # pragma: no cover
    AsyncElasticsearch = None  # type: ignore
    ApiError = Exception  # type: ignore
    async_bulk = None  # type: ignore


class ElasticsearchManager:
    """Elasticsearch client manager with auth, timeouts, and retry/backoff."""

    def __init__(self, settings: Optional[SearchServiceSettings] = None):
        self.settings = settings or SearchServiceSettings()
        self.client: Optional[AsyncElasticsearch] = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the Elasticsearch client and verify cluster health."""
        logger.info("Initializing Elasticsearch manager", url=self.settings.ELASTICSEARCH_URL)

        if AsyncElasticsearch is None:
            raise RuntimeError("Elasticsearch client library is not installed")

        http_auth = None
        if self.settings.ELASTICSEARCH_USERNAME and self.settings.ELASTICSEARCH_PASSWORD:
            http_auth = (self.settings.ELASTICSEARCH_USERNAME, self.settings.ELASTICSEARCH_PASSWORD)

        self.client = AsyncElasticsearch(
            hosts=[self.settings.ELASTICSEARCH_URL],
            basic_auth=http_auth,
            request_timeout=self.settings.ELASTICSEARCH_REQUEST_TIMEOUT,
            retry_on_timeout=self.settings.ELASTICSEARCH_RETRY_ON_TIMEOUT,
            max_retries=self.settings.ELASTICSEARCH_MAX_RETRIES,
        )

        # Verify connection/health
        await self.health_check()
        self.initialized = True
        logger.info("Elasticsearch manager initialized")

    async def close(self) -> None:
        """Close the Elasticsearch client."""
        if self.client is not None:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning("Error closing Elasticsearch client", error=str(e))
        self.initialized = False
        logger.info("Elasticsearch manager closed")

    async def health_check(self) -> Dict[str, Any]:
        """Return cluster health; raises if unreachable."""
        assert self.client is not None, "Elasticsearch client not initialized"
        try:
            start = asyncio.get_event_loop().time()
            health = await self.client.cluster.health()
            duration = asyncio.get_event_loop().time() - start
            record_elasticsearch_query("health", duration, "search-service")
            logger.info("Elasticsearch health", status=health.get("status"))
            return health
        except Exception as e:
            elasticsearch_errors_total.labels(error_type="health", service="search-service").inc()
            logger.error("Elasticsearch health check failed", error=str(e))
            raise

    def get_index_name(self, merchant_id: int, prefix: str = "discovery_products") -> str:
        """Generate normalized per-merchant index name."""
        return f"{prefix}_m{int(merchant_id)}".lower()

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute an ES call with simple exponential backoff."""
        retries = max(0, int(self.settings.ELASTICSEARCH_MAX_RETRIES))
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:  # ApiError or Timeout
                last_exc = e
                elasticsearch_errors_total.labels(error_type=type(e).__name__, service="search-service").inc()
                if attempt == retries:
                    break
                backoff = 2 ** attempt
                logger.warning("Elasticsearch call failed, retrying", attempt=attempt + 1, backoff_s=backoff)
                await asyncio.sleep(backoff)
                attempt += 1
        assert last_exc is not None
        raise last_exc

    async def ensure_index(self, merchant_id: int, settings: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
        """Create index for merchant if it doesn't exist (idempotent)."""
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)

        exists = await self._execute_with_retry(self.client.indices.exists, index=index)
        if exists:
            return True

        body = {"settings": settings, "mappings": mapping}
        await self._execute_with_retry(self.client.indices.create, index=index, body=body)
        logger.info("Created Elasticsearch index", index=index, merchant_id=merchant_id)
        return True

    async def delete_index(self, merchant_id: int) -> bool:
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)
        exists = await self._execute_with_retry(self.client.indices.exists, index=index)
        if not exists:
            return True
        await self._execute_with_retry(self.client.indices.delete, index=index)
        logger.info("Deleted Elasticsearch index", index=index, merchant_id=merchant_id)
        return True

    async def refresh_index(self, merchant_id: int) -> bool:
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)
        await self._execute_with_retry(self.client.indices.refresh, index=index)
        return True

    async def get_index_stats(self, merchant_id: int) -> Dict[str, Any]:
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)
        return await self._execute_with_retry(self.client.indices.stats, index=index)

    async def search(self, merchant_id: int, query: Dict[str, Any], from_: int, size: int) -> Dict[str, Any]:
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)
        start = asyncio.get_event_loop().time()
        result = await self._execute_with_retry(self.client.search, index=index, body=query, from_=from_, size=size)
        duration = asyncio.get_event_loop().time() - start
        record_elasticsearch_query("search", duration, "search-service")
        return result

    async def bulk(self, actions) -> Dict[str, Any]:
        assert self.client is not None and async_bulk is not None, "Elasticsearch client not initialized"
        return await async_bulk(self.client, actions)