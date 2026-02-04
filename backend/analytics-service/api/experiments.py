from fastapi import APIRouter, Request, Query, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import structlog

from shared.middleware.auth import get_merchant_id
from shared.database.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.experiments import (
    ExperimentAssignmentsList, 
    ExperimentAssignmentResponse,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResultResponse
)
from core.experiment_service import ExperimentService

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: Request,
    experiment_data: ExperimentCreate,
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = ExperimentService(db)
    try:
        experiment = await service.create_experiment(merchant_id, experiment_data.dict())
        return experiment
    except Exception as e:
        logger.error("Error creating experiment", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create experiment")

@router.get("/", response_model=List[ExperimentResponse])
async def list_experiments(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = ExperimentService(db)
    return await service.get_experiments(merchant_id)

@router.get("/{experiment_id}/results", response_model=ExperimentResultResponse)
async def get_experiment_results(
    request: Request,
    experiment_id: int,
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    service = ExperimentService(db)
    results = await service.get_experiment_results(experiment_id, merchant_id)
    if not results:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return results

@router.get("/assign", response_model=ExperimentAssignmentsList,
           summary="Assign Variants",
           description="""
    Assign A/B test variants to a user based on their user_id or session_id.
    Uses consistent hashing to ensure stable assignments.
    
    **Parameters:**
    - `user_id`: Unique identifier for the user or session.
    """)
async def assign_variants(
    request: Request,
    user_id: str = Query(..., description="Unique user or session identifier"),
    db: AsyncSession = Depends(get_db)
):
    merchant_id = get_merchant_id(request)
    if not merchant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Merchant context not found"
        )
    
    logger.info("Assigning variants for user", user_id=user_id, merchant_id=merchant_id)
    
    try:
        service = ExperimentService(db)
        assignments = await service.get_assignments(merchant_id, user_id)
        
        return ExperimentAssignmentsList(
            assignments=[ExperimentAssignmentResponse(**a) for a in assignments],
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error("Error assigning variants", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign experiment variants"
        )
