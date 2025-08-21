"""
User Interaction Tracking API for Personalized Search
Tracks user behavior to improve search ranking
"""

from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.personalized_search import personalized_search_engine

logger = logging.getLogger(__name__)
router = APIRouter()

class ProductViewRequest(BaseModel):
    """Request model for tracking product views"""
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    product_id: str = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    product_sku: Optional[str] = Field(None, description="Product SKU")
    categories: Optional[List[str]] = Field(None, description="Product categories")
    view_duration: Optional[int] = Field(0, description="Time spent viewing in seconds")
    came_from_search: Optional[bool] = Field(False, description="Did user come from search?")
    search_query: Optional[str] = Field(None, description="Search query if came from search")

class SearchQueryRequest(BaseModel):
    """Request model for tracking search queries"""
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    query: str = Field(..., description="Search query")
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Search results")

class SearchClickRequest(BaseModel):
    """Request model for tracking search result clicks"""
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    search_query: str = Field(..., description="Original search query")
    clicked_product_id: str = Field(..., description="ID of clicked product")
    clicked_product_name: Optional[str] = Field(None, description="Name of clicked product")
    position_in_results: Optional[int] = Field(None, description="Position in search results")

class TrackingResponse(BaseModel):
    """Response model for tracking endpoints"""
    success: bool
    message: str
    timestamp: str

@router.post("/product-view", response_model=TrackingResponse)
async def track_product_view(
    request: ProductViewRequest = Body(...),
    http_request: Request = None
):
    """Track a product page view for personalization"""
    try:
        success = await personalized_search_engine.track_product_view(
            product_id=request.product_id,
            user_id=request.user_id,
            session_id=request.session_id,
            product_name=request.product_name,
            product_sku=request.product_sku,
            categories=request.categories,
            came_from_search=request.came_from_search,
            search_query=request.search_query,
            view_duration=request.view_duration
        )
        
        if success:
            logger.info(f"Tracked product view: {request.product_id} for user/session: {request.user_id or request.session_id}")
            return TrackingResponse(
                success=True,
                message="Product view tracked successfully",
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to track product view")
            
    except Exception as e:
        logger.error(f"Error tracking product view: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to track product view: {str(e)}")

@router.post("/search-query", response_model=TrackingResponse)
async def track_search_query(
    request: SearchQueryRequest = Body(...),
    http_request: Request = None
):
    """Track a search query for personalization"""
    try:
        success = await personalized_search_engine.track_search_query(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id,
            results=request.results or []
        )
        
        if success:
            logger.info(f"Tracked search query: '{request.query}' for user/session: {request.user_id or request.session_id}")
            return TrackingResponse(
                success=True,
                message="Search query tracked successfully",
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to track search query")
            
    except Exception as e:
        logger.error(f"Error tracking search query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to track search query: {str(e)}")

@router.post("/search-click", response_model=TrackingResponse)
async def track_search_click(
    request: SearchClickRequest = Body(...),
    http_request: Request = None
):
    """Track a click on search result for personalization"""
    try:
        success = await personalized_search_engine.track_search_click(
            search_query=request.search_query,
            clicked_product_id=request.clicked_product_id,
            clicked_product_name=request.clicked_product_name,
            position_in_results=request.position_in_results,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        if success:
            logger.info(f"Tracked search click: {request.clicked_product_id} for query: '{request.search_query}'")
            return TrackingResponse(
                success=True,
                message="Search click tracked successfully",
                timestamp=datetime.utcnow().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to track search click")
            
    except Exception as e:
        logger.error(f"Error tracking search click: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to track search click: {str(e)}")

@router.get("/user-history/{user_id}")
async def get_user_search_history(
    user_id: str,
    limit: int = 50,
    http_request: Request = None
):
    """Get user's search history"""
    try:
        history = await personalized_search_engine.get_user_search_history(
            user_id=user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "history": history,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting user search history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user history: {str(e)}")

@router.get("/session-history/{session_id}")
async def get_session_search_history(
    session_id: str,
    limit: int = 50,
    http_request: Request = None
):
    """Get session's search history (for anonymous users)"""
    try:
        history = await personalized_search_engine.get_user_search_history(
            session_id=session_id,
            limit=limit
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting session search history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")

@router.get("/user-views/{user_id}")
async def get_user_viewed_products(
    user_id: str,
    limit: int = 100,
    http_request: Request = None
):
    """Get user's recently viewed products"""
    try:
        viewed_products = await personalized_search_engine.get_user_viewed_products(
            user_id=user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "viewed_products": viewed_products,
            "total": len(viewed_products)
        }
        
    except Exception as e:
        logger.error(f"Error getting user viewed products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user viewed products: {str(e)}")

@router.get("/session-views/{session_id}")
async def get_session_viewed_products(
    session_id: str,
    limit: int = 100,
    http_request: Request = None
):
    """Get session's recently viewed products (for anonymous users)"""
    try:
        viewed_products = await personalized_search_engine.get_user_viewed_products(
            session_id=session_id,
            limit=limit
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "viewed_products": viewed_products,
            "total": len(viewed_products)
        }
        
    except Exception as e:
        logger.error(f"Error getting session viewed products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session viewed products: {str(e)}")

@router.get("/personalization-weights")
async def get_personalization_weights(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    product_ids: Optional[str] = None,  # Comma-separated list
    http_request: Request = None
):
    """Get personalized search weights for debugging"""
    try:
        if not user_id and not session_id:
            raise HTTPException(status_code=400, detail="Either user_id or session_id is required")
        
        # Parse product IDs if provided
        product_id_list = None
        if product_ids:
            product_id_list = [pid.strip() for pid in product_ids.split(',') if pid.strip()]
        
        weights = await personalized_search_engine.get_personalized_search_weights(
            user_id=user_id,
            session_id=session_id,
            product_ids=product_id_list
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "weights": weights,
            "total": len(weights)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting personalization weights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get personalization weights: {str(e)}")

@router.get("/health")
async def tracking_health():
    """Health check for tracking service"""
    return {
        "status": "healthy",
        "service": "personalized_search_tracking",
        "timestamp": datetime.utcnow().isoformat()
    }
