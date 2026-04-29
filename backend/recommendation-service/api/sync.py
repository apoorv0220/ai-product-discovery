"""
Product Synchronization API for Recommendation Service
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import structlog

from core.simple_product_sync import simple_product_sync

logger = structlog.get_logger()
router = APIRouter()

@router.post("/products")
async def sync_products(request: Request = None):
    """
    Synchronize products from search index to recommendation database
    """
    try:
        logger.info("Starting product synchronization")
        
        # Sync products from search index
        sync_result = await simple_product_sync.sync_products_from_search_index()
        
        if sync_result["success"]:
            logger.info("Product synchronization successful", 
                       synced_count=sync_result["synced_count"])
            return {
                "success": True,
                "message": sync_result["message"],
                "synced_count": sync_result["synced_count"],
                "timestamp": sync_result.get("timestamp")
            }
        else:
            logger.error("Product synchronization failed", error=sync_result["message"])
            return {
                "success": False,
                "message": sync_result["message"],
                "synced_count": 0
            }
            
    except Exception as e:
        logger.error("Product sync endpoint error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Synchronization failed: {str(e)}"
        )

@router.get("/status")
async def get_sync_status(request: Request = None):
    """
    Get current synchronization status
    """
    try:
        status = await simple_product_sync.get_sync_status()
        return status
        
    except Exception as e:
        logger.error("Failed to get sync status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )
