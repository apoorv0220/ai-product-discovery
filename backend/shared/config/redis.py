"""
AI Product Discovery Suite - Redis Configuration

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import redis.asyncio as redis_async
import redis
from typing import Optional, Any, Dict, List
import json
import pickle
from datetime import datetime, timedelta, date
from shared.config.settings import get_settings


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def get_redis_client():
    """Get Redis client instance"""
    return RedisConfig.get_sync_connection()


async def get_async_redis_client():
    """Get async Redis client instance"""
    return await RedisConfig.get_async_connection()


class RedisConfig:
    """Redis configuration and connection management"""
    
    # Cache key prefixes
    CACHE_PREFIXES = {
        'product': 'prod:',
        'category': 'cat:',
        'search': 'search:',
        'recommendation': 'rec:',
        'user_profile': 'user:',
        'session': 'sess:',
        'analytics': 'analytics:',
        'ab_test': 'ab:',
        'config': 'config:'
    }
    
    # Default TTL values (in seconds)
    DEFAULT_TTL = {
        'product': 3600,  # 1 hour
        'category': 7200,  # 2 hours
        'search_result': 1800,  # 30 minutes
        'recommendation': 1800,  # 30 minutes
        'user_profile': 3600,  # 1 hour
        'session': 1800,  # 30 minutes
        'analytics_temp': 300,  # 5 minutes
        'ab_test_assignment': 86400,  # 24 hours
        'config': 3600  # 1 hour
    }
    
    @classmethod
    def get_sync_connection(cls) -> redis.Redis:
        """Get synchronous Redis connection"""
        settings = get_settings()
        return redis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True
        )
    
    @classmethod
    async def get_async_connection(cls) -> redis_async.Redis:
        """Get asynchronous Redis connection"""
        settings = get_settings()
        return await redis_async.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True
        )
    
    @classmethod
    def build_key(cls, prefix: str, *args) -> str:
        """Build cache key with prefix"""
        cache_prefix = cls.CACHE_PREFIXES.get(prefix, f"{prefix}:")
        return cache_prefix + ":".join(str(arg) for arg in args)


class CacheManager:
    """Redis cache manager with async support"""
    
    def __init__(self):
        self.redis_sync = RedisConfig.get_sync_connection()
        self.redis_async = None
    
    async def get_async_redis(self) -> redis_async.Redis:
        """Get or create async Redis connection"""
        import asyncio
        current_loop = asyncio.get_running_loop()
        
        if self.redis_async is None or getattr(self, '_loop', None) != current_loop:
            self.redis_async = await RedisConfig.get_async_connection()
            self._loop = current_loop
            
        return self.redis_async
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (sync)"""
        try:
            serialized_value = json.dumps(value, default=json_serial) if isinstance(value, (dict, list)) else str(value)
            return self.redis_sync.setex(key, ttl or 3600, serialized_value)
        except Exception:
            return False
    
    async def aset(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (async)"""
        try:
            redis = await self.get_async_redis()
            serialized_value = json.dumps(value, default=json_serial) if isinstance(value, (dict, list)) else str(value)
            await redis.setex(key, ttl or 3600, serialized_value)
            return True
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache (sync)"""
        try:
            value = self.redis_sync.get(key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception:
            return default
    
    async def aget(self, key: str, default: Any = None) -> Any:
        """Get value from cache (async)"""
        try:
            redis = await self.get_async_redis()
            value = await redis.get(key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception:
            return default
    
    def delete(self, *keys: str) -> int:
        """Delete keys from cache (sync)"""
        try:
            return self.redis_sync.delete(*keys)
        except Exception:
            return 0
    
    async def adelete(self, *keys: str) -> int:
        """Delete keys from cache (async)"""
        try:
            redis = await self.get_async_redis()
            return await redis.delete(*keys)
        except Exception:
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists (sync)"""
        try:
            return bool(self.redis_sync.exists(key))
        except Exception:
            return False
    
    async def aexists(self, key: str) -> bool:
        """Check if key exists (async)"""
        try:
            redis = await self.get_async_redis()
            return bool(await redis.exists(key))
        except Exception:
            return False


class SessionManager:
    """Redis-based session management"""
    
    def __init__(self):
        self.cache = CacheManager()
    
    def create_session(self, session_id: str, user_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Create user session"""
        key = RedisConfig.build_key('session', session_id)
        return self.cache.set(key, user_data, ttl)
    
    async def acreate_session(self, session_id: str, user_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Create user session (async)"""
        key = RedisConfig.build_key('session', session_id)
        return await self.cache.aset(key, user_data, ttl)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        key = RedisConfig.build_key('session', session_id)
        return self.cache.get(key)
    
    async def aget_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data (async)"""
        key = RedisConfig.build_key('session', session_id)
        return await self.cache.aget(key)
    
    def update_session(self, session_id: str, data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Update session data"""
        key = RedisConfig.build_key('session', session_id)
        existing_data = self.cache.get(key, {})
        existing_data.update(data)
        return self.cache.set(key, existing_data, ttl)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        key = RedisConfig.build_key('session', session_id)
        return bool(self.cache.delete(key))


class RecommendationCache:
    """Specialized caching for recommendations"""
    
    def __init__(self):
        self.cache = CacheManager()
    
    def cache_recommendations(self, context: str, user_id: Optional[int], 
                            product_id: Optional[int], recommendations: List[Dict], 
                            ttl: int = 1800) -> bool:
        """Cache recommendation results"""
        cache_key_parts = ['recommendation', context]
        if user_id:
            cache_key_parts.append(f"user_{user_id}")
        if product_id:
            cache_key_parts.append(f"product_{product_id}")
        
        key = RedisConfig.build_key(*cache_key_parts)
        return self.cache.set(key, recommendations, ttl)
    
    def get_cached_recommendations(self, context: str, user_id: Optional[int], 
                                 product_id: Optional[int]) -> Optional[List[Dict]]:
        """Get cached recommendation results"""
        cache_key_parts = ['recommendation', context]
        if user_id:
            cache_key_parts.append(f"user_{user_id}")
        if product_id:
            cache_key_parts.append(f"product_{product_id}")
        
        key = RedisConfig.build_key(*cache_key_parts)
        return self.cache.get(key)


class ABTestCache:
    """A/B test assignment caching"""
    
    def __init__(self):
        self.cache = CacheManager()
    
    def assign_variant(self, test_id: str, user_identifier: str, variant: str, ttl: int = 86400) -> bool:
        """Cache A/B test variant assignment"""
        key = RedisConfig.build_key('ab_test', test_id, user_identifier)
        return self.cache.set(key, {'variant': variant, 'assigned_at': str(datetime.utcnow())}, ttl)
    
    def get_variant(self, test_id: str, user_identifier: str) -> Optional[str]:
        """Get cached A/B test variant"""
        key = RedisConfig.build_key('ab_test', test_id, user_identifier)
        assignment = self.cache.get(key)
        return assignment.get('variant') if assignment else None
    
    def track_conversion(self, test_id: str, user_identifier: str, conversion_data: Dict) -> bool:
        """Track A/B test conversion"""
        key = RedisConfig.build_key('ab_test', test_id, user_identifier)
        assignment = self.cache.get(key, {})
        assignment['converted'] = True
        assignment['conversion_data'] = conversion_data
        assignment['converted_at'] = str(datetime.utcnow())
        return self.cache.set(key, assignment, 86400)


class AnalyticsBuffer:
    """Redis-based analytics event buffering with deduplication and rate limiting"""
    
    def __init__(self):
        self.redis_sync = RedisConfig.get_sync_connection()
        # Default rate limits (events per minute)
        self.default_rate_limit = 1000  # 1000 events per minute per merchant
        self.default_user_rate_limit = 100  # 100 events per minute per user
        # Deduplication TTL (events older than this won't be checked for duplicates)
        self.dedup_ttl = 3600  # 1 hour
    
    def buffer_event(
        self,
        event_data: Dict[str, Any],
        check_duplicate: bool = True,
        check_rate_limit: bool = True
    ) -> bool:
        """
        Add event to buffer for batch processing
        
        Args:
            event_data: Event data dictionary (must contain event_id, merchant_id, session_id)
            check_duplicate: Whether to check for duplicates
            check_rate_limit: Whether to check rate limits
            
        Returns:
            True if event was buffered, False otherwise
        """
        try:
            event_id = event_data.get('event_id')
            merchant_id = event_data.get('merchant_id')
            session_id = event_data.get('session_id')
            user_id = event_data.get('user_id')
            
            if not event_id or not merchant_id or not session_id:
                return False
            
            # Check for duplicates if enabled
            if check_duplicate:
                if self._is_duplicate(event_id, merchant_id, session_id):
                    return False  # Duplicate event, don't buffer
            
            # Check rate limits if enabled
            if check_rate_limit:
                if not self._check_rate_limit(merchant_id, user_id):
                    return False  # Rate limit exceeded
            
            # Add to queue
            queue_key = RedisConfig.build_key('analytics', 'events_queue')
            success = bool(self.redis_sync.lpush(queue_key, json.dumps(event_data, default=json_serial)))
            
            # Mark as seen for deduplication
            if success and check_duplicate:
                self._mark_event_seen(event_id, merchant_id, session_id)
            
            return success
            
        except Exception as e:
            # Log error but don't raise (fail silently for resilience)
            return False
    
    def _is_duplicate(self, event_id: str, merchant_id: int, session_id: str) -> bool:
        """Check if event is a duplicate using Redis set"""
        try:
            dedup_key = RedisConfig.build_key('analytics', 'dedup', merchant_id, session_id)
            return bool(self.redis_sync.sismember(dedup_key, event_id))
        except Exception:
            return False  # On error, assume not duplicate (fail open)
    
    def _mark_event_seen(self, event_id: str, merchant_id: int, session_id: str) -> None:
        """Mark event as seen for deduplication"""
        try:
            dedup_key = RedisConfig.build_key('analytics', 'dedup', merchant_id, session_id)
            # Add event_id to set with TTL
            pipe = self.redis_sync.pipeline()
            pipe.sadd(dedup_key, event_id)
            pipe.expire(dedup_key, self.dedup_ttl)
            pipe.execute()
        except Exception:
            pass  # Fail silently
    
    def _check_rate_limit(self, merchant_id: int, user_id: Optional[int] = None) -> bool:
        """
        Check rate limit for merchant and optionally user
        
        Uses sliding window rate limiting with Redis
        
        Returns:
            True if within rate limit, False if exceeded
        """
        try:
            # Check merchant rate limit
            merchant_key = RedisConfig.build_key('analytics', 'rate_limit', 'merchant', merchant_id)
            merchant_count = self.redis_sync.incr(merchant_key)
            
            if merchant_count == 1:
                # First request, set expiration
                self.redis_sync.expire(merchant_key, 60)  # 1 minute window
            
            if merchant_count > self.default_rate_limit:
                return False  # Merchant rate limit exceeded
            
            # Check user rate limit if user_id provided
            if user_id:
                user_key = RedisConfig.build_key('analytics', 'rate_limit', 'user', user_id)
                user_count = self.redis_sync.incr(user_key)
                
                if user_count == 1:
                    # First request, set expiration
                    self.redis_sync.expire(user_key, 60)  # 1 minute window
                
                if user_count > self.default_user_rate_limit:
                    return False  # User rate limit exceeded
            
            return True
            
        except Exception:
            return True  # On error, allow event (fail open)
    
    def get_buffered_events(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Get batch of events from buffer"""
        try:
            queue_key = RedisConfig.build_key('analytics', 'events_queue')
            events = []
            for _ in range(batch_size):
                event_json = self.redis_sync.rpop(queue_key)
                if not event_json:
                    break
                try:
                    events.append(json.loads(event_json))
                except json.JSONDecodeError:
                    continue
            return events
        except Exception:
            return []
    
    def get_queue_length(self) -> int:
        """Get number of events in buffer"""
        try:
            queue_key = RedisConfig.build_key('analytics', 'events_queue')
            return self.redis_sync.llen(queue_key)
        except Exception:
            return 0
    
    def clear_deduplication_cache(self, merchant_id: int, session_id: str) -> None:
        """Clear deduplication cache for a session (useful for testing)"""
        try:
            dedup_key = RedisConfig.build_key('analytics', 'dedup', merchant_id, session_id)
            self.redis_sync.delete(dedup_key)
        except Exception:
            pass


# Global instances
cache_manager = CacheManager()
session_manager = SessionManager()
recommendation_cache = RecommendationCache()
ab_test_cache = ABTestCache()
analytics_buffer = AnalyticsBuffer()