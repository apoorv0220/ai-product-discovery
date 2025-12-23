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


def _calibrate_scores_by_attribute_coverage(
    results: List[Dict[str, Any]],
    query_attributes: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Calibrate hybrid scores based on how well products match query attributes.

    Boosts products that have more of the attributes mentioned in the query.
    This is part of Hybrid+ Scoring Tweaks for better semantic relevance.

    Args:
        results: Search results with hybrid_score
        query_attributes: Dict with 'attributes' list and 'query' string

    Returns:
        Results with calibrated scores
    """
    attributes_list = query_attributes.get("attributes", [])
    if not attributes_list:
        return results

    calibrated_results = []

    for result in results:
        score_multiplier = 1.0
        attribute_coverage = 0

        # Get product attributes
        attributes = result.get("metadata", {}).get("attributes", {})

        # Check coverage for each query attribute
        for attr in attributes_list:
            if attr.lower() in ["color", "colour"]:
                if attributes.get("color"):
                    attribute_coverage += 1
                    score_multiplier *= 1.2  # Boost products with color info
            elif attr.lower() in ["size", "sizing"]:
                if attributes.get("size"):
                    attribute_coverage += 1
                    score_multiplier *= 1.15  # Boost products with size info
            elif attr.lower() in ["material", "fabric"]:
                if attributes.get("material"):
                    attribute_coverage += 1
                    score_multiplier *= 1.15  # Boost products with material info
            elif attr.lower() in ["brand", "manufacturer"]:
                if result.get("metadata", {}).get("brand"):
                    attribute_coverage += 1
                    score_multiplier *= 1.25  # Boost products with brand info

        # Apply score calibration
        if score_multiplier > 1.0:
            result["hybrid_score"] *= score_multiplier
            result["attribute_coverage"] = attribute_coverage
            result["attribute_boost"] = score_multiplier

        calibrated_results.append(result)

    # Re-sort by calibrated scores
    calibrated_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

    return calibrated_results


def reciprocal_rank_fusion(
    keyword_results: List[Dict[str, Any]],
    semantic_results: List[Dict[str, Any]],
    keyword_weight: float = 0.7,
    semantic_weight: float = 0.3,
    query_attributes: Optional[Dict[str, Any]] = None
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
        if not result or not isinstance(result, dict):
            continue
        product_id = str(result.get("product_id", ""))
        if product_id and result.get("product_id"):  # Extra validation
            # RRF score = 1 / (k + rank)
            keyword_scores[product_id] = keyword_weight / (RRF_K + rank)
            # Store full result for later (ensure it's a valid dict)
            if isinstance(result, dict) and "product_id" in result:
                try:
                    keyword_results_map[product_id] = dict(result)  # Create a copy to be safe
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to store keyword result for product {product_id}: {e}")

    # Extract product IDs and scores from semantic results
    for rank, result in enumerate(semantic_results, start=1):
        if not result or not isinstance(result, dict):
            continue
        product_id = str(result.get("product_id", ""))
        if product_id and result.get("product_id"):  # Extra validation
            # RRF score = 1 / (k + rank)
            semantic_scores[product_id] = semantic_weight / (RRF_K + rank)
            # Store full result for later (ensure it's a valid dict)
            if isinstance(result, dict) and "product_id" in result:
                try:
                    semantic_results_map[product_id] = dict(result)  # Create a copy to be safe
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to store semantic result for product {product_id}: {e}")
    
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
        result = None

        # Try keyword result first
        if product_id in keyword_results_map:
            keyword_result = keyword_results_map[product_id]
            if (keyword_result is not None and
                isinstance(keyword_result, dict) and
                keyword_result and
                keyword_result.get("product_id")):
                try:
                    result = keyword_result.copy()
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Failed to copy keyword result for product {product_id}: {e}")
                    result = None

        # Fall back to semantic result
        if not result and product_id in semantic_results_map:
            semantic_result = semantic_results_map[product_id]
            if (semantic_result is not None and
                isinstance(semantic_result, dict) and
                semantic_result and
                semantic_result.get("product_id")):
                try:
                    result = semantic_result.copy()
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Failed to copy semantic result for product {product_id}: {e}")
                    result = None

        if not result:
            continue
        
        # Add combined score
        result["hybrid_score"] = combined_scores[product_id]
        result["keyword_score"] = keyword_scores.get(product_id, 0.0)
        result["semantic_score"] = semantic_scores.get(product_id, 0.0)
        
        merged_results.append(result)
    
    # Apply score calibration based on attribute coverage (Hybrid+ Scoring Tweaks)
    if query_attributes:
        merged_results = _calibrate_scores_by_attribute_coverage(
            merged_results, query_attributes
        )

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
    semantic_weight: float = 0.3,
    query_attributes: Optional[Dict[str, Any]] = None
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
        query_attributes: List of attributes mentioned in query for score calibration
        
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
    
    # Extract results with validation
    keyword_results = keyword_results_data.get("results", []) if isinstance(keyword_results_data, dict) else []
    semantic_results = semantic_results_data.get("results", []) if isinstance(semantic_results_data, dict) else []

    # Ensure results are lists and filter out None/invalid items
    keyword_results = [r for r in keyword_results if r is not None and isinstance(r, dict)]
    semantic_results = [r for r in semantic_results if r is not None and isinstance(r, dict)]
    
    # Merge using RRF
    merged_results = reciprocal_rank_fusion(
        keyword_results,
        semantic_results,
        keyword_weight,
        semantic_weight,
        query_attributes
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

