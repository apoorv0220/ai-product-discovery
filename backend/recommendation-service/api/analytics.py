"""
AI Product Discovery Suite - Recommendation Service Analytics API

@category    Backend
@package     RecommendationService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/performance")
async def get_recommendation_performance(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    http_request: Request = None
):
    """
    Get recommendation performance metrics
    
    Args:
        start_date: Start date for the analytics period
        end_date: End date for the analytics period
        http_request: FastAPI request object
        
    Returns:
        Recommendation performance metrics
    """
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        logger.info(
            "Getting recommendation performance",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Get performance metrics
        performance = await recommendation_engine.get_performance_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info("Recommendation performance retrieved")
        
        return performance
        
    except Exception as e:
        logger.error("Error getting recommendation performance", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendation performance: {str(e)}"
        )


@router.get("/conversion")
async def get_conversion_metrics(
    algorithm: Optional[str] = Query(None, description="Filter by algorithm"),
    context: Optional[str] = Query(None, description="Filter by context"),
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    http_request: Request = None
):
    """
    Get recommendation conversion metrics
    
    Args:
        algorithm: Filter by specific algorithm
        context: Filter by recommendation context
        days: Number of days to analyze
        http_request: FastAPI request object
        
    Returns:
        Conversion metrics
    """
    try:
        logger.info(
            "Getting conversion metrics",
            algorithm=algorithm,
            context=context,
            days=days
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Get conversion metrics
        conversion_data = await recommendation_engine.get_conversion_metrics(
            algorithm=algorithm,
            context=context,
            days=days
        )
        
        logger.info("Conversion metrics retrieved")
        
        return conversion_data
        
    except Exception as e:
        logger.error("Error getting conversion metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversion metrics: {str(e)}"
        )


@router.get("/popular")
async def get_popular_recommendations(
    time_period: Optional[str] = Query("24h", description="Time period (1h, 24h, 7d, 30d)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: Optional[int] = Query(20, description="Number of popular items to return"),
    http_request: Request = None
):
    """
    Get most popular recommended products
    
    Args:
        time_period: Time period for popularity analysis
        category: Filter by product category
        limit: Maximum number of items to return
        http_request: FastAPI request object
        
    Returns:
        List of popular recommended products
    """
    try:
        logger.info(
            "Getting popular recommendations",
            time_period=time_period,
            category=category,
            limit=limit
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Get popular recommendations
        popular_items = await recommendation_engine.get_popular_recommendations(
            time_period=time_period,
            category=category,
            limit=limit
        )
        
        logger.info("Popular recommendations retrieved")
        
        return popular_items
        
    except Exception as e:
        logger.error("Error getting popular recommendations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get popular recommendations: {str(e)}"
        )


@router.get("/model/accuracy")
async def get_model_accuracy(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    days: Optional[int] = Query(7, description="Number of days to analyze"),
    http_request: Request = None
):
    """
    Get ML model accuracy metrics
    
    Args:
        model_name: Filter by specific model
        days: Number of days to analyze
        http_request: FastAPI request object
        
    Returns:
        Model accuracy metrics
    """
    try:
        logger.info(
            "Getting model accuracy",
            model_name=model_name,
            days=days
        )
        
        # Get ML models manager from app state
        ml_models = http_request.app.state.ml_models
        
        # Get model accuracy
        accuracy_data = await ml_models.get_accuracy_metrics(
            model_name=model_name,
            days=days
        )
        
        logger.info("Model accuracy retrieved")
        
        return accuracy_data
        
    except Exception as e:
        logger.error("Error getting model accuracy", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model accuracy: {str(e)}"
        )


@router.post("/retrain")
async def trigger_model_retrain(
    model_name: str = Query(..., description="Name of the model to retrain"),
    force: bool = Query(False, description="Force retrain even if not scheduled"),
    http_request: Request = None
):
    """
    Trigger model retraining
    
    Args:
        model_name: Name of the model to retrain
        force: Force retrain even if not scheduled
        http_request: FastAPI request object
        
    Returns:
        Retrain status
    """
    try:
        logger.info(
            "Triggering model retrain",
            model_name=model_name,
            force=force
        )
        
        # Get ML models manager from app state
        ml_models = http_request.app.state.ml_models
        
        # Trigger retrain
        retrain_result = await ml_models.trigger_retrain(
            model_name=model_name,
            force=force
        )
        
        logger.info("Model retrain triggered", model_name=model_name)
        
        return retrain_result
        
    except Exception as e:
        logger.error("Error triggering model retrain", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger model retrain: {str(e)}"
        )