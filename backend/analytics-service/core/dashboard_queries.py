"""
AI Product Discovery Suite - Dashboard Query Service

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, distinct
from sqlalchemy.sql import extract
import structlog
import time

from shared.database.base import AsyncSessionLocal
from shared.models.analytics import (
    AnalyticsEvent,
    AnalyticsAggregation,
    UserBehaviorAggregation,
    SessionAnalytics,
)
from core.dashboard_cache import DashboardCache

logger = structlog.get_logger()


class DashboardQueryService:
    """Service for dashboard database queries with proper error handling and optimization"""
    
    def __init__(self):
        self.cache = DashboardCache()
    
    def _build_date_filter(self, merchant_id: int, date_from: Optional[datetime], date_to: Optional[datetime]):
        """Build date range filter conditions"""
        conditions = [AnalyticsEvent.merchant_id == merchant_id]

        if date_from:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
            conditions.append(AnalyticsEvent.timestamp >= naive_date_from)
        if date_to:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to
            conditions.append(AnalyticsEvent.timestamp <= naive_date_to)

        return and_(*conditions)
    
    def _build_aggregation_date_filter(self, merchant_id: int, date_from: Optional[datetime], date_to: Optional[datetime]):
        """Build date range filter for aggregation table"""
        conditions = [AnalyticsAggregation.merchant_id == merchant_id]

        if date_from:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
            conditions.append(AnalyticsAggregation.time_window_start >= naive_date_from)
        if date_to:
            # Convert timezone-aware datetime to naive datetime for database compatibility
            naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to
            conditions.append(AnalyticsAggregation.time_window_end <= naive_date_to)

        return and_(*conditions)
    
    async def get_overview_metrics(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard overview metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with overview metrics
        """
        start_time = time.time()
        session = AsyncSessionLocal()
        
        try:
            # Build date filter
            date_filter = self._build_date_filter(merchant_id, date_from, date_to)
            
            # Query for overview metrics
            query = select(
                func.count(AnalyticsEvent.id).label('total_events'),
                func.count(distinct(AnalyticsEvent.user_id)).label('unique_users'),
                func.count(distinct(AnalyticsEvent.session_id)).label('unique_sessions'),
                func.sum(
                    case(
                        (AnalyticsEvent.event_type.in_(['page_view', 'product_view']), 1),
                        else_=0
                    )
                ).label('page_views'),
                func.sum(
                    case(
                        (AnalyticsEvent.event_type == 'product_view', 1),
                        else_=0
                    )
                ).label('product_views'),
                func.sum(
                    case(
                        (AnalyticsEvent.event_type.in_(['search', 'search_query']), 1),
                        else_=0
                    )
                ).label('searches'),
                func.sum(
                    case(
                        (AnalyticsEvent.event_type == 'purchase', 1),
                        else_=0
                    )
                ).label('purchases'),
                func.coalesce(func.sum(AnalyticsEvent.revenue), 0.0).label('revenue')
            ).where(date_filter)
            
            result = await session.execute(query)
            row = result.first()
            
            if not row:
                return {
                    'total_events': 0,
                    'unique_users': 0,
                    'unique_sessions': 0,
                    'page_views': 0,
                    'product_views': 0,
                    'searches': 0,
                    'purchases': 0,
                    'revenue': 0.0,
                    'conversion_rate': 0.0
                }
            
            total_events = row.total_events or 0
            unique_users = row.unique_users or 0
            unique_sessions = row.unique_sessions or 0
            page_views = row.page_views or 0
            product_views = row.product_views or 0
            searches = row.searches or 0
            purchases = row.purchases or 0
            revenue = float(row.revenue or 0.0)
            
            # Calculate conversion rate
            conversion_rate = 0.0
            if unique_users > 0:
                conversion_rate = purchases / unique_users
            
            elapsed = time.time() - start_time
            logger.info(
                "Dashboard overview metrics queried",
                merchant_id=merchant_id,
                elapsed_ms=elapsed * 1000,
                total_events=total_events
            )
            
            return {
                'total_events': total_events,
                'unique_users': unique_users,
                'unique_sessions': unique_sessions,
                'page_views': page_views,
                'product_views': product_views,
                'searches': searches,
                'purchases': purchases,
                'revenue': revenue,
                'conversion_rate': conversion_rate
            }
            
        except Exception as e:
            logger.error(
                "Error getting overview metrics",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await session.close()
    
    async def get_time_series_data(
        self,
        merchant_id: int,
        metric_name: str,
        period: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get time-series data for a specific metric
        
        Args:
            merchant_id: Merchant ID
            metric_name: Name of the metric (page_views, product_views, searches, purchases, revenue, unique_users, unique_sessions)
            period: Time period (hourly, daily, weekly, monthly)
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            List of data points with timestamp and value
        """
        start_time = time.time()
        session = AsyncSessionLocal()
        
        try:
            # Try to use aggregation table first for better performance
            use_aggregation = period in ['hourly', 'daily']
            
            if use_aggregation:
                data_points = await self._get_time_series_from_aggregation(
                    session, merchant_id, metric_name, period, date_from, date_to
                )
                
                # If aggregation table has data, return it
                if data_points:
                    elapsed = time.time() - start_time
                    logger.info(
                        "Time-series data from aggregation table",
                        merchant_id=merchant_id,
                        metric=metric_name,
                        period=period,
                        points=len(data_points),
                        elapsed_ms=elapsed * 1000
                    )
                    return data_points
            
            # Fallback to raw events query
            data_points = await self._get_time_series_from_events(
                session, merchant_id, metric_name, period, date_from, date_to
            )
            
            elapsed = time.time() - start_time
            logger.info(
                "Time-series data from events table",
                merchant_id=merchant_id,
                metric=metric_name,
                period=period,
                points=len(data_points),
                elapsed_ms=elapsed * 1000
            )
            
            return data_points
            
        except Exception as e:
            logger.error(
                "Error getting time-series data",
                merchant_id=merchant_id,
                metric=metric_name,
                period=period,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await session.close()
    
    async def _get_time_series_from_aggregation(
        self,
        session: AsyncSession,
        merchant_id: int,
        metric_name: str,
        period: str,
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get time-series data from aggregation table"""
        date_filter = self._build_aggregation_date_filter(merchant_id, date_from, date_to)
        
        # Map metric names to aggregation columns
        metric_map = {
            'page_views': AnalyticsAggregation.page_views,
            'product_views': AnalyticsAggregation.product_views,
            'searches': AnalyticsAggregation.searches,
            'purchases': AnalyticsAggregation.purchases,
            'revenue': AnalyticsAggregation.revenue,
            'unique_users': AnalyticsAggregation.unique_users,
            'unique_sessions': AnalyticsAggregation.unique_sessions,
        }
        
        if metric_name not in metric_map:
            return []
        
        aggregation_type = 'hourly' if period == 'hourly' else 'daily'
        
        query = select(
            AnalyticsAggregation.time_window_start.label('timestamp'),
            metric_map[metric_name].label('value')
        ).where(
            and_(
                date_filter,
                AnalyticsAggregation.aggregation_type == aggregation_type
            )
        ).order_by(AnalyticsAggregation.time_window_start)
        
        result = await session.execute(query)
        rows = result.all()
        
        return [
            {
                'timestamp': row.timestamp,
                'value': float(row.value or 0)
            }
            for row in rows
        ]
    
    async def _get_time_series_from_events(
        self,
        session: AsyncSession,
        merchant_id: int,
        metric_name: str,
        period: str,
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get time-series data from raw events table"""
        date_filter = self._build_date_filter(merchant_id, date_from, date_to)
        
        # Determine time truncation based on period
        if period == 'hourly':
            time_expr = func.date_trunc('hour', AnalyticsEvent.timestamp)
        elif period == 'daily':
            time_expr = func.date_trunc('day', AnalyticsEvent.timestamp)
        elif period == 'weekly':
            time_expr = func.date_trunc('week', AnalyticsEvent.timestamp)
        elif period == 'monthly':
            time_expr = func.date_trunc('month', AnalyticsEvent.timestamp)
        else:
            time_expr = func.date_trunc('day', AnalyticsEvent.timestamp)
        
        # Build metric expression based on metric_name
        if metric_name == 'page_views':
            metric_expr = func.sum(
                case(
                    (AnalyticsEvent.event_type.in_(['page_view', 'product_view']), 1),
                    else_=0
                )
            )
        elif metric_name == 'product_views':
            metric_expr = func.sum(
                case(
                    (AnalyticsEvent.event_type == 'product_view', 1),
                    else_=0
                )
            )
        elif metric_name == 'searches':
            metric_expr = func.sum(
                case(
                    (AnalyticsEvent.event_type.in_(['search', 'search_query']), 1),
                    else_=0
                )
            )
        elif metric_name == 'purchases':
            metric_expr = func.sum(
                case(
                    (AnalyticsEvent.event_type == 'purchase', 1),
                    else_=0
                )
            )
        elif metric_name == 'revenue':
            metric_expr = func.coalesce(func.sum(AnalyticsEvent.revenue), 0.0)
        elif metric_name == 'unique_users':
            metric_expr = func.count(distinct(AnalyticsEvent.user_id))
        elif metric_name == 'unique_sessions':
            metric_expr = func.count(distinct(AnalyticsEvent.session_id))
        else:
            metric_expr = func.count(AnalyticsEvent.id)
        
        query = select(
            time_expr.label('timestamp'),
            metric_expr.label('value')
        ).where(date_filter).group_by(time_expr).order_by(time_expr)
        
        result = await session.execute(query)
        rows = result.all()
        
        return [
            {
                'timestamp': row.timestamp,
                'value': float(row.value or 0)
            }
            for row in rows
        ]
    
    async def get_session_analytics(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get session analytics metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with session analytics
        """
        start_time = time.time()
        session = AsyncSessionLocal()
        
        try:
            conditions = [SessionAnalytics.merchant_id == merchant_id]

            if date_from:
                # Convert timezone-aware datetime to naive datetime for database compatibility
                naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
                conditions.append(SessionAnalytics.start_time >= naive_date_from)
            if date_to:
                # Convert timezone-aware datetime to naive datetime for database compatibility
                naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to
                conditions.append(SessionAnalytics.start_time <= naive_date_to)
            
            date_filter = and_(*conditions)
            
            # Query session metrics
            query = select(
                func.count(SessionAnalytics.id).label('total_sessions'),
                func.avg(SessionAnalytics.duration).label('avg_duration'),
                func.sum(
                    case(
                        (SessionAnalytics.bounce == 'true', 1),
                        else_=0
                    )
                ).label('bounce_count'),
                func.count(SessionAnalytics.id).label('total_count')
            ).where(date_filter)
            
            result = await session.execute(query)
            row = result.first()
            
            if not row or row.total_sessions == 0:
                return {
                    'total_sessions': 0,
                    'avg_duration': 0.0,
                    'bounce_rate': 0.0,
                    'sessions_by_device': {},
                    'sessions_by_platform': {}
                }
            
            total_sessions = row.total_sessions or 0
            avg_duration = float(row.avg_duration or 0.0)
            bounce_count = row.bounce_count or 0
            bounce_rate = bounce_count / total_sessions if total_sessions > 0 else 0.0
            
            # Get device breakdown
            device_query = select(
                SessionAnalytics.device_type,
                func.count(SessionAnalytics.id).label('count')
            ).where(date_filter).group_by(SessionAnalytics.device_type)
            
            device_result = await session.execute(device_query)
            sessions_by_device = {
                row.device_type or 'unknown': row.count
                for row in device_result.all()
            }
            
            # Get platform breakdown
            platform_query = select(
                SessionAnalytics.platform,
                func.count(SessionAnalytics.id).label('count')
            ).where(date_filter).group_by(SessionAnalytics.platform)
            
            platform_result = await session.execute(platform_query)
            sessions_by_platform = {
                row.platform or 'unknown': row.count
                for row in platform_result.all()
            }
            
            elapsed = time.time() - start_time
            logger.info(
                "Session analytics queried",
                merchant_id=merchant_id,
                total_sessions=total_sessions,
                elapsed_ms=elapsed * 1000
            )
            
            return {
                'total_sessions': total_sessions,
                'avg_duration': avg_duration,
                'bounce_rate': bounce_rate,
                'sessions_by_device': sessions_by_device,
                'sessions_by_platform': sessions_by_platform
            }
            
        except Exception as e:
            logger.error(
                "Error getting session analytics",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await session.close()
    
    async def get_user_behavior_metrics(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get user behavior metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            limit: Limit for pagination
            offset: Offset for pagination
            
        Returns:
            Dictionary with user behavior metrics
        """
        start_time = time.time()
        session = AsyncSessionLocal()
        
        try:
            conditions = [UserBehaviorAggregation.merchant_id == merchant_id]
            
            if date_from:
                # Convert timezone-aware datetime to naive datetime for database compatibility
                naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
                conditions.append(UserBehaviorAggregation.last_activity >= naive_date_from)
            if date_to:
                # Convert timezone-aware datetime to naive datetime for database compatibility
                naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to
                conditions.append(UserBehaviorAggregation.last_activity <= naive_date_to)
            
            date_filter = and_(*conditions)
            
            # Get total users
            total_query = select(func.count(distinct(UserBehaviorAggregation.user_id))).where(
                and_(
                    date_filter,
                    UserBehaviorAggregation.user_id.isnot(None)
                )
            )
            total_result = await session.execute(total_query)
            total_users = total_result.scalar() or 0
            
            # Get new users (users with first activity in date range)
            # This is approximated by checking users with session_count == 1
            new_users_query = select(func.count(distinct(UserBehaviorAggregation.user_id))).where(
                and_(
                    date_filter,
                    UserBehaviorAggregation.user_id.isnot(None),
                    UserBehaviorAggregation.session_count == 1
                )
            )
            new_users_result = await session.execute(new_users_query)
            new_users = new_users_result.scalar() or 0
            
            returning_users = total_users - new_users
            
            # Get average events per user
            avg_events_query = select(
                func.avg(UserBehaviorAggregation.total_events).label('avg_events')
            ).where(
                and_(
                    date_filter,
                    UserBehaviorAggregation.user_id.isnot(None)
                )
            )
            avg_events_result = await session.execute(avg_events_query)
            avg_events = float(avg_events_result.scalar() or 0.0)
            
            # Get top user segments (foundation for segmentation)
            # This will be enhanced in Phase 2.3
            top_segments = []
            
            elapsed = time.time() - start_time
            logger.info(
                "User behavior metrics queried",
                merchant_id=merchant_id,
                total_users=total_users,
                elapsed_ms=elapsed * 1000
            )
            
            return {
                'total_users': total_users,
                'new_users': new_users,
                'returning_users': returning_users,
                'avg_events_per_user': avg_events,
                'top_user_segments': top_segments
            }
            
        except Exception as e:
            logger.error(
                "Error getting user behavior metrics",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            await session.close()
    
    def generate_cache_key(
        self,
        cache_type: str,
        merchant_id: int,
        **kwargs
    ) -> str:
        """
        Generate cache key for dashboard queries
        
        Args:
            cache_type: Type of cache (overview, metrics, sessions, users)
            merchant_id: Merchant ID
            **kwargs: Additional parameters for cache key
            
        Returns:
            Cache key string
        """
        key_parts = ['analytics', 'dashboard', cache_type, str(merchant_id)]
        
        if 'date_from' in kwargs and kwargs['date_from']:
            key_parts.append(kwargs['date_from'].isoformat())
        if 'date_to' in kwargs and kwargs['date_to']:
            key_parts.append(kwargs['date_to'].isoformat())
        if 'metric_name' in kwargs:
            key_parts.append(kwargs['metric_name'])
        if 'period' in kwargs:
            key_parts.append(kwargs['period'])
        
        return ':'.join(key_parts)

