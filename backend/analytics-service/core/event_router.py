"""
Event Router
Routes and enriches events from various services to analytics service
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from shared.config.redis import analytics_buffer, RedisConfig
from shared.schemas.analytics import AnalyticsEventSchema, EventType
from shared.utils.event_validator import event_validator

logger = structlog.get_logger()


class EventRouter:
    """Routes events from various services to analytics service"""
    
    def __init__(self):
        self.redis_sync = RedisConfig.get_sync_connection()
    
    async def route_event(
        self,
        event_data: Dict[str, Any],
        source_service: str = "unknown"
    ) -> bool:
        """
        Route event to analytics service
        
        Args:
            event_data: Event data dictionary
            source_service: Source service name (e.g., "search", "recommendation")
            
        Returns:
            True if event was routed successfully, False otherwise
        """
        try:
            # Validate event
            validation_result = event_validator.validate_event(event_data)
            
            if not validation_result.is_valid:
                logger.warning(
                    "Event validation failed",
                    errors=validation_result.errors,
                    source_service=source_service
                )
                return False
            
            # Get sanitized event
            event = validation_result.sanitized_event
            if not event:
                return False
            
            # Enrich event with context
            enriched_event = await self._enrich_event(event.dict(), source_service)
            
            # Route to analytics service via Redis buffer
            success = analytics_buffer.buffer_event(
                enriched_event,
                check_duplicate=True,
                check_rate_limit=True
            )
            
            if success:
                logger.debug(
                    "Event routed successfully",
                    event_id=enriched_event.get('event_id'),
                    event_type=enriched_event.get('event_type'),
                    source_service=source_service
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Error routing event",
                error=str(e),
                source_service=source_service
            )
            return False
    
    async def _enrich_event(
        self,
        event_data: Dict[str, Any],
        source_service: str
    ) -> Dict[str, Any]:
        """
        Enrich event with additional context
        
        Args:
            event_data: Event data dictionary
            source_service: Source service name
            
        Returns:
            Enriched event data dictionary
        """
        enriched = event_data.copy()
        
        # Add source service metadata
        if 'properties' not in enriched:
            enriched['properties'] = {}
        
        if not isinstance(enriched['properties'], dict):
            enriched['properties'] = {}
        
        enriched['properties']['source_service'] = source_service
        enriched['properties']['routed_at'] = datetime.utcnow().isoformat()
        
        # Ensure required fields are present
        if 'timestamp' not in enriched or not enriched['timestamp']:
            enriched['timestamp'] = datetime.utcnow()
        
        if 'event_id' not in enriched or not enriched['event_id']:
            import uuid
            enriched['event_id'] = str(uuid.uuid4())
        
        return enriched
    
    async def route_search_event(
        self,
        merchant_id: int,
        event_type: str,
        session_id: str,
        user_id: Optional[int] = None,
        product_id: Optional[int] = None,
        query: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Route search service event to analytics
        
        Args:
            merchant_id: Merchant ID
            event_type: Event type (e.g., "search", "product_view", "search_click")
            session_id: Session identifier
            user_id: Optional user ID
            product_id: Optional product ID
            query: Optional search query
            additional_data: Additional event data
            
        Returns:
            True if event was routed successfully
        """
        event_data = {
            'merchant_id': merchant_id,
            'event_type': event_type,
            'session_id': session_id,
            'user_id': user_id,
            'product_id': product_id,
            'properties': additional_data or {}
        }
        
        if query:
            event_data['properties']['query'] = query
        
        return await self.route_event(event_data, source_service="search")
    
    async def route_recommendation_event(
        self,
        merchant_id: int,
        event_type: str,
        session_id: str,
        user_id: Optional[int] = None,
        product_id: Optional[int] = None,
        recommendation_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Route recommendation service event to analytics
        
        Args:
            merchant_id: Merchant ID
            event_type: Event type (e.g., "recommendation_click")
            session_id: Session identifier
            user_id: Optional user ID
            product_id: Optional product ID
            recommendation_id: Optional recommendation ID
            additional_data: Additional event data
            
        Returns:
            True if event was routed successfully
        """
        event_data = {
            'merchant_id': merchant_id,
            'event_type': event_type,
            'session_id': session_id,
            'user_id': user_id,
            'product_id': product_id,
            'properties': additional_data or {}
        }
        
        if recommendation_id:
            event_data['properties']['recommendation_id'] = recommendation_id
        
        return await self.route_event(event_data, source_service="recommendation")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            queue_length = analytics_buffer.get_queue_length()
            return {
                'queue_length': queue_length,
                'status': 'healthy' if queue_length < 10000 else 'warning'
            }
        except Exception as e:
            logger.error("Error getting queue stats", error=str(e))
            return {
                'queue_length': 0,
                'status': 'error'
            }


# Global event router instance
event_router = EventRouter()

