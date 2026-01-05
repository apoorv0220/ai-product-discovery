"""
AI Product Discovery Suite - Data Aggregator

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from shared.database.base import AsyncSessionLocal
from shared.models.analytics import (
    AnalyticsEvent,
    AnalyticsAggregation,
    UserBehaviorAggregation,
    SessionAnalytics,
)
from shared.config.redis import analytics_buffer

logger = structlog.get_logger()


class DataAggregator:
    """Data aggregator for analytics"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        """Initialize the data aggregator"""
        logger.info("Initializing data aggregator")
        self.initialized = True
    
    async def cleanup(self):
        """Clean up the data aggregator"""
        logger.info("Cleaning up data aggregator")
        self.initialized = False
    
    async def aggregate_events(self, events: List[Dict[str, Any]]) -> bool:
        """
        Aggregate a batch of events
        
        Args:
            events: List of event dictionaries
            
        Returns:
            True if aggregation was successful
        """
        try:
            if not events:
                return True
            
            # Group events by merchant and time window
            events_by_merchant = {}
            for event in events:
                merchant_id = event.get('merchant_id')
                if not merchant_id:
                    continue
                
                if merchant_id not in events_by_merchant:
                    events_by_merchant[merchant_id] = []
                events_by_merchant[merchant_id].append(event)
            
            # Aggregate for each merchant
            for merchant_id, merchant_events in events_by_merchant.items():
                # Real-time aggregation (5-minute windows)
                await self.aggregate_by_time_window(
                    merchant_events,
                    merchant_id,
                    'real_time',
                    timedelta(minutes=5)
                )
                
                # Hourly aggregation
                await self.aggregate_by_time_window(
                    merchant_events,
                    merchant_id,
                    'hourly',
                    timedelta(hours=1)
                )
                
                # Daily aggregation
                await self.aggregate_by_time_window(
                    merchant_events,
                    merchant_id,
                    'daily',
                    timedelta(days=1)
                )
                
                # User behavior aggregation
                await self.aggregate_user_behavior(merchant_events, merchant_id)
                
                # Session analytics
                await self.aggregate_session_analytics(merchant_events, merchant_id)
            
            return True
            
        except Exception as e:
            logger.error("Error aggregating events", error=str(e), exc_info=True)
            return False
    
    async def aggregate_by_time_window(
        self,
        events: List[Dict[str, Any]],
        merchant_id: int,
        aggregation_type: str,
        window_size: timedelta
    ) -> bool:
        """
        Aggregate events by time window
        
        Args:
            events: List of event dictionaries
            merchant_id: Merchant ID
            aggregation_type: Type of aggregation ('real_time', 'hourly', 'daily', 'weekly')
            window_size: Size of time window
            
        Returns:
            True if aggregation was successful
        """
        db_session = AsyncSessionLocal()
        
        try:
            # Group events by time window
            events_by_window = {}
            for event in events:
                timestamp = event.get('timestamp')
                if not timestamp:
                    continue
                
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # Round down to window start
                window_start = self._round_to_window(timestamp, window_size)
                window_key = (merchant_id, aggregation_type, window_start)
                
                if window_key not in events_by_window:
                    events_by_window[window_key] = []
                events_by_window[window_key].append(event)
            
            # Aggregate each time window
            for (merch_id, agg_type, window_start), window_events in events_by_window.items():
                window_end = window_start + window_size
                
                # Get or create aggregation record
                result = await db_session.execute(
                    select(AnalyticsAggregation).where(
                        and_(
                            AnalyticsAggregation.merchant_id == merch_id,
                            AnalyticsAggregation.aggregation_type == agg_type,
                            AnalyticsAggregation.time_window_start == window_start
                        )
                    )
                )
                aggregation = result.scalar_one_or_none()
                
                if not aggregation:
                    aggregation = AnalyticsAggregation(
                        merchant_id=merch_id,
                        aggregation_type=agg_type,
                        time_window_start=window_start,
                        time_window_end=window_end,
                        total_events=0,
                        unique_users=0,
                        unique_sessions=0,
                        page_views=0,
                        product_views=0,
                        searches=0,
                        add_to_carts=0,
                        purchases=0,
                        revenue=0.0,
                        conversion_rate=0.0,
                        metrics={}
                    )
                    db_session.add(aggregation)
                
                # Update aggregation metrics
                aggregation.total_events += len(window_events)
                
                unique_users = set()
                unique_sessions = set()
                
                for event in window_events:
                    # Track unique users
                    if event.get('user_id'):
                        unique_users.add(event['user_id'])
                    
                    # Track unique sessions
                    if event.get('session_id'):
                        unique_sessions.add(event['session_id'])
                    
                    # Count event types
                    event_type = event.get('event_type', '').lower()
                    if 'page_view' in event_type:
                        aggregation.page_views += 1
                    elif 'product_view' in event_type:
                        aggregation.product_views += 1
                    elif 'search' in event_type:
                        aggregation.searches += 1
                    elif 'add_to_cart' in event_type:
                        aggregation.add_to_carts += 1
                    elif 'purchase' in event_type:
                        aggregation.purchases += 1
                        revenue = event.get('revenue', 0) or 0
                        aggregation.revenue += float(revenue)
                
                # Update unique counts (convert sets to counts for database)
                aggregation.unique_users = len(unique_users)
                aggregation.unique_sessions = len(unique_sessions)
                
                # Calculate conversion rate
                if aggregation.unique_users > 0:
                    aggregation.conversion_rate = aggregation.purchases / aggregation.unique_users
                
                aggregation.updated_at = datetime.utcnow()
            
            await db_session.commit()
            return True
            
        except Exception as e:
            logger.error("Error aggregating by time window", error=str(e))
            await db_session.rollback()
            return False
        finally:
            await db_session.close()
    
    def _round_to_window(self, timestamp: datetime, window_size: timedelta) -> datetime:
        """Round timestamp down to window start"""
        if window_size == timedelta(minutes=5):
            # Round to nearest 5 minutes
            minutes = (timestamp.minute // 5) * 5
            return timestamp.replace(minute=minutes, second=0, microsecond=0)
        elif window_size == timedelta(hours=1):
            # Round to hour
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif window_size == timedelta(days=1):
            # Round to day
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default: round to nearest hour
            return timestamp.replace(minute=0, second=0, microsecond=0)
    
    async def aggregate_user_behavior(
        self,
        events: List[Dict[str, Any]],
        merchant_id: int
    ) -> bool:
        """
        Aggregate user behavior metrics
        
        Args:
            events: List of event dictionaries
            merchant_id: Merchant ID
            
        Returns:
            True if aggregation was successful
        """
        db_session = AsyncSessionLocal()
        
        try:
            # Group events by user/session (support both user-only and session-only tracking)
            events_by_user = {}
            for event in events:
                user_id = event.get('user_id')
                session_id = event.get('session_id')

                # Use whichever identifier is available (user_id takes precedence for user-level aggregation)
                if user_id:
                    key = (user_id, session_id or 'no_session')
                elif session_id:
                    key = ('anonymous', session_id)
                else:
                    # Skip events with no user or session identifier
                    continue

                if key not in events_by_user:
                    events_by_user[key] = []
                events_by_user[key].append(event)
            
            # Update user behavior aggregations
            for (user_id, session_id), user_events in events_by_user.items():
                # For user-level aggregation, use user_id as primary key when available
                if user_id and user_id != 'anonymous':
                    # User-level aggregation
                    result = await db_session.execute(
                        select(UserBehaviorAggregation).where(
                            and_(
                                UserBehaviorAggregation.merchant_id == merchant_id,
                                UserBehaviorAggregation.user_id == str(user_id),
                                UserBehaviorAggregation.session_id == session_id
                            )
                        )
                    )
                else:
                    # Session-level aggregation for anonymous users
                    result = await db_session.execute(
                        select(UserBehaviorAggregation).where(
                            and_(
                                UserBehaviorAggregation.merchant_id == merchant_id,
                                UserBehaviorAggregation.session_id == session_id
                            )
                        )
                    )

                behavior = result.scalar_one_or_none()

                if not behavior:
                    behavior = UserBehaviorAggregation(
                        merchant_id=merchant_id,
                        user_id=str(user_id) if user_id and user_id != 'anonymous' else None,
                        session_id=session_id,
                        total_events=0,
                        page_views=0,
                        product_views=0,
                        searches=0,
                        add_to_carts=0,
                        purchases=0,
                        total_revenue=0.0,
                        session_count=0,
                        avg_session_duration=0.0,
                        last_activity=datetime.utcnow(),
                        behavior_patterns={}
                    )
                    db_session.add(behavior)
                
                # Update behavior metrics
                behavior.total_events += len(user_events)
                
                for event in user_events:
                    event_type = event.get('event_type', '').lower()
                    if 'page_view' in event_type:
                        behavior.page_views += 1
                    if 'product_view' in event_type:
                        behavior.product_views += 1
                    if 'search' in event_type:
                        behavior.searches += 1
                    if 'add_to_cart' in event_type:
                        behavior.add_to_carts += 1
                    if 'purchase' in event_type:
                        behavior.purchases += 1
                        revenue = event.get('revenue', 0) or 0
                        behavior.total_revenue += float(revenue)
                
                behavior.last_activity = datetime.utcnow()
                behavior.updated_at = datetime.utcnow()
            
            await db_session.commit()
            return True
            
        except Exception as e:
            logger.error("Error aggregating user behavior", error=str(e))
            await db_session.rollback()
            return False
        finally:
            await db_session.close()
    
    async def aggregate_session_analytics(
        self,
        events: List[Dict[str, Any]],
        merchant_id: int
    ) -> bool:
        """
        Aggregate session analytics
        
        Args:
            events: List of event dictionaries
            merchant_id: Merchant ID
            
        Returns:
            True if aggregation was successful
        """
        # Session analytics are updated in real-time by SessionTracker
        # This method can be used for batch updates if needed
        return True
    
    async def update_real_time_metrics(self) -> bool:
        """
        Update real-time metrics cache
        
        Returns:
            True if update was successful
        """
        # Real-time metrics are updated by RealTimeAnalyticsEngine
        # This method can be used for additional real-time updates if needed
        return True

