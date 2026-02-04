"""
AI Product Discovery Suite - Event Processor

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.base import AsyncSessionLocal
from shared.models.analytics import AnalyticsEvent
# from shared.models import Product # Removed
from shared.schemas.analytics import AnalyticsEventSchema, EventType
from shared.utils.event_validator import event_validator
from shared.config.redis import analytics_buffer

from core.event_enricher import event_enricher
from core.session_tracker import session_tracker

logger = structlog.get_logger()


class EventProcessor:
    """Event processor for analytics"""
    
    def __init__(self):
        self.initialized = False
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    async def initialize(self):
        """Initialize the event processor"""
        logger.info("Initializing event processor")
        self.initialized = True
    
    async def cleanup(self):
        """Clean up the event processor"""
        logger.info("Cleaning up event processor")
        self.initialized = False
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Main event processing method
        
        Validates, enriches, stores, and queues event for aggregation
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event was processed successfully
        """
        try:
            # Validate event
            validation_result = self.validate_event(event_data)
            if not validation_result:
                return False
            
            # Enrich event with context
            enriched_event = await self.enrich_event(event_data)
            if not enriched_event:
                return False
            
            # Store event in database
            stored = await self.store_event(enriched_event)
            if not stored:
                logger.warning("Failed to store event", event_id=enriched_event.get('event_id'))
                # Continue processing even if storage fails (event is still queued)
            
            # Queue for aggregation
            queued = await self.queue_for_aggregation(enriched_event)
            if not queued:
                logger.warning("Failed to queue event for aggregation", event_id=enriched_event.get('event_id'))
            
            # Update session tracking
            try:
                merchant_id = enriched_event.get('merchant_id')
                session_id = enriched_event.get('session_id')
                event_type = enriched_event.get('event_type')
                
                if merchant_id and session_id:
                    await session_tracker.update_session(
                        merchant_id=merchant_id,
                        session_id=session_id,
                        event_type=event_type,
                        event_data=enriched_event
                    )
            except Exception as e:
                logger.warning("Error updating session", error=str(e))
                # Don't fail event processing if session update fails
            
            return True
            
        except Exception as e:
            logger.error("Error processing event", error=str(e), exc_info=True)
            await self.handle_errors(event_data, e)
            return False
    
    def validate_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate event data
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            Validated event data dictionary or None if validation fails
        """
        try:
            validation_result = event_validator.validate_event(event_data)
            
            if not validation_result.is_valid:
                logger.warning(
                    "Event validation failed",
                    errors=validation_result.errors,
                    event_type=event_data.get('event_type')
                )
                return None
            
            if not validation_result.sanitized_event:
                logger.warning("Event validation failed: no sanitized event", event_type=event_data.get('event_type'))
                return None
            
            return validation_result.sanitized_event.dict()
            
        except Exception as e:
            logger.error("Error validating event", error=str(e))
            return None
    
    async def enrich_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enrich event with additional context
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            Enriched event data dictionary or None if enrichment fails
        """
        try:
            enriched = await event_enricher.enrich_event(event_data)
            
            # Ensure required fields are present
            if 'timestamp' not in enriched or not enriched['timestamp']:
                enriched['timestamp'] = datetime.utcnow()
            
            if isinstance(enriched.get('timestamp'), datetime):
                enriched['timestamp'] = enriched['timestamp']
            elif isinstance(enriched.get('timestamp'), str):
                # Parse ISO format string
                enriched['timestamp'] = datetime.fromisoformat(enriched['timestamp'].replace('Z', '+00:00'))
            else:
                enriched['timestamp'] = datetime.utcnow()
            
            return enriched
            
        except Exception as e:
            logger.error("Error enriching event", error=str(e))
            return None
    
    async def store_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Store event in database
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event was stored successfully
        """
        db_session = AsyncSessionLocal()
        retry_count = 0
        
        try:
            while retry_count < self.max_retries:
                try:
                    # Resolve user_id to integer if possible for foreign key relationship
                    user_id_str = event_data.get('user_id')
                    user_id_int = None

                    if user_id_str is not None:
                        # Try to resolve string user_id to integer user_id
                        if isinstance(user_id_str, int):
                            user_id_int = user_id_str
                        elif isinstance(user_id_str, str):
                            # Check if it's a numeric string (legacy integer ID)
                            try:
                                user_id_int = int(user_id_str)
                            except ValueError:
                                # It's a string user ID, try to find matching user record
                                # This is a simplified approach - in production you'd want more sophisticated resolution
                                # For now, we'll keep it as string and not resolve to int
                                pass

                    # Product validation removed - analytics service doesn't validate product existence
                    # Products are managed externally (ElasticSearch/Qdrant), so we accept any product_id
                    product_id = event_data.get('product_id')
                    
                    # Create AnalyticsEvent model instance
                    analytics_event = AnalyticsEvent(
                        event_id=event_data.get('event_id'),
                        merchant_id=event_data.get('merchant_id'),
                        event_type=event_data.get('event_type'),
                        user_id=str(user_id_str) if user_id_str is not None else None,  # Store as string
                        session_id=event_data.get('session_id'),
                        product_id=product_id,  # Use verified product_id (may be None)
                        platform=event_data.get('platform'),
                        device_type=event_data.get('device_type'),
                        ip_address=event_data.get('ip_address'),
                        user_agent=event_data.get('user_agent'),
                        referrer=event_data.get('referrer'),
                        revenue=event_data.get('revenue'),
                        experiment_id=event_data.get('experiment_id'),
                        variant_id=event_data.get('variant_id'),
                        properties=event_data.get('properties', {}),
                        timestamp=event_data.get('timestamp', datetime.utcnow())
                    )
                    
                    db_session.add(analytics_event)
                    await db_session.commit()
                    
                    logger.debug("Event stored in database", event_id=event_data.get('event_id'))
                    return True
                    
                except Exception as e:
                    retry_count += 1
                    await db_session.rollback()
                    
                    if retry_count >= self.max_retries:
                        logger.error(
                            "Failed to store event after retries",
                            error=str(e),
                            event_id=event_data.get('event_id'),
                            retry_count=retry_count
                        )
                        return False
                    
                    logger.warning(
                        "Error storing event, retrying",
                        error=str(e),
                        event_id=event_data.get('event_id'),
                        retry_count=retry_count
                    )
                    # Wait before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(self.retry_delay * retry_count)
            
            return False
        finally:
            await db_session.close()
    
    async def queue_for_aggregation(self, event_data: Dict[str, Any]) -> bool:
        """
        Queue event for batch aggregation processing
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event was queued successfully
        """
        try:
            # Queue event to Redis buffer for batch processing
            success = analytics_buffer.buffer_event(
                event_data,
                check_duplicate=False,  # Already checked during validation
                check_rate_limit=False  # Already checked at API level
            )
            
            if success:
                logger.debug("Event queued for aggregation", event_id=event_data.get('event_id'))
            
            return success
            
        except Exception as e:
            logger.error("Error queueing event for aggregation", error=str(e))
            return False
    
    async def handle_errors(self, event_data: Dict[str, Any], error: Exception) -> None:
        """
        Handle errors during event processing
        
        Args:
            event_data: Event data dictionary
            error: Exception that occurred
        """
        try:
            logger.error(
                "Event processing error",
                error=str(error),
                error_type=type(error).__name__,
                event_id=event_data.get('event_id'),
                event_type=event_data.get('event_type'),
                merchant_id=event_data.get('merchant_id')
            )
            
            # TODO: Could implement error queue for manual review/reprocessing
            # For now, just log the error
            
        except Exception as e:
            logger.error("Error in error handler", error=str(e))
