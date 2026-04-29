"""
AI Product Discovery Suite - Performance Metrics API

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request
from typing import Dict, Any
import time
import structlog
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import Counter, Histogram, Gauge

logger = structlog.get_logger()

router = APIRouter()

# Prometheus metrics
event_processing_latency = Histogram(
    'analytics_event_processing_latency_seconds',
    'Event processing latency in seconds',
    ['event_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

database_query_duration = Histogram(
    'analytics_database_query_duration_seconds',
    'Database query execution time in seconds',
    ['query_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

redis_operation_duration = Histogram(
    'analytics_redis_operation_duration_seconds',
    'Redis operation latency in seconds',
    ['operation_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

celery_task_duration = Histogram(
    'analytics_celery_task_duration_seconds',
    'Celery task execution time in seconds',
    ['task_name'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

events_processed_total = Counter(
    'analytics_events_processed_total',
    'Total number of events processed',
    ['event_type', 'status']
)

database_connections_active = Gauge(
    'analytics_database_connections_active',
    'Number of active database connections'
)

redis_queue_length = Gauge(
    'analytics_redis_queue_length',
    'Number of events in Redis queue'
)

memory_usage_bytes = Gauge(
    'analytics_memory_usage_bytes',
    'Memory usage in bytes'
)


@router.get("/prometheus")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    return generate_latest()


@router.get("/performance")
async def get_performance_metrics(request: Request) -> Dict[str, Any]:
    """
    Get performance metrics for monitoring
    
    Returns:
        Dictionary with key performance indicators
    """
    try:
        from shared.config.redis import analytics_buffer
        from shared.database.base import engine
        
        # Get Redis queue length
        queue_length = analytics_buffer.get_queue_length()
        redis_queue_length.set(queue_length)
        
        # Get database connection pool stats
        pool = engine.pool
        active_connections = pool.size() - pool.checkedout()
        database_connections_active.set(active_connections)
        
        # Get memory usage (approximate)
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_usage_bytes.set(memory_info.rss)
        
        return {
            "database": {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "active_connections": active_connections
            },
            "redis": {
                "queue_length": queue_length
            },
            "memory": {
                "rss_bytes": memory_info.rss,
                "vms_bytes": memory_info.vms,
                "percent": process.memory_percent()
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Error getting performance metrics", error=str(e))
        return {
            "error": str(e),
            "timestamp": time.time()
        }

