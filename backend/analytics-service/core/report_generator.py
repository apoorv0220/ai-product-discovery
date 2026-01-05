"""
AI Product Discovery Suite - Report Generator Service

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog

from core.dashboard_queries import DashboardQueryService

logger = structlog.get_logger()


class ReportGenerator:
    """Service for generating analytics reports with proper data aggregation and formatting"""
    
    def __init__(self):
        self.query_service = DashboardQueryService()
    
    async def generate_performance_report(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate performance report with traffic, engagement, conversion funnel, and revenue metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with performance report data
        """
        try:
            # Default to last 30 days if no date range specified
            if not date_to:
                date_to = datetime.utcnow()
            if not date_from:
                date_from = date_to - timedelta(days=30)
            
            # Get overview metrics
            overview = await self.query_service.get_overview_metrics(
                merchant_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Get previous period for comparison
            period_duration = date_to - date_from
            previous_date_from = date_from - period_duration
            previous_date_to = date_from
            
            previous_overview = await self.query_service.get_overview_metrics(
                merchant_id,
                date_from=previous_date_from,
                date_to=previous_date_to
            )
            
            # Get session analytics for engagement metrics
            session_data = await self.query_service.get_session_analytics(
                merchant_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Calculate conversion funnel
            funnel = {
                'page_views': overview.get('page_views', 0),
                'searches': overview.get('searches', 0),
                'product_views': overview.get('product_views', 0),
                'purchases': overview.get('purchases', 0)
            }
            
            # Calculate funnel conversion rates
            funnel_rates = {}
            if funnel['page_views'] > 0:
                funnel_rates['search_rate'] = funnel['searches'] / funnel['page_views']
                funnel_rates['product_view_rate'] = funnel['product_views'] / funnel['page_views']
                funnel_rates['purchase_rate'] = funnel['purchases'] / funnel['page_views']
            else:
                funnel_rates = {
                    'search_rate': 0.0,
                    'product_view_rate': 0.0,
                    'purchase_rate': 0.0
                }
            
            # Calculate revenue metrics
            revenue = overview.get('revenue', 0.0)
            purchases = overview.get('purchases', 0)
            unique_users = overview.get('unique_users', 0)
            
            avg_order_value = revenue / purchases if purchases > 0 else 0.0
            revenue_per_user = revenue / unique_users if unique_users > 0 else 0.0
            
            # Calculate period-over-period changes
            def calculate_change(current: float, previous: float) -> Dict[str, Any]:
                if previous == 0:
                    return {'value': current, 'change': 0.0, 'change_percent': 0.0 if current == 0 else 100.0}
                change = current - previous
                change_percent = (change / previous) * 100
                return {
                    'value': current,
                    'previous': previous,
                    'change': change,
                    'change_percent': change_percent
                }
            
            # Build report
            report = {
                'report_type': 'performance',
                'period': {
                    'start': date_from.isoformat(),
                    'end': date_to.isoformat(),
                    'previous_start': previous_date_from.isoformat(),
                    'previous_end': previous_date_to.isoformat()
                },
                'traffic': {
                    'page_views': calculate_change(
                        overview.get('page_views', 0),
                        previous_overview.get('page_views', 0)
                    ),
                    'unique_visitors': calculate_change(
                        overview.get('unique_users', 0),
                        previous_overview.get('unique_users', 0)
                    ),
                    'sessions': calculate_change(
                        overview.get('unique_sessions', 0),
                        previous_overview.get('unique_sessions', 0)
                    )
                },
                'engagement': {
                    'avg_session_duration': session_data.get('avg_duration', 0.0),
                    'bounce_rate': session_data.get('bounce_rate', 0.0),
                    'pages_per_session': (
                        overview.get('page_views', 0) / session_data.get('total_sessions', 1)
                        if session_data.get('total_sessions', 0) > 0 else 0.0
                    )
                },
                'conversion_funnel': {
                    'funnel': funnel,
                    'funnel_rates': funnel_rates,
                    'conversion_rate': overview.get('conversion_rate', 0.0)
                },
                'revenue': {
                    'total_revenue': revenue,
                    'average_order_value': avg_order_value,
                    'revenue_per_user': revenue_per_user,
                    'total_orders': purchases,
                    'revenue_change': calculate_change(
                        revenue,
                        previous_overview.get('revenue', 0.0)
                    )
                },
                'generated_at': datetime.utcnow().isoformat(),
                'merchant_id': merchant_id
            }
            
            logger.info(
                "Performance report generated",
                merchant_id=merchant_id,
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat()
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "Error generating performance report",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def generate_user_behavior_report(
        self,
        merchant_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate user behavior report with segmentation, patterns, and engagement metrics
        
        Args:
            merchant_id: Merchant ID
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with user behavior report data
        """
        try:
            # Default to last 30 days if no date range specified
            if not date_to:
                date_to = datetime.utcnow()
            if not date_from:
                date_from = date_to - timedelta(days=30)
            
            # Get user behavior metrics
            user_data = await self.query_service.get_user_behavior_metrics(
                merchant_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Get overview for additional context
            overview = await self.query_service.get_overview_metrics(
                merchant_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Get session analytics
            session_data = await self.query_service.get_session_analytics(
                merchant_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Calculate user segmentation breakdown
            # This is a foundation - will be enhanced in Phase 2.3
            total_users = user_data.get('total_users', 0)
            new_users = user_data.get('new_users', 0)
            returning_users = user_data.get('returning_users', 0)
            
            segmentation = {
                'total_users': total_users,
                'new_users': {
                    'count': new_users,
                    'percentage': (new_users / total_users * 100) if total_users > 0 else 0.0
                },
                'returning_users': {
                    'count': returning_users,
                    'percentage': (returning_users / total_users * 100) if total_users > 0 else 0.0
                }
            }
            
            # Behavioral patterns (foundation - can be enhanced with top pages, queries, etc.)
            behavioral_patterns = {
                'avg_events_per_user': user_data.get('avg_events_per_user', 0.0),
                'avg_session_duration': session_data.get('avg_duration', 0.0),
                'device_preference': session_data.get('sessions_by_device', {}),
                'platform_preference': session_data.get('sessions_by_platform', {})
            }
            
            # Engagement metrics
            engagement = {
                'avg_events_per_user': user_data.get('avg_events_per_user', 0.0),
                'avg_session_duration': session_data.get('avg_duration', 0.0),
                'bounce_rate': session_data.get('bounce_rate', 0.0),
                'total_events': overview.get('total_events', 0),
                'total_sessions': session_data.get('total_sessions', 0)
            }
            
            # Retention patterns
            retention = {
                'new_users': new_users,
                'returning_users': returning_users,
                'retention_rate': (returning_users / total_users * 100) if total_users > 0 else 0.0
            }
            
            # Build report
            report = {
                'report_type': 'user_behavior',
                'period': {
                    'start': date_from.isoformat(),
                    'end': date_to.isoformat()
                },
                'user_segmentation': segmentation,
                'behavioral_patterns': behavioral_patterns,
                'engagement_metrics': engagement,
                'retention_patterns': retention,
                'generated_at': datetime.utcnow().isoformat(),
                'merchant_id': merchant_id
            }
            
            logger.info(
                "User behavior report generated",
                merchant_id=merchant_id,
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat()
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "Error generating user behavior report",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True
            )
            raise

