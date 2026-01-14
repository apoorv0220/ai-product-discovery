"""
AI Product Discovery Suite - Search Configuration API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import structlog

from shared.middleware.auth import get_merchant_id
from shared.config.redis import CacheManager

logger = structlog.get_logger()

router = APIRouter()

# Default search weights
DEFAULT_KEYWORD_WEIGHT = 0.7
DEFAULT_SEMANTIC_WEIGHT = 0.3


class SearchWeightsConfig(BaseModel):
    """Search weights configuration"""
    keyword_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for keyword search results")
    semantic_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for semantic search results")
    
    @validator('semantic_weight', always=True)
    def validate_weights(cls, v, values):
        """Ensure weights sum to 1.0"""
        keyword_weight = values.get('keyword_weight', DEFAULT_KEYWORD_WEIGHT)
        total = keyword_weight + v
        if abs(total - 1.0) > 0.01:
            # Normalize to sum to 1.0
            if total > 0:
                return v / total
            else:
                return DEFAULT_SEMANTIC_WEIGHT
        return v


@router.get("/")
async def get_search_config(request: Request) -> Dict[str, Any]:
    """
    Get default search weights configuration
    
    Returns:
        Dictionary with current search weight configuration
    """
    try:
        merchant_id = get_merchant_id(request)
        cache = CacheManager()
        
        # Try to get from cache/database
        cache_key = f"search_config:weights:{merchant_id}"
        cached_config = await cache.aget(cache_key)
        
        if cached_config:
            return {
                "keyword_weight": cached_config.get("keyword_weight", DEFAULT_KEYWORD_WEIGHT),
                "semantic_weight": cached_config.get("semantic_weight", DEFAULT_SEMANTIC_WEIGHT),
                "source": "configured"
            }
        
        # Return defaults
        return {
            "keyword_weight": DEFAULT_KEYWORD_WEIGHT,
            "semantic_weight": DEFAULT_SEMANTIC_WEIGHT,
            "source": "default"
        }
    except Exception as e:
        logger.error("Error getting search config", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get search config: {str(e)}")


@router.put("/")
async def update_search_config(config: SearchWeightsConfig, request: Request) -> Dict[str, Any]:
    """
    Update default search weights configuration (admin only)
    
    Args:
        config: Search weights configuration
        
    Returns:
        Updated configuration
    """
    try:
        merchant_id = get_merchant_id(request)
        cache = CacheManager()
        
        # Normalize weights to sum to 1.0
        total = config.keyword_weight + config.semantic_weight
        if total > 0:
            normalized_keyword = config.keyword_weight / total
            normalized_semantic = config.semantic_weight / total
        else:
            normalized_keyword = DEFAULT_KEYWORD_WEIGHT
            normalized_semantic = DEFAULT_SEMANTIC_WEIGHT
        
        # Store in cache (persistent storage would be in database)
        cache_key = f"search_config:weights:{merchant_id}"
        config_data = {
            "keyword_weight": normalized_keyword,
            "semantic_weight": normalized_semantic
        }
        await cache.aset(cache_key, config_data, 86400 * 365)  # 1 year TTL
        
        logger.info("Search weights updated", 
                   merchant_id=merchant_id,
                   keyword_weight=normalized_keyword,
                   semantic_weight=normalized_semantic)
        
        return {
            "keyword_weight": normalized_keyword,
            "semantic_weight": normalized_semantic,
            "message": "Search weights updated successfully"
        }
    except Exception as e:
        logger.error("Error updating search config", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update search config: {str(e)}")

