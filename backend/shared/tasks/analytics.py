"""
AI Product Discovery Suite - Analytics Tasks

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from shared.celery.app import app
from shared.config.redis import analytics_buffer
import structlog

logger = structlog.get_logger()


def _get_analytics_service_path():
    """Get analytics service path for imports"""
    import sys
    import os
    # Get to backend directory from backend/shared/tasks/analytics.py
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    analytics_service_path = os.path.join(backend_dir, 'analytics-service')
    if analytics_service_path not in sys.path:
        sys.path.insert(0, analytics_service_path)
    return analytics_service_path


def _run_async(coro):
    """Run async function in new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(bind=True, name='analytics.process_batch', queue='analytics', max_retries=3, default_retry_delay=30)
def process_analytics_batch(self):
    """
    Process a batch of analytics events from Redis queue
    """
    async def _internal_process():
        from shared.database.base import engine
        try:
            # Get events from buffer
            events_batch = analytics_buffer.get_buffered_events(batch_size=100)
            
            if not events_batch:
                logger.debug("No events to process")
                return {"success": True, "processed": 0}
            
            logger.info("Processing analytics batch", count=len(events_batch))
            
            # Import here to avoid circular dependencies
            _get_analytics_service_path()
            from core.aggregator import DataAggregator
            
            # Create aggregator and process events
            aggregator = DataAggregator()
            
            # Run aggregation
            success = await aggregator.aggregate_events(events_batch)
            if not success:
                raise Exception("Aggregation failed")
            
            logger.info("Analytics batch processed", count=len(events_batch))
            return {"success": True, "processed": len(events_batch)}
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_process())
    except Exception as e:
        logger.error("Analytics batch processing failed", error=str(e), exc_info=True)
        # Exponential backoff: 30s, 60s, 120s
        retry_countdown = 30 * (2 ** (self.request.retries or 0))
        raise self.retry(exc=e, countdown=min(retry_countdown, 300), max_retries=3)


@app.task(bind=True, name='analytics.aggregate_time_series', queue='analytics', max_retries=2)
def aggregate_time_series(self, aggregation_type: str, merchant_id: int = None):
    """
    Periodic time-series aggregation (5min, hourly, daily)
    """
    async def _internal_aggregate():
        from shared.database.base import engine, AsyncSessionLocal
        nonlocal merchant_id
        try:
            logger.info("Starting time-series aggregation", aggregation_type=aggregation_type, merchant_id=merchant_id)
            
            _get_analytics_service_path()
            from core.aggregator import DataAggregator
            from shared.models.analytics import AnalyticsEvent
            from sqlalchemy import select, and_
            
            aggregator = DataAggregator()
            
            # Determine time window based on aggregation type
            now = datetime.utcnow()
            if aggregation_type == 'real_time':
                window_size = timedelta(minutes=5)
                window_start = now.replace(second=0, microsecond=0) - timedelta(minutes=5)
            elif aggregation_type == 'hourly':
                window_size = timedelta(hours=1)
                window_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
            elif aggregation_type == 'daily':
                window_size = timedelta(days=1)
                window_start = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1))
            else:
                logger.warning("Unknown aggregation type", aggregation_type=aggregation_type)
                return {"success": False, "error": "Unknown aggregation type"}
            
            # Get events for the time window
            db_session = AsyncSessionLocal()
            try:
                query = select(AnalyticsEvent).where(
                    and_(
                        AnalyticsEvent.timestamp >= window_start,
                        AnalyticsEvent.timestamp < window_start + window_size
                    )
                )
                if merchant_id:
                    query = query.where(AnalyticsEvent.merchant_id == merchant_id)
                
                result = await db_session.execute(query)
                events = result.scalars().all()
                
                # Convert to dict format
                events_list = []
                for event in events:
                    events_list.append({
                        'event_id': str(event.event_id),
                        'event_type': event.event_type,
                        'merchant_id': event.merchant_id,
                        'user_id': event.user_id,
                        'session_id': event.session_id,
                        'product_id': event.product_id,
                        'revenue': event.revenue,
                        'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                        'properties': event.properties or {}
                    })
                
                if not events_list:
                    logger.debug("No events found for aggregation", aggregation_type=aggregation_type, window_start=window_start)
                    return {"success": True, "processed": 0}
                
                # Aggregate events
                if not merchant_id:
                    merchant_id = events_list[0].get('merchant_id')
                
                if not merchant_id:
                    logger.warning("No merchant_id available for aggregation", aggregation_type=aggregation_type)
                    return {"success": False, "error": "No merchant_id available"}
                
                success = await aggregator.aggregate_by_time_window(
                    events_list,
                    merchant_id,
                    aggregation_type,
                    window_size
                )
                
                logger.info("Time-series aggregation completed", 
                           aggregation_type=aggregation_type, 
                           events_count=len(events_list),
                           success=success)
                
                return {"success": success, "processed": len(events_list), "aggregation_type": aggregation_type}
            finally:
                await db_session.close()
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_aggregate())
    except Exception as e:
        logger.error("Time-series aggregation failed", 
                    error=str(e), 
                    aggregation_type=aggregation_type,
                    exc_info=True)
        raise self.retry(exc=e, countdown=60, max_retries=2)


