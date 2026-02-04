from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from shared.middleware.auth import get_merchant_id
from shared.database.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.funnels import FunnelCreate, FunnelResponse, FunnelAnalyticsResponse
from core.funnel_service import FunnelService

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/", response_model=FunnelResponse, status_code=status.HTTP_201_CREATED)
async def create_funnel(
    request: Request,
    funnel_data: FunnelCreate,
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = FunnelService(db)
    try:
        funnel = await service.create_funnel(merchant_id, funnel_data.dict())
        return funnel
    except Exception as e:
        logger.error("Error creating funnel", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create funnel")

@router.get("/", response_model=List[FunnelResponse])
async def list_funnels(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = FunnelService(db)
    return await service.get_funnels(merchant_id)

@router.get("/{funnel_id}/analytics", response_model=FunnelAnalyticsResponse)
async def get_funnel_analytics(
    request: Request,
    funnel_id: int,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = FunnelService(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    analytics = await service.get_funnel_analytics(funnel_id, merchant_id, start_date, end_date)
    if not analytics:
        raise HTTPException(status_code=404, detail="Funnel not found")
        
    return analytics
