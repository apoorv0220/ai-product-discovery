"""
AI Product Discovery Suite - Analytics Tasks

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import asyncio
from shared.celery.app import app
from shared.config.redis import analytics_buffer
import structlog

logger = structlog.get_logger()


@app.task(bind=True)
def process_analytics_batch(self):
    """
    Process a batch of analytics events from Redis queue
    
    This task is called periodically (e.g., every 30 seconds) to process
    buffered events from the Redis queue.
    """
    try:
        # Get events from buffer
        events_batch = analytics_buffer.get_buffered_events(batch_size=100)
        
        if not events_batch:
            logger.debug("No events to process")
            return {"success": True, "processed": 0}
        
        logger.info("Processing analytics batch", count=len(events_batch))
        
        # Import here to avoid circular dependencies
        import sys
        import os
        # Add analytics-service to path
        analytics_service_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'analytics-service')
        if analytics_service_path not in sys.path:
            sys.path.insert(0, analytics_service_path)
        from core.aggregator import DataAggregator
        
        # Create aggregator and process events
        aggregator = DataAggregator()
        
        # Run async aggregation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(aggregator.aggregate_events(events_batch))
            if not success:
                raise Exception("Aggregation failed")
        finally:
            loop.close()
        
        logger.info("Analytics batch processed", count=len(events_batch))
        return {"success": True, "processed": len(events_batch)}
        
    except Exception as e:
        logger.error("Analytics batch processing failed", error=str(e))
        raise self.retry(exc=e, countdown=30, max_retries=2)