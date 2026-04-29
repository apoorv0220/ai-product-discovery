"""
AI Product Discovery Suite - Catalog Sync Tasks

This module provides Celery tasks for synchronizing the product catalog
from Magento to the search service (Elasticsearch + Qdrant).

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from shared.celery.app import app
import structlog
import subprocess
import os
from datetime import datetime

logger = structlog.get_logger()


@app.task(bind=True)
def sync_product_catalog(self, store_id=1, batch_size=100, full_reindex=False):
    """
    Sync product catalog from Magento to search and recommendation services
    
    This task calls the Magento CLI command that handles the actual product
    extraction and sending to the search service API.
    
    Args:
        store_id: Store ID to sync (default: 1)
        batch_size: Number of products per batch (default: 100)
        full_reindex: Whether to do full reindex (default: False)
    
    Returns:
        dict: Sync result with success status and message
    """
    try:
        logger.info("Starting catalog sync",
                   store_id=store_id,
                   batch_size=batch_size,
                   full_reindex=full_reindex,
                   start_time=datetime.utcnow().isoformat())
        
        # Get Magento path from environment
        magento_path = os.getenv('MAGENTO_PATH', '/var/www/magento')
        
        # Build command to call Magento sync CLI
        cmd = [
            'php',
            f'{magento_path}/bin/magento',
            'vendor:discoverysuite:sync-catalog',
            f'--store-id={store_id}',
            f'--batch-size={batch_size}'
        ]
        
        logger.info("Executing Magento sync command",
                   command=' '.join(cmd))
        
        # Execute the Magento CLI command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("Catalog sync completed successfully",
                       store_id=store_id,
                       stdout=result.stdout[:500],  # Log first 500 chars
                       end_time=datetime.utcnow().isoformat())
            
            return {
                "success": True,
                "message": "Catalog sync completed successfully",
                "store_id": store_id,
                "output": result.stdout
            }
        else:
            error_msg = result.stderr or result.stdout
            logger.error("Catalog sync command failed",
                        store_id=store_id,
                        returncode=result.returncode,
                        error=error_msg[:500])
            
            # Retry on failure
            raise self.retry(
                exc=Exception(f"Sync command failed: {error_msg}"),
                countdown=60,
                max_retries=3
            )
        
    except subprocess.TimeoutExpired:
        logger.error("Catalog sync timed out",
                    store_id=store_id,
                    timeout=3600)
        raise self.retry(exc=Exception("Sync timeout"), countdown=120, max_retries=2)
        
    except FileNotFoundError as e:
        logger.error("Magento CLI not found",
                    magento_path=magento_path,
                    error=str(e))
        return {
            "success": False,
            "message": f"Magento CLI not found at {magento_path}. Set MAGENTO_PATH environment variable.",
            "error": str(e)
        }
        
    except Exception as e:
        logger.error("Catalog sync failed",
                    store_id=store_id,
                    error=str(e),
                    error_type=type(e).__name__)
        
        # Retry on generic failures
        raise self.retry(exc=e, countdown=60, max_retries=3)


@app.task(bind=True)
def incremental_catalog_sync(self, store_id=1):
    """
    Perform incremental catalog sync (only changed products)
    
    This is a lighter-weight sync that only updates products that have
    changed since the last sync.
    
    Args:
        store_id: Store ID to sync (default: 1)
    
    Returns:
        dict: Sync result
    """
    try:
        logger.info("Starting incremental catalog sync", store_id=store_id)
        
        # For now, call the full sync with smaller batch size
        # In future, this could check last_synced_at and only sync changed products
        return sync_product_catalog(
            store_id=store_id,
            batch_size=50,
            full_reindex=False
        )
        
    except Exception as e:
        logger.error("Incremental sync failed", store_id=store_id, error=str(e))
        raise self.retry(exc=e, countdown=60, max_retries=3)


@app.task
def schedule_periodic_sync():
    """
    Schedule periodic catalog syncs
    
    This task can be called by Celery Beat to schedule regular syncs.
    Configure in celeryconfig.py:
    
    beat_schedule = {
        'sync-catalog-hourly': {
            'task': 'shared.tasks.catalog_sync.schedule_periodic_sync',
            'schedule': crontab(minute=0),  # Every hour
        },
    }
    """
    logger.info("Triggering scheduled catalog sync")
    
    # Get list of stores to sync from environment or config
    # For now, just sync store 1
    stores_to_sync = [1]
    
    for store_id in stores_to_sync:
        # Call incremental sync for each store
        incremental_catalog_sync.delay(store_id=store_id)
    
    return {"success": True, "stores_synced": stores_to_sync}