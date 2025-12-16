"""
Simple Similar Products Implementation using ORM.

Uses the shared Product model and a synchronous Session for compatibility
with existing recommendation engine code.
"""

import structlog
from typing import Any, Dict, List

from sqlalchemy import select, and_, func

from shared.database.base import SessionLocal
from shared.models import Product

logger = structlog.get_logger()


def get_similar_products_simple(product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get similar products using ORM queries against the products table.
    """
    try:
        session = SessionLocal()
        
        try:
            # Get reference product details
            ref_stmt = select(Product).where(
                and_(
                    Product.magento_product_id == int(product_id),
                    Product.status == 1,
                )
            )
            ref_product = session.execute(ref_stmt).scalar_one_or_none()
            
            if not ref_product:
                logger.warning("Reference product not found", product_id=product_id)
                return []
            
            ref_price = float(ref_product.price) if ref_product.price else 50.0
            min_price = ref_price * 0.5
            max_price = ref_price * 1.5
            ref_categories = ref_product.category_ids or []

            # Build similarity query using ORM expressions
            if ref_categories:
                category_overlap = Product.category_ids.overlap(ref_categories)
            else:
                category_overlap = True

            similar_stmt = (
                select(Product)
                .where(
                    and_(
                        Product.magento_product_id != int(product_id),
                        Product.status == 1,
                        Product.visibility.in_([2, 3, 4]),
                        Product.price.between(min_price, max_price),
                        category_overlap,
                    )
                )
                .order_by(
                    # Prefer products sharing categories
                    func.case(
                        (Product.category_ids.overlap(ref_categories), 1),
                        else_=2,
                    ),
                    func.abs(Product.price - ref_price),
                    func.coalesce(Product.avg_rating, 0).desc(),
                    func.coalesce(Product.view_count, 0).desc(),
                )
                .limit(limit)
            )
            
            products = session.execute(similar_stmt).scalars().all()
            
            recommendations: List[Dict[str, Any]] = []
            ref_cats = set(ref_categories)

            for i, product in enumerate(products):
                prod_cats = set(product.category_ids or [])
                union = ref_cats | prod_cats
                category_similarity = len(ref_cats & prod_cats) / len(union) if union else 0.0

                if ref_price > 0 and product.price is not None:
                    price_diff = abs(float(product.price) - ref_price) / ref_price
                    price_similarity = max(0.0, 1.0 - price_diff)
                else:
                    price_similarity = 0.0

                quality_score = (
                    ((float(product.avg_rating) if product.avg_rating else 0.0) / 5.0) * 0.7
                    + min(1.0, (product.view_count or 0) / 100.0) * 0.3
                )

                similarity_score = (
                    category_similarity * 0.5 + price_similarity * 0.3 + quality_score * 0.2
                )
                final_score = max(0.1, similarity_score - (i * 0.02))  # Position penalty
                
                recommendations.append(
                    {
                        "product_id": str(product.magento_product_id),
                    "score": final_score,
                    "similarity_score": final_score,
                        "reason": (
                            f"Similar product (category match: {category_similarity:.1%}, "
                            f"price similarity: {price_similarity:.1%})"
                        ),
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
                            "confidence_score": final_score,
                        },
                    }
                )
            
            return recommendations
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error("Error getting similar products", error=str(e), product_id=product_id)
        return []

