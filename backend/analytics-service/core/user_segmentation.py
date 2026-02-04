"""
AI Product Discovery Suite - User Segmentation Service

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct
import structlog

from shared.database.base import AsyncSessionLocal
from shared.models.analytics import UserBehaviorAggregation, AnalyticsEvent, SessionAnalytics
from core.dashboard_queries import DashboardQueryService

logger = structlog.get_logger()


class BehavioralTagger:
    """Service for assigning behavioral tags to users based on history"""
    
    def __init__(self):
        self.thresholds = {
            'high_spender_revenue': 500.0,
            'frequent_searcher_count': 10,
            'window_shopper_views': 20,
            'loyal_customer_purchases': 3
        }

    async def tag_user(self, behavior: UserBehaviorAggregation) -> List[str]:
        """Assign tags to a user based on their behavior aggregation"""
        tags = []
        
        # 1. High Spender
        if (behavior.total_revenue or 0) > self.thresholds['high_spender_revenue']:
            tags.append("High Spender")
            
        # 2. Frequent Searcher
        if (behavior.searches or 0) > self.thresholds['frequent_searcher_count']:
            tags.append("Frequent Searcher")
            
        # 3. Window Shopper (High views, no purchases)
        if (behavior.product_views or 0) > self.thresholds['window_shopper_views'] and (behavior.purchases or 0) == 0:
            tags.append("Window Shopper")
            
        # 4. Loyal Customer
        if (behavior.purchases or 0) >= self.thresholds['loyal_customer_purchases']:
            tags.append("Loyal Customer")
            
        # 5. Category Loyal (Top category affinity > 0.7)
        if behavior.category_affinity:
            top_cat = max(behavior.category_affinity.values()) if behavior.category_affinity else 0
            if top_cat > 0.7:
                tags.append("Category Specialist")
                
        return tags


class UserSegmentationService:
    """Rule-based user segmentation using analytics event data"""
    
    def __init__(self):
        self.query_service = DashboardQueryService()
        
        # Default segmentation thresholds (can be made configurable)
        self.thresholds = {
            'high_value_revenue': 1000.0,  # $1000+ total revenue
            'frequent_buyer_purchases': 5,  # 5+ purchases
            'engaged_events': 50,  # 50+ total events
            'search_active_searches': 10,  # 10+ searches
            'new_user_days': 30  # First event within last 30 days
        }
    
    async def get_segments(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get all user segments with counts and metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with segment information
        """
        try:
            # Default to last 30 days if no date range specified
            if not date_to:
                date_to = datetime.utcnow()
            if not date_from:
                date_from = date_to - timedelta(days=30)
            
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
                
                # Get all segments
                segments = {}
                
                # High-value users
                high_value = await self._get_high_value_users(session, date_filter)
                segments['high_value'] = high_value
                
                # Frequent buyers
                frequent_buyers = await self._get_frequent_buyers(session, date_filter)
                segments['frequent_buyers'] = frequent_buyers
                
                # Engaged users
                engaged = await self._get_engaged_users(session, date_filter)
                segments['engaged'] = engaged
                
                # New users
                new_users = await self._get_new_users(session, merchant_id, date_from, date_to)
                segments['new_users'] = new_users
                
                # Returning users
                returning = await self._get_returning_users(session, date_filter)
                segments['returning'] = returning
                
                # Search-active users
                search_active = await self._get_search_active_users(session, date_filter)
                segments['search_active'] = search_active
                
                logger.info(
                    "User segments calculated",
                    merchant_id=merchant_id,
                    segments=list(segments.keys())
                )
                
                return {
                    'segments': segments,
                    'total_segments': len(segments),
                    'period': {
                        'start': date_from.isoformat(),
                        'end': date_to.isoformat()
                    }
                }
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(
                "Error getting user segments",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _get_high_value_users(
        self,
        session: AsyncSession,
        date_filter
    ) -> Dict[str, Any]:
        """Get high-value users (revenue > threshold)"""
        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count'),
            func.sum(UserBehaviorAggregation.total_revenue).label('total_revenue'),
            func.avg(UserBehaviorAggregation.total_revenue).label('avg_revenue')
        ).where(
            and_(
                date_filter,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.total_revenue > self.thresholds['high_value_revenue']
            )
        )
        
        result = await session.execute(query)
        row = result.first()
        
        return {
            'segment_name': 'high_value',
            'user_count': row.count or 0,
            'total_revenue': float(row.total_revenue or 0.0),
            'avg_revenue': float(row.avg_revenue or 0.0),
            'threshold': self.thresholds['high_value_revenue']
        }
    
    async def _get_frequent_buyers(
        self,
        session: AsyncSession,
        date_filter
    ) -> Dict[str, Any]:
        """Get frequent buyers (purchases > threshold)"""
        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count'),
            func.sum(UserBehaviorAggregation.purchases).label('total_purchases'),
            func.avg(UserBehaviorAggregation.purchases).label('avg_purchases')
        ).where(
            and_(
                date_filter,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.purchases > self.thresholds['frequent_buyer_purchases']
            )
        )
        
        result = await session.execute(query)
        row = result.first()
        
        return {
            'segment_name': 'frequent_buyers',
            'user_count': row.count or 0,
            'total_purchases': row.total_purchases or 0,
            'avg_purchases': float(row.avg_purchases or 0.0),
            'threshold': self.thresholds['frequent_buyer_purchases']
        }
    
    async def _get_engaged_users(
        self,
        session: AsyncSession,
        date_filter
    ) -> Dict[str, Any]:
        """Get engaged users (events > threshold)"""
        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count'),
            func.sum(UserBehaviorAggregation.total_events).label('total_events'),
            func.avg(UserBehaviorAggregation.total_events).label('avg_events')
        ).where(
            and_(
                date_filter,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.total_events > self.thresholds['engaged_events']
            )
        )
        
        result = await session.execute(query)
        row = result.first()
        
        return {
            'segment_name': 'engaged',
            'user_count': row.count or 0,
            'total_events': row.total_events or 0,
            'avg_events': float(row.avg_events or 0.0),
            'threshold': self.thresholds['engaged_events']
        }
    
    async def _get_new_users(
        self,
        session: AsyncSession,
        merchant_id: int,
        date_from: datetime,
        date_to: datetime
    ) -> Dict[str, Any]:
        """Get new users (first event within date range)"""
        # Approximate new users as users with session_count == 1
        # This is a simplification - in production, you'd track first_event_date
        # Convert timezone-aware datetime to naive datetime for database compatibility
        naive_date_from = date_from.replace(tzinfo=None) if date_from.tzinfo else date_from
        naive_date_to = date_to.replace(tzinfo=None) if date_to.tzinfo else date_to

        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count')
        ).where(
            and_(
                UserBehaviorAggregation.merchant_id == merchant_id,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.last_activity >= naive_date_from,
                UserBehaviorAggregation.last_activity <= naive_date_to,
                UserBehaviorAggregation.session_count == 1
            )
        )
        
        result = await session.execute(query)
        count = result.scalar() or 0
        
        return {
            'segment_name': 'new_users',
            'user_count': count,
            'period_days': (date_to - date_from).days
        }
    
    async def _get_returning_users(
        self,
        session: AsyncSession,
        date_filter
    ) -> Dict[str, Any]:
        """Get returning users (multiple sessions)"""
        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count'),
            func.avg(UserBehaviorAggregation.session_count).label('avg_sessions')
        ).where(
            and_(
                date_filter,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.session_count > 1
            )
        )
        
        result = await session.execute(query)
        row = result.first()
        
        return {
            'segment_name': 'returning',
            'user_count': row.count or 0,
            'avg_sessions': float(row.avg_sessions or 0.0)
        }
    
    async def _get_search_active_users(
        self,
        session: AsyncSession,
        date_filter
    ) -> Dict[str, Any]:
        """Get search-active users (searches > threshold)"""
        query = select(
            func.count(distinct(UserBehaviorAggregation.user_id)).label('count'),
            func.sum(UserBehaviorAggregation.searches).label('total_searches'),
            func.avg(UserBehaviorAggregation.searches).label('avg_searches')
        ).where(
            and_(
                date_filter,
                UserBehaviorAggregation.user_id.isnot(None),
                UserBehaviorAggregation.searches > self.thresholds['search_active_searches']
            )
        )
        
        result = await session.execute(query)
        row = result.first()
        
        return {
            'segment_name': 'search_active',
            'user_count': row.count or 0,
            'total_searches': row.total_searches or 0,
            'avg_searches': float(row.avg_searches or 0.0),
            'threshold': self.thresholds['search_active_searches']
        }
    
    async def get_segment_users(
        self,
        merchant_id: int,
        segment_name: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get users in a specific segment with pagination
        
        Args:
            merchant_id: Merchant ID
            segment_name: Name of the segment
            date_from: Start date (optional)
            date_to: End date (optional)
            limit: Limit for pagination
            offset: Offset for pagination
            
        Returns:
            Dictionary with segment users
        """
        try:
            if not date_to:
                date_to = datetime.utcnow()
            if not date_from:
                date_from = date_to - timedelta(days=30)
            
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
                
                # Build segment-specific filter
                segment_filter = self._build_segment_filter(segment_name, date_filter)
                
                # Get users
                query = select(
                    UserBehaviorAggregation.user_id,
                    UserBehaviorAggregation.total_events,
                    UserBehaviorAggregation.total_revenue,
                    UserBehaviorAggregation.purchases,
                    UserBehaviorAggregation.searches,
                    UserBehaviorAggregation.session_count,
                    UserBehaviorAggregation.last_activity
                ).where(
                    and_(
                        segment_filter,
                        UserBehaviorAggregation.user_id.isnot(None)
                    )
                ).order_by(
                    UserBehaviorAggregation.last_activity.desc()
                ).limit(limit).offset(offset)
                
                result = await session.execute(query)
                users = []
                
                for row in result.all():
                    users.append({
                        'user_id': row.user_id,
                        'total_events': row.total_events,
                        'total_revenue': float(row.total_revenue or 0.0),
                        'purchases': row.purchases,
                        'searches': row.searches,
                        'session_count': row.session_count,
                        'last_activity': row.last_activity.isoformat() if row.last_activity else None
                    })
                
                # Get total count
                count_query = select(
                    func.count(distinct(UserBehaviorAggregation.user_id))
                ).where(
                    and_(
                        segment_filter,
                        UserBehaviorAggregation.user_id.isnot(None)
                    )
                )
                
                count_result = await session.execute(count_query)
                total_count = count_result.scalar() or 0
                
                return {
                    'segment_name': segment_name,
                    'users': users,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset
                }
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(
                "Error getting segment users",
                merchant_id=merchant_id,
                segment_name=segment_name,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _build_segment_filter(self, segment_name: str, base_filter):
        """Build filter for specific segment"""
        if segment_name == 'high_value':
            return and_(
                base_filter,
                UserBehaviorAggregation.total_revenue > self.thresholds['high_value_revenue']
            )
        elif segment_name == 'frequent_buyers':
            return and_(
                base_filter,
                UserBehaviorAggregation.purchases > self.thresholds['frequent_buyer_purchases']
            )
        elif segment_name == 'engaged':
            return and_(
                base_filter,
                UserBehaviorAggregation.total_events > self.thresholds['engaged_events']
            )
        elif segment_name == 'returning':
            return and_(
                base_filter,
                UserBehaviorAggregation.session_count > 1
            )
        elif segment_name == 'search_active':
            return and_(
                base_filter,
                UserBehaviorAggregation.searches > self.thresholds['search_active_searches']
            )
        else:
            return base_filter
    
    async def analyze_segment_performance(
        self,
        merchant_id: int,
        segment_name: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance metrics for a specific segment
        
        Args:
            merchant_id: Merchant ID
            segment_name: Name of the segment
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with segment performance metrics
        """
        try:
            if not date_to:
                date_to = datetime.utcnow()
            if not date_from:
                date_from = date_to - timedelta(days=30)
            
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
                segment_filter = self._build_segment_filter(segment_name, date_filter)
                
                # Get segment metrics
                query = select(
                    func.count(distinct(UserBehaviorAggregation.user_id)).label('user_count'),
                    func.sum(UserBehaviorAggregation.total_revenue).label('total_revenue'),
                    func.avg(UserBehaviorAggregation.total_revenue).label('avg_revenue_per_user'),
                    func.sum(UserBehaviorAggregation.purchases).label('total_purchases'),
                    func.avg(UserBehaviorAggregation.purchases).label('avg_purchases_per_user'),
                    func.sum(UserBehaviorAggregation.total_events).label('total_events'),
                    func.avg(UserBehaviorAggregation.total_events).label('avg_events_per_user')
                ).where(
                    and_(
                        segment_filter,
                        UserBehaviorAggregation.user_id.isnot(None)
                    )
                )
                
                result = await session.execute(query)
                row = result.first()
                
                user_count = row.user_count or 0
                total_revenue = float(row.total_revenue or 0.0)
                total_purchases = row.total_purchases or 0
                
                # Calculate conversion rate
                conversion_rate = (total_purchases / user_count * 100) if user_count > 0 else 0.0
                
                # Calculate retention (approximate as returning users / total)
                returning_query = select(
                    func.count(distinct(UserBehaviorAggregation.user_id))
                ).where(
                    and_(
                        segment_filter,
                        UserBehaviorAggregation.user_id.isnot(None),
                        UserBehaviorAggregation.session_count > 1
                    )
                )
                
                returning_result = await session.execute(returning_query)
                returning_count = returning_result.scalar() or 0
                retention_rate = (returning_count / user_count * 100) if user_count > 0 else 0.0
                
                return {
                    'segment_name': segment_name,
                    'user_count': user_count,
                    'total_revenue': total_revenue,
                    'avg_revenue_per_user': float(row.avg_revenue_per_user or 0.0),
                    'total_purchases': total_purchases,
                    'avg_purchases_per_user': float(row.avg_purchases_per_user or 0.0),
                    'conversion_rate': conversion_rate,
                    'total_events': row.total_events or 0,
                    'avg_events_per_user': float(row.avg_events_per_user or 0.0),
                    'retention_rate': retention_rate
                }
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(
                "Error analyzing segment performance",
                merchant_id=merchant_id,
                segment_name=segment_name,
                error=str(e),
                exc_info=True
            )
            raise

