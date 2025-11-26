"""
AI Product Discovery Suite - Hybrid Search

Combines keyword search (Elasticsearch) and semantic search (Qdrant) using Reciprocal Rank Fusion.

@category    Backend
@package     SearchService/Core
@license     MIT License
"""

from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# RRF constant (standard value)
RRF_K = 60


def reciprocal_rank_fusion(
    keyword_results: List[Dict[str, Any]],
    semantic_results: List[Dict[str, Any]],
    keyword_weight: float = 0.7,
    semantic_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Merge keyword and semantic search results using Reciprocal Rank Fusion (RRF)
    
    Args:
        keyword_results: Results from Elasticsearch keyword search
        semantic_results: Results from Qdrant semantic search
        keyword_weight: Weight for keyword results (default: 0.7)
        semantic_weight: Weight for semantic results (default: 0.3)
        
    Returns:
        Merged and re-ranked results
    """
    # Build product ID to score mapping
    keyword_scores = {}
    semantic_scores = {}
    keyword_results_map = {}
    semantic_results_map = {}
    
    # Extract product IDs and scores from keyword results
    for rank, result in enumerate(keyword_results, start=1):
        product_id = str(result.get("product_id", ""))
        if product_id:
            # RRF score = 1 / (k + rank)
            keyword_scores[product_id] = keyword_weight / (RRF_K + rank)
            # Store full result for later
            keyword_results_map[product_id] = result
    
    # Extract product IDs and scores from semantic results
    for rank, result in enumerate(semantic_results, start=1):
        product_id = str(result.get("product_id", ""))
        if product_id:
            # RRF score = 1 / (k + rank)
            semantic_scores[product_id] = semantic_weight / (RRF_K + rank)
            # Store full result for later
            semantic_results_map[product_id] = result
    
    # Combine scores
    combined_scores = {}
    all_product_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())
    
    for product_id in all_product_ids:
        keyword_score = keyword_scores.get(product_id, 0.0)
        semantic_score = semantic_scores.get(product_id, 0.0)
        combined_scores[product_id] = keyword_score + semantic_score
    
    # Sort by combined score (descending)
    sorted_product_ids = sorted(
        combined_scores.keys(),
        key=lambda pid: combined_scores[pid],
        reverse=True
    )
    
    # Build merged results
    merged_results = []
    seen_ids = set()
    
    for product_id in sorted_product_ids:
        if product_id in seen_ids:
            continue
        
        seen_ids.add(product_id)
        
        # Prefer keyword result if available (has more fields), otherwise use semantic
        if product_id in keyword_results_map:
            result = keyword_results_map[product_id].copy()
        elif product_id in semantic_results_map:
            result = semantic_results_map[product_id].copy()
        else:
            continue
        
        # Add combined score
        result["hybrid_score"] = combined_scores[product_id]
        result["keyword_score"] = keyword_scores.get(product_id, 0.0)
        result["semantic_score"] = semantic_scores.get(product_id, 0.0)
        
        merged_results.append(result)
    
    logger.info("Merged search results",
               keyword_count=len(keyword_results),
               semantic_count=len(semantic_results),
               merged_count=len(merged_results))
    
    return merged_results


async def hybrid_search(
    keyword_search_func,
    semantic_search_func,
    query: str,
    merchant_id: int,
    limit: int = 20,
    offset: int = 0,
    filters: Optional[Dict[str, Any]] = None,
    keyword_weight: float = 0.7,
    semantic_weight: float = 0.3
) -> Dict[str, Any]:
    """
    Perform hybrid search combining keyword and semantic results
    
    Args:
        keyword_search_func: Async function to perform keyword search
        semantic_search_func: Async function to perform semantic search
        query: Search query
        merchant_id: Merchant ID
        limit: Number of results
        offset: Offset for pagination
        filters: Optional filters
        keyword_weight: Weight for keyword results
        semantic_weight: Weight for semantic results
        
    Returns:
        Dictionary with merged results and metadata
    """
    import asyncio
    
    # Run both searches in parallel
    keyword_task = keyword_search_func(query, merchant_id, limit * 2, 0, filters)
    semantic_task = semantic_search_func(query, merchant_id, limit * 2, 0, filters)
    
    keyword_results_data, semantic_results_data = await asyncio.gather(
        keyword_task,
        semantic_task,
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(keyword_results_data, Exception):
        logger.warning("Keyword search failed, using semantic only",
                      error=str(keyword_results_data))
        keyword_results_data = {"results": []}
    
    if isinstance(semantic_results_data, Exception):
        logger.warning("Semantic search failed, using keyword only",
                      error=str(semantic_results_data))
        semantic_results_data = {"results": []}
    
    # Extract results
    keyword_results = keyword_results_data.get("results", [])
    semantic_results = semantic_results_data.get("results", [])
    
    # Merge using RRF
    merged_results = reciprocal_rank_fusion(
        keyword_results,
        semantic_results,
        keyword_weight,
        semantic_weight
    )
    
    # Apply pagination
    if offset > 0:
        merged_results = merged_results[offset:]
    
    merged_results = merged_results[:limit]
    
    return {
        "results": merged_results,
        "total": len(merged_results),  # Note: approximate total
        "keyword_count": len(keyword_results),
        "semantic_count": len(semantic_results),
        "merged_count": len(merged_results)
    }

