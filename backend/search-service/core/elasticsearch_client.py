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
            [self.settings.ELASTICSEARCH_URL],
            http_auth=http_auth,
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )

        # Verify cluster health
        try:
            health = await self.client.cluster.health(wait_for_status="yellow", timeout="10s")
            logger.info("Elasticsearch cluster health verified", status=health.get("status"))
        except Exception as e:
            logger.warning("Elasticsearch cluster health check failed", error=str(e))
            # Don't fail initialization if health check fails - cluster might be starting up

        self.initialized = True

    async def close(self) -> None:
        """Close the Elasticsearch client."""
        if self.client:
                await self.client.close()
        self.initialized = False

    def get_index_name(self, merchant_id: int) -> str:
        """Get the index name for a merchant."""
        return f"discovery_products_m{merchant_id}"

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute an Elasticsearch operation with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except ApiError as e:
                elasticsearch_errors_total.labels(
                    error_type=type(e).__name__,
                    service="search-service"
                ).inc()
                
                if attempt == max_retries - 1:
                    logger.error("Elasticsearch operation failed after retries",
                               error=str(e),
                               error_type=type(e).__name__,
                               attempts=max_retries)
                    raise
                
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning("Elasticsearch operation failed, retrying",
                             error=str(e),
                             attempt=attempt + 1,
                             wait_time=wait_time)
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error("Unexpected error in Elasticsearch operation",
                           error=str(e),
                           error_type=type(e).__name__)
                raise

    async def search(self, merchant_id: int, query: Dict[str, Any], from_: int, size: int) -> Dict[str, Any]:
        assert self.client is not None, "Elasticsearch client not initialized"
        index = self.get_index_name(merchant_id)
        start = asyncio.get_event_loop().time()
        
        # Query builder already includes from and size in the query body
        # But we need to ensure they match the passed parameters (override if needed)
        query_with_pagination = query.copy()
        query_with_pagination['from'] = from_
        query_with_pagination['size'] = size
        
        # Use only body parameter, not separate from_/size params to avoid "multiple values" error
        result = await self._execute_with_retry(self.client.search, index=index, body=query_with_pagination)
        duration = asyncio.get_event_loop().time() - start
        record_elasticsearch_query("search", duration, "search-service")
        
        # Convert Elasticsearch response to dict if it's an ObjectApiResponse
        if hasattr(result, 'body'):
            return result.body
        elif hasattr(result, 'to_dict'):
            return result.to_dict()
        elif isinstance(result, dict):
            return result
        else:
            # Fallback: try to convert to dict
            import json
            try:
                return json.loads(json.dumps(result, default=str))
            except:
                return dict(result) if hasattr(result, '__dict__') else result

    async def bulk(self, actions) -> Dict[str, Any]:
        assert self.client is not None and async_bulk is not None, "Elasticsearch client not initialized"
        return await async_bulk(self.client, actions)
