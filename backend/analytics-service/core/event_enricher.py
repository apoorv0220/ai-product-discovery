"""
Event Enricher
Enriches events with additional context (merchant, user, session, geographic, device)
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.models import Merchant, Product
from shared.database.base import AsyncSessionLocal

logger = structlog.get_logger()


class EventEnricher:
    """Enriches events with additional context"""
    
    def __init__(self):
        pass
    
    async def enrich_event(
        self,
        event_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Enrich event with additional context
        
        Args:
            event_data: Event data dictionary
            db_session: Optional database session (if None, creates new one)
            
        Returns:
            Enriched event data dictionary
        """
        enriched = event_data.copy()
        
        # Use provided session or create new one
        use_external_session = db_session is not None
        if not db_session:
            db_session = AsyncSessionLocal()
        
        try:
            # Add merchant context
            enriched = await self._add_merchant_context(enriched, db_session)
            
            # User context enrichment disabled - plugin architecture uses external user_ids
            # User data is not stored locally, only behavioral analytics
            
            # Add product context (if product_id provided)
            if enriched.get('product_id'):
                enriched = await self._add_product_context(enriched, db_session)
            
            # Add geographic context (from IP address)
            enriched = await self._add_geographic_context(enriched)
            
            # Add device context (from user agent)
            enriched = await self._add_device_context(enriched)
            
            return enriched
            
        except Exception as e:
            logger.error("Error enriching event", error=str(e))
            # Return original event data if enrichment fails
            return event_data
        finally:
            # Only close session if we created it
            if not use_external_session:
                await db_session.close()
    
    async def _add_merchant_context(
        self,
        event_data: Dict[str, Any],
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Add merchant context to event"""
        merchant_id = event_data.get('merchant_id')
        if not merchant_id:
            return event_data
        
        try:
            result = await db_session.execute(
                select(Merchant).where(Merchant.id == merchant_id)
            )
            merchant = result.scalar_one_or_none()
            
            if merchant:
                if 'properties' not in event_data:
                    event_data['properties'] = {}
                if not isinstance(event_data['properties'], dict):
                    event_data['properties'] = {}
                
                event_data['properties']['merchant_name'] = merchant.name
                event_data['properties']['merchant_tier'] = merchant.tier
                event_data['properties']['merchant_status'] = merchant.status
        except Exception as e:
            logger.warning("Error adding merchant context", error=str(e), merchant_id=merchant_id)
        
        return event_data
    
    
    async def _add_product_context(
        self,
        event_data: Dict[str, Any],
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Add product context to event

        NOTE: Product enrichment is currently disabled since products are stored
        in ElasticSearch/Qdrant, not PostgreSQL. This method returns the event
        data unchanged.
        """
        product_id = event_data.get('product_id')
        if not product_id:
            return event_data

        # TODO: Implement product enrichment from ElasticSearch when needed
        # For now, products are not stored in PostgreSQL, so we skip enrichment
        logger.debug("Skipping product enrichment - products not stored in PostgreSQL", product_id=product_id)

        return event_data
    
    async def _add_geographic_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add geographic context from IP address"""
        ip_address = event_data.get('ip_address')
        if not ip_address:
            return event_data
        
        # TODO: Implement IP geolocation lookup (e.g., using MaxMind GeoIP2)
        # For now, just store the IP address
        if 'properties' not in event_data:
            event_data['properties'] = {}
        if not isinstance(event_data['properties'], dict):
            event_data['properties'] = {}
        
        # Placeholder for geographic data
        # event_data['properties']['country'] = ...
        # event_data['properties']['region'] = ...
        # event_data['properties']['city'] = ...
        
        return event_data
    
    async def _add_device_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add device context from user agent"""
        user_agent = event_data.get('user_agent')
        if not user_agent:
            return event_data
        
        # Basic device/browser detection from user agent
        # TODO: Use a library like user-agents for better detection
        if 'properties' not in event_data:
            event_data['properties'] = {}
        if not isinstance(event_data['properties'], dict):
            event_data['properties'] = {}
        
        user_agent_lower = user_agent.lower()
        
        # Basic browser detection
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            event_data['properties']['browser'] = 'Chrome'
        elif 'firefox' in user_agent_lower:
            event_data['properties']['browser'] = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            event_data['properties']['browser'] = 'Safari'
        elif 'edg' in user_agent_lower:
            event_data['properties']['browser'] = 'Edge'
        else:
            event_data['properties']['browser'] = 'Unknown'
        
        # OS detection
        if 'windows' in user_agent_lower:
            event_data['properties']['os'] = 'Windows'
        elif 'mac' in user_agent_lower or 'darwin' in user_agent_lower:
            event_data['properties']['os'] = 'macOS'
        elif 'linux' in user_agent_lower:
            event_data['properties']['os'] = 'Linux'
        elif 'android' in user_agent_lower:
            event_data['properties']['os'] = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            event_data['properties']['os'] = 'iOS'
        else:
            event_data['properties']['os'] = 'Unknown'
        
        return event_data


# Global event enricher instance
event_enricher = EventEnricher()

