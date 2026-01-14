"""
AI Product Discovery Suite - Celery App Configuration

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from celery import Celery, signals
import os
import structlog

logger = structlog.get_logger()

# Create Celery app
app = Celery('discovery_suite')

# Import beat schedule
try:
    from shared.celery.beat_schedule import beat_schedule
except ImportError:
    beat_schedule = {}

# Configure Celery
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Task routing
    task_routes={
        'analytics.*': {'queue': 'analytics'},
        'shared.tasks.analytics.*': {'queue': 'analytics'},
    },
    # Task priorities (higher number = higher priority)
    task_default_priority=5,
    task_inherit_parent_priority=True,
    # Result backend expiration
    result_expires=3600,  # 1 hour
    # Worker concurrency
    worker_concurrency=int(os.getenv('CELERY_WORKER_CONCURRENCY', '4')),
    # Task acknowledgment
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule for periodic tasks
    beat_schedule=beat_schedule,
)

# Task monitoring hooks
@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info("Task starting", task_id=task_id, task_name=task.name if task else None)

@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    logger.info("Task completed", task_id=task_id, task_name=task.name if task else None, state=state)

@signals.task_success.connect
def task_success_handler(sender=None, result=None, **kwds):
    """Log task success"""
    logger.info("Task succeeded", task_name=sender.name if sender else None)

@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failure"""
    logger.error("Task failed", 
                task_id=task_id,
                task_name=sender.name if sender else None,
                exception=str(exception) if exception else None)

@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Log task retry"""
    logger.warning("Task retrying", 
                  task_id=task_id,
                  task_name=sender.name if sender else None,
                  reason=str(reason) if reason else None)

# Auto-discover tasks
app.autodiscover_tasks([
    'shared.tasks',
])

if __name__ == '__main__':
    app.start()