@app.task(bind=True, name='analytics.update_dashboard_cache', queue='analytics', max_retries=2)
def update_dashboard_cache(self, merchant_id: int = None):
    """
    Real-time dashboard cache updates
    """
    async def _internal_update():
        from shared.database.base import engine, AsyncSessionLocal
        try:
            logger.info("Updating dashboard cache", merchant_id=merchant_id)
            
            _get_analytics_service_path()
            from core.dashboard_cache import DashboardCache
            from core.dashboard_queries import DashboardQueryService
            
            cache = DashboardCache()
            queries = DashboardQueryService()
            
            # Get all merchants if merchant_id not specified
            db_session = AsyncSessionLocal()
            try:
                if merchant_id:
                    merchants = [merchant_id]
                else:
                    from shared.models import Merchant
                    from sqlalchemy import select
                    result = await db_session.execute(select(Merchant.id))
                    merchants = [row[0] for row in result.fetchall()]
            finally:
                await db_session.close()
            
            updated_count = 0
            for merch_id in merchants:
                try:
                    # Get overview data
                    now = datetime.utcnow()
                    overview = await queries.get_overview_metrics(
                        merch_id,
                        date_from=now - timedelta(hours=24),
                        date_to=now
                    )
                    if overview:
                        await cache.set('overview', merch_id, overview, ttl=120)  # 2 minutes TTL
                    
                    # Get recent metrics (time-series) for key metrics
                    for metric_name in ['page_views', 'product_views', 'searches', 'purchases']:
                        metrics = await queries.get_time_series_data(
                            merchant_id=merch_id,
                            metric_name=metric_name,
                            period='hour',
                            date_from=now - timedelta(hours=24),
                            date_to=now
                        )
                        if metrics:
                            await cache.set(f'metrics_{metric_name}', merch_id, metrics, 
                                                date_from=now - timedelta(hours=24),
                                                date_to=now,
                                                period='hour',
                                                ttl=120)
                    
                    updated_count += 1
                except Exception as e:
                    logger.warning("Failed to update cache for merchant", 
                                 merchant_id=merch_id, 
                                 error=str(e))
            
            logger.info("Dashboard cache updated", merchants_updated=updated_count)
            return {"success": True, "merchants_updated": updated_count}
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_update())
    except Exception as e:
        logger.error("Dashboard cache update failed", error=str(e), exc_info=True)
        raise self.retry(exc=e, countdown=30, max_retries=2)


@app.task(bind=True, name='analytics.enrich_events_batch', queue='analytics', max_retries=2)
def enrich_events_batch(self, events: List[Dict[str, Any]]):
    """
    Batch event enrichment
    """
    async def _internal_enrich():
        from shared.database.base import engine
        try:
            if not events:
                return {"success": True, "processed": 0}
            
            logger.info("Enriching events batch", count=len(events))
            
            _get_analytics_service_path()
            from core.event_enricher import event_enricher
            
            enriched_count = 0
            for event in events:
                try:
                    enriched = await event_enricher.enrich_event(event)
                    if enriched:
                        enriched_count += 1
                except Exception as e:
                    logger.warning("Failed to enrich event", event_id=event.get('event_id'), error=str(e))
            
            logger.info("Events batch enriched", total=len(events), enriched=enriched_count)
            return {"success": True, "processed": len(events), "enriched": enriched_count}
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_enrich())
    except Exception as e:
        logger.error("Event enrichment batch failed", error=str(e), exc_info=True)
        raise self.retry(exc=e, countdown=30, max_retries=2)


