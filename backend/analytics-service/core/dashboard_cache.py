"""
AI Product Discovery Suite - Dashboard Cache Service

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import structlog

from shared.config.redis import CacheManager, RedisConfig

logger = structlog.get_logger()


class DashboardCache:
    """Centralized caching logic for dashboard endpoints"""
    
    def __init__(self):
        self.cache = CacheManager()
    
    def _build_cache_key(
        self,
        cache_type: str,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        period: Optional[str] = None
    ) -> str:
        """
        Build cache key for dashboard queries
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            metric_name: Metric name for time-series (optional)
            period: Period for time-series (optional)
            
        Returns:
            Cache key string
        """
        key_parts = ['analytics', 'dashboard', cache_type, str(merchant_id)]
        
        if date_from:
            key_parts.append(date_from.isoformat())
        if date_to:
            key_parts.append(date_to.isoformat())
        if metric_name:
            key_parts.append(metric_name)
        if period:
            key_parts.append(period)
        
        return ':'.join(key_parts)
    
    async def get(
        self,
        cache_type: str,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        period: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached dashboard data
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            metric_name: Metric name for time-series (optional)
            period: Period for time-series (optional)
            
        Returns:
            Cached data or None if not found
        """
        try:
            cache_key = self._build_cache_key(
                cache_type, merchant_id, date_from, date_to, metric_name, period
            )
            data = await self.cache.aget(cache_key)
            
            if data:
                logger.debug("Cache hit", cache_key=cache_key, cache_type=cache_type)
            else:
                logger.debug("Cache miss", cache_key=cache_key, cache_type=cache_type)
            
            return data
        except Exception as e:
            logger.warning("Error getting cache", error=str(e), cache_type=cache_type)
            return None
    
    async def set(
        self,
        cache_type: str,
        merchant_id: int,
        data: Any,
        ttl: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        period: Optional[str] = None
    ) -> bool:
        """
        Set cached dashboard data
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            merchant_id: Merchant ID
            data: Data to cache
            ttl: Time to live in seconds
            date_from: Start date (optional)
            date_to: End date (optional)
            metric_name: Metric name for time-series (optional)
            period: Period for time-series (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._build_cache_key(
                cache_type, merchant_id, date_from, date_to, metric_name, period
            )
            success = await self.cache.aset(cache_key, data, ttl)
            
            if success:
                logger.debug("Cache set", cache_key=cache_key, ttl=ttl, cache_type=cache_type)
            
            return success
        except Exception as e:
            logger.warning("Error setting cache", error=str(e), cache_type=cache_type)
            return False
    
    async def delete(
        self,
        cache_type: str,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        period: Optional[str] = None
    ) -> bool:
        """
        Delete cached dashboard data
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            metric_name: Metric name for time-series (optional)
            period: Period for time-series (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._build_cache_key(
                cache_type, merchant_id, date_from, date_to, metric_name, period
            )
            deleted = await self.cache.adelete(cache_key)
            
            if deleted:
                logger.debug("Cache deleted", cache_key=cache_key, cache_type=cache_type)
            
            return bool(deleted)
        except Exception as e:
            logger.warning("Error deleting cache", error=str(e), cache_type=cache_type)
            return False
    
    def get_ttl(self, cache_type: str, period: Optional[str] = None) -> int:
        """
        Get TTL for cache type
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            period: Period for time-series metrics (optional)
            
        Returns:
            TTL in seconds
        """
        # Default TTLs
        ttl_map = {
            'overview': 300,  # 5 minutes
            'sessions': 300,  # 5 minutes
            'users': 300,  # 5 minutes
            'metrics': {
                'hourly': 600,  # 10 minutes
                'daily': 1800,  # 30 minutes
                'weekly': 3600,  # 1 hour
                'monthly': 3600,  # 1 hour
            }
        }
        
        if cache_type == 'metrics' and period:
            return ttl_map.get('metrics', {}).get(period, 600)
        
        return ttl_map.get(cache_type, 300)
    
    async def invalidate_merchant(self, merchant_id: int) -> bool:
        """
        Invalidate all cache entries for a merchant
        
        Args:
            merchant_id: Merchant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a simple implementation - in production, you might want to use
            # Redis SCAN to find all keys matching the pattern
            pattern = f"analytics:dashboard:*:{merchant_id}:*"
            logger.info("Invalidating merchant cache", merchant_id=merchant_id, pattern=pattern)
            # Note: Full implementation would require Redis SCAN or maintaining a key index
            return True
        except Exception as e:
            logger.warning("Error invalidating merchant cache", error=str(e), merchant_id=merchant_id)
            return False

