"""
AI Product Discovery Suite - Search Service Event Publisher

Publishes search query events to Redis pub/sub for analytics service consumption.
Implements auto-tracking for search queries (zero manual calls required).

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import structlog
import asyncio

from shared.config.redis import get_async_redis_client

logger = structlog.get_logger()


class EventPublisher:
    """Event publisher for Redis pub/sub"""
    
    # Redis channel for analytics events
    ANALYTICS_CHANNEL = "analytics:search_query"
    
    def __init__(self):
        self.redis_client = None
        self._initialized = False
    
    async def _ensure_redis(self):
        """Ensure Redis client is initialized"""
        if not self._initialized:
            self.redis_client = await get_async_redis_client()
            self._initialized = True
    
    async def publish_search_query_event(
        self,
        merchant_id: int,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        results: Optional[List[Dict]] = None
    ) -> bool:
        """
        Publish search query event to Redis pub/sub for analytics service
        
        Args:
            merchant_id: Merchant ID
            query: Search query string
            user_id: Optional user ID
            session_id: Optional session ID
            results: Optional search results
            
        Returns:
            True if event was published successfully, False otherwise
        """
        try:
            await self._ensure_redis()
            
            # Build event data
            event_data = {
                "event_type": "search_query",
                "merchant_id": merchant_id,
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
                "results_count": len(results) if results else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish to Redis channel (non-blocking, fire-and-forget)
            # Use asyncio.create_task to avoid blocking the search response
            asyncio.create_task(self._publish_async(event_data))
            
            logger.debug(
                "Search query event queued for publishing",
                merchant_id=merchant_id,
                query=query,
                channel=self.ANALYTICS_CHANNEL
            )
            
            return True
            
        except Exception as e:
            # Don't fail search if event publishing fails
            logger.warning(
                "Failed to publish search query event",
                error=str(e),
                merchant_id=merchant_id,
                query=query
            )
            return False
    
    async def _publish_async(self, event_data: Dict[str, Any]) -> None:
        """Publish event to Redis channel asynchronously"""
        try:
            await self._ensure_redis()
            
            # Serialize event data
            message = json.dumps(event_data)
            
            # Publish to Redis channel
            subscribers = await self.redis_client.publish(self.ANALYTICS_CHANNEL, message)
            
            logger.debug(
                "Search query event published",
                channel=self.ANALYTICS_CHANNEL,
                subscribers=subscribers,
                merchant_id=event_data.get('merchant_id')
            )
            
        except Exception as e:
            logger.error(
                "Error publishing event to Redis",
                error=str(e),
                channel=self.ANALYTICS_CHANNEL
            )
            # Don't raise - this is fire-and-forget
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False


# Global event publisher instance
event_publisher = EventPublisher()

