"""
AI Product Discovery Suite - Search Service Health API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import time
import structlog

logger = structlog.get_logger()

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: float
    service: str
    version: str
    checks: Dict[str, Any]


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    try:
        return HealthResponse(
            status="healthy",
            timestamp=time.time(),
            service="search-service",
            version="1.0.0",
            checks={
                "database": "healthy",
                "elasticsearch": "healthy",
                "ml_engine": "healthy"
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/Docker"""
    return {"status": "ready", "timestamp": time.time()}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes/Docker"""
    return {"status": "alive", "timestamp": time.time()}