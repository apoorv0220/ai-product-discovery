"""
AI Product Discovery Suite - Analytics Service Event Subscriber

Subscribes to Redis pub/sub channels for auto-tracked events (e.g., search queries).
Processes events asynchronously via EventProcessor.

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import json
import asyncio
from typing import Optional
from datetime import datetime
import structlog
import uuid

from shared.config.redis import get_async_redis_client
from core.processor import EventProcessor

logger = structlog.get_logger()


class EventSubscriber:
    """Event subscriber for Redis pub/sub"""
    
    # Redis channel for search query events
    SEARCH_QUERY_CHANNEL = "analytics:search_query"
    
    def __init__(self, event_processor: EventProcessor):
        self.event_processor = event_processor
        self.redis_client = None
        self.pubsub = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start subscribing to Redis channels"""
        try:
            self.redis_client = await get_async_redis_client()
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to search query channel
            await self.pubsub.subscribe(self.SEARCH_QUERY_CHANNEL)
            
            logger.info(
                "Event subscriber started",
                channel=self.SEARCH_QUERY_CHANNEL
            )
            
            # Start background task to listen for messages
            self._running = True
            self._task = asyncio.create_task(self._listen_messages())
            
        except Exception as e:
            logger.error("Failed to start event subscriber", error=str(e))
            raise
    
    async def stop(self):
        """Stop subscribing and cleanup"""
        try:
            self._running = False
            
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            
            if self.pubsub:
                await self.pubsub.unsubscribe(self.SEARCH_QUERY_CHANNEL)
                await self.pubsub.close()
            
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("Event subscriber stopped")
            
        except Exception as e:
            logger.error("Error stopping event subscriber", error=str(e))
    
    async def _listen_messages(self):
        """Listen for messages from Redis pub/sub"""
        try:
            while self._running:
                try:
                    # Get message with timeout to allow checking _running flag
                    message = await asyncio.wait_for(
                        self.pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0
                    )
                    
                    if message:
                        await self._process_message(message)
                        
                except asyncio.TimeoutError:
                    # Timeout is expected, continue listening
                    continue
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    # Continue listening even if one message fails
                    continue
                    
        except asyncio.CancelledError:
            logger.info("Event subscriber listening task cancelled")
        except Exception as e:
            logger.error("Error in message listener", error=str(e))
    
    async def _process_message(self, message):
        """Process a message from Redis pub/sub"""
        try:
            if message['type'] != 'message':
                return
            
            channel = message['channel']
            data = message['data']
            
            # Parse JSON data
            try:
                event_data = json.loads(data)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse event data", error=str(e), channel=channel)
                return
            
            # Convert to analytics event format
            analytics_event = self._convert_to_analytics_event(event_data, channel)
            
            if analytics_event:
                # Process event via EventProcessor
                await self.event_processor.process_event(analytics_event)
                
                logger.debug(
                    "Event processed from Redis",
                    channel=channel,
                    event_type=analytics_event.get('event_type'),
                    merchant_id=analytics_event.get('merchant_id')
                )
            
        except Exception as e:
            logger.error("Error processing message", error=str(e), exc_info=True)
    
    def _convert_to_analytics_event(self, event_data: dict, channel: str) -> Optional[dict]:
        """
        Convert Redis pub/sub event to analytics event format
        
        Args:
            event_data: Event data from Redis
            channel: Redis channel name
            
        Returns:
            Analytics event dictionary or None if conversion fails
        """
        try:
            # Map channel to event type
            if channel == self.SEARCH_QUERY_CHANNEL:
                event_type = "search_query"
            else:
                logger.warning("Unknown channel", channel=channel)
                return None
            
            # Build analytics event
            analytics_event = {
                "event_type": event_type,
                "merchant_id": event_data.get("merchant_id"),
                "user_id": event_data.get("user_id"),
                "session_id": event_data.get("session_id"),
                "properties": {
                    "query": event_data.get("query"),
                    "results_count": event_data.get("results_count", 0)
                },
                "timestamp": datetime.utcnow(),
                "event_id": str(uuid.uuid4())
            }
            
            # Parse timestamp if provided
            if "timestamp" in event_data:
                try:
                    analytics_event["timestamp"] = datetime.fromisoformat(
                        event_data["timestamp"].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    pass  # Use current timestamp if parsing fails
            
            return analytics_event
            
        except Exception as e:
            logger.error("Error converting event", error=str(e))
            return None

