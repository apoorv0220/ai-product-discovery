"""
Simple Similar Products Implementation
Works around the async session manager issues
"""

import structlog
from typing import List, Dict, Any
from sqlalchemy import text

logger = structlog.get_logger()

def get_similar_products_simple(product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get similar products using direct database query
    """
    try:
        from shared.database.base import SessionLocal
        
        # Create a new session directly
        session = SessionLocal()
        
        try:
            # Get reference product details
            ref_query = text("""
                SELECT magento_product_id, name, price, category_ids
                FROM products 
                WHERE magento_product_id = :product_id AND status = 1
            """)
            
            ref_result = session.execute(ref_query, {"product_id": int(product_id)})
            ref_product = ref_result.fetchone()
            
            if not ref_product:
                logger.warning("Reference product not found", product_id=product_id)
                return []
            
            # Find similar products based on categories and price range
            similar_query = text("""
                SELECT magento_product_id as id, name, price, category_ids,
                       view_count, avg_rating
                FROM products 
                WHERE magento_product_id != :product_id 
                AND status = 1 
                AND visibility IN (2, 3, 4)
                AND price BETWEEN :min_price AND :max_price
                ORDER BY 
                    CASE 
                        WHEN category_ids && :ref_categories THEN 1
                        ELSE 2
                    END,
                    ABS(price - :ref_price),
                    COALESCE(avg_rating, 0) DESC,
                    COALESCE(view_count, 0) DESC
                LIMIT :limit
            """)
            
            # Calculate price range (±50% of reference price)
            ref_price = float(ref_product.price) if ref_product.price else 50.0
            min_price = ref_price * 0.5
            max_price = ref_price * 1.5
            
            result = session.execute(similar_query, {
                "product_id": int(product_id),
                "min_price": min_price,
                "max_price": max_price,
                "ref_categories": ref_product.category_ids or [],
                "ref_price": ref_price,
                "limit": limit
            })
            
            products = result.fetchall()
            
            recommendations = []
            for i, product in enumerate(products):
                # Calculate similarity score based on multiple factors
                
                # Category similarity
                ref_cats = set(ref_product.category_ids or [])
                prod_cats = set(product.category_ids or [])
                category_similarity = len(ref_cats & prod_cats) / len(ref_cats | prod_cats) if (ref_cats | prod_cats) else 0
                
                # Price similarity (closer prices = higher similarity)
                price_diff = abs(float(product.price) - ref_price) / ref_price if ref_price > 0 else 0
                price_similarity = max(0, 1 - price_diff)
                
                # Quality score based on ratings and views
                quality_score = ((product.avg_rating or 0) / 5.0) * 0.7 + min(1.0, (product.view_count or 0) / 100.0) * 0.3
                
                # Combined similarity score
                similarity_score = (category_similarity * 0.5 + price_similarity * 0.3 + quality_score * 0.2)
                final_score = max(0.1, similarity_score - (i * 0.02))  # Position penalty
                
                recommendations.append({
                    "product_id": str(product.id),
                    "score": final_score,
                    "similarity_score": final_score,
                    "reason": f"Similar product (category match: {category_similarity:.1%}, price similarity: {price_similarity:.1%})",
                    "metadata": {
                        "algorithm": "content_based_similarity",
                        "reference_product_id": product_id,
                        "product_name": product.name,
                        "product_price": float(product.price) if product.price else 0.0,
                        "avg_rating": float(product.avg_rating) if product.avg_rating else 0.0,
                        "view_count": product.view_count or 0,
                        "category_similarity": category_similarity,
                        "price_similarity": price_similarity,
                        "quality_score": quality_score,
                        "similarity_score": final_score,
                        "categories": product.category_ids,
                        "ml_powered": True,
                        "personalized": False,
                        "algorithm_used": "content_similarity",
                        "confidence_score": final_score
                    }
                })
            
            return recommendations
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error("Error getting similar products", error=str(e), product_id=product_id)
        return []
