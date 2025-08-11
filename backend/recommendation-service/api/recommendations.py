"""
AI Product Discovery Suite - Recommendation Service API

@category    Backend
@package     RecommendationService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional, Dict, Any
import structlog

from schemas.recommendations import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationItem,
    TrackingRequest,
    TrackingResponse
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    http_request: Request
):
    """
    Get product recommendations based on user context and preferences
    
    Args:
        request: Recommendation request with user context and filters
        http_request: FastAPI request object for accessing app state
        
    Returns:
        RecommendationResponse with recommended products
    """
    try:
        logger.info(
            "Getting recommendations",
            user_id=request.user_id,
            context=request.context,
            limit=request.limit
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Generate recommendations
        recommendations = await recommendation_engine.get_recommendations(
            user_id=request.user_id,
            context=request.context,
            product_ids=request.product_ids,
            category_ids=request.category_ids,
            limit=request.limit,
            filters=request.filters,
            exclude_viewed=request.exclude_viewed,
            exclude_purchased=request.exclude_purchased
        )
        
        # Convert to response format
        recommendation_items = [
            RecommendationItem(
                product_id=rec["product_id"],
                score=rec["score"],
                reason=rec["reason"],
                metadata=rec.get("metadata", {})
            )
            for rec in recommendations
        ]
        
        response = RecommendationResponse(
            recommendations=recommendation_items,
            user_id=request.user_id,
            context=request.context,
            total_count=len(recommendation_items),
            metadata={
                "algorithm": "collaborative_filtering_v2",
                "model_version": "1.0.0",
                "timestamp": recommendations[0].get("timestamp") if recommendations else None
            }
        )
        
        logger.info(
            "Recommendations generated",
            user_id=request.user_id,
            count=len(recommendation_items)
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Error generating recommendations",
            user_id=request.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.post("/similar", response_model=RecommendationResponse)
async def get_similar_products(
    request: dict,
    http_request: Request = None
):
    """
    Get products similar to a given product
    
    Args:
        request: Dictionary containing product_id and optional limit
        http_request: FastAPI request object
        
    Returns:
        RecommendationResponse with similar products
    """
    try:
        # Extract parameters from request body
        product_id = str(request.get('product_id', ''))
        limit = int(request.get('limit', 10))
        
        if not product_id:
            raise HTTPException(status_code=400, detail="product_id is required")
        
        logger.info(
            "Getting similar products",
            product_id=product_id,
            limit=limit
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Get similar products
        similar_products = await recommendation_engine.get_similar_products(
            product_id=product_id,
            limit=limit
        )
        
        # Convert to response format
        recommendation_items = [
            RecommendationItem(
                product_id=item["product_id"],
                score=item.get("similarity_score", item.get("score", 0.5)),  # Handle both field names
                reason=f"Similar to {product_id}",
                metadata=item.get("metadata", {})
            )
            for item in similar_products
        ]
        
        response = RecommendationResponse(
            recommendations=recommendation_items,
            context="similar_products",
            total_count=len(recommendation_items),
            metadata={
                "reference_product_id": product_id,
                "algorithm": "content_based_similarity",
                "model_version": "1.0.0"
            }
        )
        
        logger.info(
            "Similar products found",
            product_id=product_id,
            count=len(recommendation_items)
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Error getting similar products",
            product_id=product_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get similar products: {str(e)}"
        )


@router.post("/track", response_model=TrackingResponse)
async def track_recommendation_event(
    request: TrackingRequest,
    http_request: Request
):
    """
    Track user interaction with recommendations
    
    Args:
        request: Tracking request with event details
        http_request: FastAPI request object
        
    Returns:
        TrackingResponse confirming the event was tracked
    """
    try:
        logger.info(
            "Tracking recommendation event",
            user_id=request.user_id,
            event_type=request.event_type,
            product_id=request.product_id
        )
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Track the event
        tracking_result = await recommendation_engine.track_event(
            user_id=request.user_id,
            event_type=request.event_type,
            product_id=request.product_id,
            session_id=request.session_id,
            recommendation_id=request.recommendation_id,
            metadata=request.metadata
        )
        
        response = TrackingResponse(
            success=True,
            event_id=tracking_result["event_id"],
            message="Event tracked successfully"
        )
        
        logger.info(
            "Recommendation event tracked",
            user_id=request.user_id,
            event_id=tracking_result["event_id"]
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Error tracking recommendation event",
            user_id=request.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track event: {str(e)}"
        )


@router.get("/stats/{user_id}")
async def get_user_recommendation_stats(
    user_id: str,
    http_request: Request
):
    """
    Get recommendation statistics for a user
    
    Args:
        user_id: User ID
        http_request: FastAPI request object
        
    Returns:
        User recommendation statistics
    """
    try:
        logger.info("Getting user recommendation stats", user_id=user_id)
        
        # Get recommendation engine from app state
        recommendation_engine = http_request.app.state.recommendation_engine
        
        # Get user stats
        stats = await recommendation_engine.get_user_stats(user_id)
        
        logger.info("User recommendation stats retrieved", user_id=user_id)
        
        return stats
        
    except Exception as e:
        logger.error(
            "Error getting user recommendation stats",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user stats: {str(e)}"
        )