@app.task(bind=True, name='analytics.stitch_user_history', queue='analytics', max_retries=3)
def stitch_user_history(self, merchant_id: int, session_id: str, user_id: str):
    """
    Background task to stitch historical sessions to a user ID via device fingerprint
    """
    async def _internal_stitch():
        from shared.database.base import engine, AsyncSessionLocal
        from sqlalchemy import select, update, and_
        
        try:
            logger.info("Starting background identity stitching", 
                        merchant_id=merchant_id, 
                        session_id=session_id, 
                        user_id=user_id)
            
            _get_analytics_service_path()
            from shared.models.analytics import AnalyticsEvent, SessionAnalytics
            
            async with AsyncSessionLocal() as db_session:
                # 1. Find the device fingerprint for the current session
                fp_query = select(AnalyticsEvent.properties['device_fingerprint'].astext).where(
                    and_(
                        AnalyticsEvent.merchant_id == merchant_id,
                        AnalyticsEvent.session_id == session_id,
                        AnalyticsEvent.properties.has_key('device_fingerprint')
                    )
                ).limit(1)
                
                result = await db_session.execute(fp_query)
                fingerprint = result.scalar()
                
                if not fingerprint:
                    logger.debug("No fingerprint found for session, skipping historical stitching", 
                                 session_id=session_id)
                    return {"success": True, "status": "no_fingerprint"}
                
                # 2. Find all other sessions with this fingerprint that don't have a user_id
                other_sessions_query = select(AnalyticsEvent.session_id).where(
                    and_(
                        AnalyticsEvent.merchant_id == merchant_id,
                        AnalyticsEvent.properties['device_fingerprint'].astext == fingerprint,
                        AnalyticsEvent.user_id.is_(None)
                    )
                ).distinct()
                
                result = await db_session.execute(other_sessions_query)
                session_ids = [row[0] for row in result.fetchall() if row[0]]
                
                if not session_ids:
                    return {"success": True, "status": "no_other_sessions"}
                
                logger.info("Stitching historical sessions", 
                            count=len(session_ids), 
                            fingerprint=fingerprint)
                
                # 3. Batch update all events and sessions
                await db_session.execute(
                    update(AnalyticsEvent)
                    .where(and_(
                        AnalyticsEvent.merchant_id == merchant_id,
                        AnalyticsEvent.session_id.in_(session_ids),
                        AnalyticsEvent.user_id.is_(None)
                    ))
                    .values(user_id=user_id)
                )
                
                await db_session.execute(
                    update(SessionAnalytics)
                    .where(and_(
                        SessionAnalytics.merchant_id == merchant_id,
                        SessionAnalytics.session_id.in_(session_ids),
                        SessionAnalytics.user_id.is_(None)
                    ))
                    .values(user_id=user_id)
                )
                
                await db_session.commit()
                return {"success": True, "stitched_sessions": len(session_ids)}
                
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_stitch())
    except Exception as e:
        logger.error("Identity stitching failed", error=str(e), exc_info=True)
        raise self.retry(exc=e, countdown=60, max_retries=3)


@app.task(bind=True, name='analytics.calculate_product_affinities', queue='analytics', max_retries=2)
def calculate_product_affinities(self, merchant_id: int):
    """
    Periodic task to calculate product-to-product affinities based on co-occurrence
    """
    async def _internal_calculate():
        from shared.database.base import engine
        try:
            logger.info("Starting product affinity calculation", merchant_id=merchant_id)
            
            _get_analytics_service_path()
            from core.stats_engine import AffinityCalculator
            
            calculator = AffinityCalculator()
            success = await calculator.calculate_all_affinities(merchant_id)
            
            return {"success": success, "merchant_id": merchant_id}
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_calculate())
    except Exception as e:
        logger.error("Product affinity calculation failed", error=str(e), exc_info=True)
        raise self.retry(exc=e, countdown=300, max_retries=2)


@app.task(bind=True, name='analytics.generate_report_task', queue='analytics', max_retries=1)
def generate_report_task(self, merchant_id: int, report_type: str, date_from: str = None, date_to: str = None):
    """
    Asynchronous task to generate a complex analytics report
    """
    async def _internal_generate():
        from shared.database.base import engine
        from datetime import datetime
        try:
            logger.info("Starting async report generation", 
                        merchant_id=merchant_id, 
                        report_type=report_type)
            
            _get_analytics_service_path()
            from core.report_generator import ReportGenerator
            
            # Parse dates if provided
            d_from = datetime.fromisoformat(date_from) if date_from else None
            d_to = datetime.fromisoformat(date_to) if date_to else None
            
            generator = ReportGenerator()
            
            if report_type == 'performance':
                report = await generator.generate_performance_report(merchant_id, d_from, d_to)
            elif report_type == 'user_behavior':
                report = await generator.generate_user_behavior_report(merchant_id, d_from, d_to)
            else:
                return {"success": False, "error": f"Unknown report type: {report_type}"}
            
            # In a real system, we'd save this to a 'reports' table or S3
            # For POC, we'll cache it in Redis for the API to pick up
            from shared.config.redis import CacheManager
            cache = CacheManager()
            report_id = f"report:{merchant_id}:{report_type}:{datetime.utcnow().timestamp()}"
            await cache.aset(report_id, report, ttl=3600)
            
            return {"success": True, "report_id": report_id}
        finally:
            await engine.dispose()

    try:
        return _run_async(_internal_generate())
    except Exception as e:
        logger.error("Report generation task failed", error=str(e), exc_info=True)
        raise self.retry(exc=e, countdown=60)

#Heartbeat task to monitor worker health and connectivity
# @app.task(name='analytics.heartbeat', queue='analytics')
# def analytics_heartbeat():
#     """Lightweight heartbeat task to monitor worker health and connectivity"""
#     async def _internal_heartbeat():
#         from shared.database.base import engine, AsyncSessionLocal
#         from sqlalchemy import text
#         try:
#             # Check database connectivity
#             async with AsyncSessionLocal() as session:
#                 await session.execute(text("SELECT 1"))

#             logger.info("Analytics heartbeat successful",
#                         timestamp=datetime.utcnow().isoformat())
#             return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
#         except Exception as e:
#             logger.error("Analytics heartbeat failed", error=str(e))
#             return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
#         finally:
#             await engine.dispose()

#     return _run_async(_internal_heartbeat())
