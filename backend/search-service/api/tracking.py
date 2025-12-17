"""
User Interaction Tracking API for Personalized Search
Tracks user behavior to improve search ranking
"""

from fastapi import APIRouter, HTTPException, Request, Body
from typing import Optional, List, Dict, Any
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.personalized_search import personalized_search_engine
from shared.middleware.auth import get_merchant_id
from schemas.tracking import (
    ProductViewRequest,
    SearchQueryRequest,
    SearchClickRequest,
    BulkTrackingRequest,
    BulkTrackingResponse,
    TrackingResponse,
    UserHistoryResponse,
    PersonalizationWeightsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/product-view", response_model=TrackingResponse)
async def track_product_view(
    request: ProductViewRequest = Body(...),
    http_request: Request = None
):
    # Extract merchant_id from authenticated request (API key)
    merchant_id = get_merchant_id(http_request)
    """Track a product page view for personalization"""
    try:
        success = await personalized_search_engine.track_product_view(
            merchant_id=merchant_id,
            product_id=request.product_id,
            user_id=request.user_id,
            session_id=request.session_id,
            product_name=request.product_name,
            product_sku=request.product_sku,
            categories=request.categories,
            category_ids=request.category_ids,
            came_from_search=request.came_from_search,
            search_query=request.search_query,
            view_duration=request.view_duration,
            platform=getattr(request, 'platform', None),
            device_type=getattr(request, 'device_type', None),
            user_agent=getattr(request, 'user_agent', None),
            referrer=getattr(request, 'referrer', None)
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
    # Extract merchant_id from authenticated request (API key)
    merchant_id = get_merchant_id(http_request)
    """Track a search query for personalization"""
    try:
        success = await personalized_search_engine.track_search_query(
            merchant_id=merchant_id,
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
    # Extract merchant_id from authenticated request (API key)
    merchant_id = get_merchant_id(http_request)
    """Track a click on search result for personalization"""
    try:
        success = await personalized_search_engine.track_search_click(
            merchant_id=merchant_id,
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

@router.post("/bulk-ingest", response_model=BulkTrackingResponse)
async def bulk_ingest_historical_data(
    request: BulkTrackingRequest = Body(...),
    http_request: Request = None
):
    # Extract merchant_id from authenticated request (API key)
    merchant_id = get_merchant_id(http_request)
    """Bulk ingest historical user interaction data for personalization"""
    processed_counts = {
        "product_views": 0,
        "search_queries": 0,
        "search_clicks": 0
    }
    errors = []

    try:
        # Process product views
        for view_request in request.product_views or []:
            try:
                success = await personalized_search_engine.track_product_view(
                    merchant_id=merchant_id,
                    product_id=view_request.product_id,
                    user_id=view_request.user_id,
                    session_id=view_request.session_id,
                    product_name=view_request.product_name,
                    product_sku=view_request.product_sku,
                    categories=view_request.categories,
                    category_ids=view_request.category_ids,
                    came_from_search=view_request.came_from_search,
                    search_query=view_request.search_query,
                    view_duration=view_request.view_duration,
                    platform=view_request.platform,
                    device_type=view_request.device_type,
                    user_agent=view_request.user_agent,
                    referrer=view_request.referrer
                )
                if success:
                    processed_counts["product_views"] += 1
                else:
                    errors.append(f"Failed to process product view for {view_request.product_id}")
            except Exception as e:
                errors.append(f"Error processing product view: {str(e)}")

        # Process search queries
        for query_request in request.search_queries or []:
            try:
                success = await personalized_search_engine.track_search_query(
                    merchant_id=merchant_id,
                    query=query_request.query,
                    user_id=query_request.user_id,
                    session_id=query_request.session_id,
                    results=query_request.results or []
                )
                if success:
                    processed_counts["search_queries"] += 1
                else:
                    errors.append(f"Failed to process search query: {query_request.query}")
            except Exception as e:
                errors.append(f"Error processing search query: {str(e)}")

        # Process search clicks
        for click_request in request.search_clicks or []:
            try:
                success = await personalized_search_engine.track_search_click(
                    merchant_id=merchant_id,
                    search_query=click_request.search_query,
                    clicked_product_id=click_request.clicked_product_id,
                    clicked_product_name=click_request.clicked_product_name,
                    position_in_results=click_request.position_in_results,
                    user_id=click_request.user_id,
                    session_id=click_request.session_id
                )
                if success:
                    processed_counts["search_clicks"] += 1
                else:
                    errors.append(f"Failed to process search click for {click_request.clicked_product_id}")
            except Exception as e:
                errors.append(f"Error processing search click: {str(e)}")

        total_processed = sum(processed_counts.values())
        success_message = f"Successfully processed {total_processed} historical interactions"

        logger.info(f"Bulk ingestion completed: {processed_counts}")
        if errors:
            logger.warning(f"Bulk ingestion errors: {len(errors)}")

        return BulkTrackingResponse(
            success=len(errors) == 0,  # Success if no errors
            message=success_message,
            processed_counts=processed_counts,
            errors=errors[:10],  # Limit error messages
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error in bulk ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk ingestion failed: {str(e)}")

@router.get("/health")
async def tracking_health():
    """Health check for tracking service"""
    return {
        "status": "healthy",
        "service": "personalized_search_tracking",
        "timestamp": datetime.utcnow().isoformat()
    }
