"""
AI Product Discovery Suite - Celery Beat Schedule Configuration

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from celery.schedules import crontab

# Celery Beat schedule for periodic tasks
beat_schedule = {
    # Event aggregation every 5 minutes
    'aggregate-real-time': {
        'task': 'analytics.aggregate_time_series',
        'schedule': 300.0,  # Every 5 minutes
        'args': ('real_time',),
        'options': {'queue': 'analytics', 'priority': 7}
    },
    
    # Hourly aggregation at :00
    'aggregate-hourly': {
        'task': 'analytics.aggregate_time_series',
        'schedule': crontab(minute=0),  # Every hour at :00
        'args': ('hourly',),
        'options': {'queue': 'analytics', 'priority': 6}
    },
    
    # Daily aggregation at midnight UTC
    'aggregate-daily': {
        'task': 'analytics.aggregate_time_series',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight UTC
        'args': ('daily',),
        'options': {'queue': 'analytics', 'priority': 5}
    },
    
    # Dashboard cache refresh every 2 minutes
    'update-dashboard-cache': {
        'task': 'analytics.update_dashboard_cache',
        'schedule': 120.0,  # Every 2 minutes
        'options': {'queue': 'analytics', 'priority': 8}
    },
    
    # Process analytics batch every 30 seconds
    'process-analytics-batch': {
        'task': 'analytics.process_batch',
        'schedule': 30.0,  # Every 30 seconds
        'options': {'queue': 'analytics', 'priority': 9}
    },
    
    # Heartbeat task every 1 minute
    # 'analytics-heartbeat': {
    #     'task': 'analytics.heartbeat',
    #     'schedule': 60.0,  # Every minute
    #     'options': {'queue': 'analytics', 'priority': 10}
    # },
}

