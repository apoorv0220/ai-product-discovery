"""
Event Enricher
Enriches events with additional context (merchant, user, session, geographic, device)
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog
import hashlib
import ipaddress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.models import Merchant
from shared.database.base import AsyncSessionLocal
from shared.config.redis import CacheManager

logger = structlog.get_logger()

# Try to import optional dependencies
try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.warning("geoip2 not available, using fallback geolocation")

try:
    from user_agents import parse as parse_user_agent
    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False
    logger.warning("user-agents not available, using basic device detection")


class EventEnricher:
    """Enriches events with additional context"""
    
    def __init__(self):
        self.cache = CacheManager()
        self.geoip_reader = None
        self._init_geoip()
    
    def _init_geoip(self):
        """Initialize GeoIP2 reader if available"""
        if not GEOIP2_AVAILABLE:
            return
        
        try:
            # Try to load GeoIP2 database (if available)
            # In production, you would download MaxMind GeoLite2 database
            # For now, we'll use a fallback approach with ipapi.co or similar
            pass
        except Exception as e:
            logger.warning("Failed to initialize GeoIP2", error=str(e))
    
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
            
            # Add event correlation (multi-touch attribution)
            enriched = await self._add_event_correlation(enriched)
            
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
        ip_address_str = event_data.get('ip_address')
        if not ip_address_str:
            return event_data
        
        # Check cache first (24h TTL)
        cache_key = f"geoip:{ip_address_str}"
        cached_geo = await self.cache.aget(cache_key)
        if cached_geo:
            if 'properties' not in event_data:
                event_data['properties'] = {}
            if not isinstance(event_data['properties'], dict):
                event_data['properties'] = {}
            event_data['properties'].update(cached_geo)
            return event_data
        
        # Initialize properties dict
        if 'properties' not in event_data:
            event_data['properties'] = {}
        if not isinstance(event_data['properties'], dict):
            event_data['properties'] = {}
        
        geo_data = {}
        
        try:
            # Check if IP is private/local
            ip = ipaddress.ip_address(ip_address_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                geo_data['country'] = None
                geo_data['region'] = None
                geo_data['city'] = None
                geo_data['timezone'] = None
                geo_data['is_private'] = True
            else:
                # Try GeoIP2 first if available
                if GEOIP2_AVAILABLE and self.geoip_reader:
                    try:
                        response = self.geoip_reader.city(ip_address_str)
                        geo_data['country'] = response.country.iso_code
                        geo_data['country_name'] = response.country.name
                        geo_data['region'] = response.subdivisions.most_specific.iso_code if response.subdivisions else None
                        geo_data['region_name'] = response.subdivisions.most_specific.name if response.subdivisions else None
                        geo_data['city'] = response.city.name
                        geo_data['timezone'] = response.location.time_zone
                        geo_data['latitude'] = response.location.latitude
                        geo_data['longitude'] = response.location.longitude
                    except (geoip2.errors.AddressNotFoundError, ValueError):
                        # Fallback to API-based lookup
                        geo_data = await self._geolocate_via_api(ip_address_str)
                else:
                    # Fallback to API-based lookup (ipapi.co or similar)
                    geo_data = await self._geolocate_via_api(ip_address_str)
        except (ValueError, ipaddress.AddressValueError):
            # Invalid IP address
            logger.warning("Invalid IP address", ip_address=ip_address_str)
            geo_data['is_invalid'] = True
        except Exception as e:
            logger.warning("Error in geolocation", error=str(e), ip_address=ip_address_str)
            geo_data['error'] = str(e)
        
        # Cache the result (24h TTL)
        if geo_data:
            await self.cache.aset(cache_key, geo_data, 86400)  # 24 hours
        
        # Add to event properties
        event_data['properties'].update(geo_data)
        
        return event_data
    
    async def _geolocate_via_api(self, ip_address: str) -> Dict[str, Any]:
        """Fallback geolocation via API (ipapi.co or similar)"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Using ipapi.co free tier (no API key needed for basic usage)
                response = await client.get(f"https://ipapi.co/{ip_address}/json/")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'country': data.get('country_code'),
                        'country_name': data.get('country_name'),
                        'region': data.get('region_code'),
                        'region_name': data.get('region'),
                        'city': data.get('city'),
                        'timezone': data.get('timezone'),
                        'latitude': data.get('latitude'),
                        'longitude': data.get('longitude'),
                    }
        except Exception as e:
            logger.debug("API geolocation failed", error=str(e), ip_address=ip_address)
        
        return {}
    
    async def _add_device_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add device context from user agent"""
        user_agent = event_data.get('user_agent')
        if not user_agent:
            return event_data
        
        # Check cache first (1h TTL)
        cache_key = f"device_fp:{hashlib.md5(user_agent.encode()).hexdigest()}"
        cached_device = await self.cache.aget(cache_key)
        if cached_device:
            if 'properties' not in event_data:
                event_data['properties'] = {}
            if not isinstance(event_data['properties'], dict):
                event_data['properties'] = {}
            event_data['properties'].update(cached_device)
            return event_data
        
        # Initialize properties dict
        if 'properties' not in event_data:
            event_data['properties'] = {}
        if not isinstance(event_data['properties'], dict):
            event_data['properties'] = {}
        
        device_data = {}
        
        if USER_AGENTS_AVAILABLE:
            try:
                ua = parse_user_agent(user_agent)
                
                # Device type
                if ua.is_mobile:
                    device_data['device_type'] = 'mobile'
                elif ua.is_tablet:
                    device_data['device_type'] = 'tablet'
                else:
                    device_data['device_type'] = 'desktop'
                
                # Browser
                device_data['browser'] = ua.browser.family
                device_data['browser_version'] = f"{ua.browser.version_string}" if ua.browser.version_string else None
                
                # OS
                device_data['os'] = ua.os.family
                device_data['os_version'] = f"{ua.os.version_string}" if ua.os.version_string else None
                
                # Device
                device_data['device'] = ua.device.family if ua.device.family else None
                
            except Exception as e:
                logger.warning("Error parsing user agent", error=str(e))
                device_data = self._basic_device_detection(user_agent)
        else:
            device_data = self._basic_device_detection(user_agent)
        
        # Generate device fingerprint
        fingerprint_components = [
            user_agent,
            event_data.get('properties', {}).get('timezone', ''),
            event_data.get('properties', {}).get('screen_resolution', ''),
        ]
        fingerprint_string = '|'.join(str(c) for c in fingerprint_components if c)
        device_data['device_fingerprint'] = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
        
        # Cache the result (1h TTL)
        if device_data:
            await self.cache.aset(cache_key, device_data, 3600)  # 1 hour
        
        # Add to event properties
        event_data['properties'].update(device_data)
        
        return event_data
    
    def _basic_device_detection(self, user_agent: str) -> Dict[str, Any]:
        """Basic device detection fallback"""
        user_agent_lower = user_agent.lower()
        device_data = {}
        
        # Device type
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            device_data['device_type'] = 'mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            device_data['device_type'] = 'tablet'
        else:
            device_data['device_type'] = 'desktop'
        
        # Browser detection
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            device_data['browser'] = 'Chrome'
        elif 'firefox' in user_agent_lower:
            device_data['browser'] = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            device_data['browser'] = 'Safari'
        elif 'edg' in user_agent_lower:
            device_data['browser'] = 'Edge'
        else:
            device_data['browser'] = 'Unknown'
        
        # OS detection
        if 'windows' in user_agent_lower:
            device_data['os'] = 'Windows'
        elif 'mac' in user_agent_lower or 'darwin' in user_agent_lower:
            device_data['os'] = 'macOS'
        elif 'linux' in user_agent_lower:
            device_data['os'] = 'Linux'
        elif 'android' in user_agent_lower:
            device_data['os'] = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            device_data['os'] = 'iOS'
        else:
            device_data['os'] = 'Unknown'
        
        return device_data
    
    async def _add_event_correlation(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add multi-touch attribution tracking
        
        Tracks all touchpoints in user journey and weights them by recency and type
        """
        try:
            merchant_id = event_data.get('merchant_id')
            session_id = event_data.get('session_id')
            user_id = event_data.get('user_id')
            device_fingerprint = event_data.get('properties', {}).get('device_fingerprint')
            
            if not merchant_id or not session_id:
                return event_data
            
            # Get user journey to build attribution
            from core.session_tracker import session_tracker
            
            journey = await session_tracker.get_user_journey(
                merchant_id=merchant_id,
                device_fingerprint=device_fingerprint,
                user_id=user_id,
                limit=20  # Last 20 sessions
            )
            
            if not journey:
                return event_data
            
            # Build touchpoint sequence
            touchpoints = []
            for session in journey:
                session_events = session.get('journey', [])
                for event in session_events:
                    event_type = event.get('event_type')
                    if event_type in ['search', 'product_view', 'add_to_cart', 'purchase']:
                        touchpoint = {
                            'type': event_type,
                            'timestamp': event.get('timestamp'),
                            'session_id': session.get('session_id'),
                            'weight': self._calculate_touchpoint_weight(event_type, event.get('timestamp'))
                        }
                        touchpoints.append(touchpoint)
            
            # Sort by timestamp (most recent first)
            touchpoints.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Calculate attribution weights
            attribution = {
                'touchpoint_count': len(touchpoints),
                'first_touch': touchpoints[-1] if touchpoints else None,
                'last_touch': touchpoints[0] if touchpoints else None,
                'touchpoints': touchpoints[:10],  # Last 10 touchpoints
                'attribution_model': 'multi_touch'
            }
            
            # Add to event properties
            if 'properties' not in event_data:
                event_data['properties'] = {}
            if not isinstance(event_data['properties'], dict):
                event_data['properties'] = {}
            
            event_data['properties']['attribution'] = attribution
            
            return event_data
            
        except Exception as e:
            logger.warning("Error adding event correlation", error=str(e))
            return event_data
    
    def _calculate_touchpoint_weight(self, event_type: str, timestamp: Optional[str]) -> float:
        """
        Calculate touchpoint weight based on type and recency
        
        Args:
            event_type: Type of event
            timestamp: Event timestamp
            
        Returns:
            Weight value (0.0 to 1.0)
        """
        # Base weights by event type
        type_weights = {
            'purchase': 1.0,
            'add_to_cart': 0.7,
            'product_view': 0.5,
            'search': 0.3,
        }
        
        base_weight = type_weights.get(event_type, 0.1)
        
        # Recency decay (events in last 24h get full weight, older events decay)
        if timestamp:
            try:
                from datetime import datetime
                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                now = datetime.utcnow()
                hours_ago = (now - event_time.replace(tzinfo=None)).total_seconds() / 3600
                
                # Decay factor: 1.0 for <24h, linear decay to 0.1 for >7 days
                if hours_ago < 24:
                    recency_factor = 1.0
                elif hours_ago < 168:  # 7 days
                    recency_factor = 1.0 - ((hours_ago - 24) / 144) * 0.9  # Decay to 0.1
                else:
                    recency_factor = 0.1
                
                return base_weight * recency_factor
            except Exception:
                return base_weight
        
        return base_weight


# Global event enricher instance
event_enricher = EventEnricher()

