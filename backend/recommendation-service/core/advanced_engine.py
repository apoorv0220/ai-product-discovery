"""
Advanced Recommendation Engine
Professional-grade recommendation algorithms like Luigibox
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd

from shared.database.base import get_database_session
# from shared.models.product import Product # Removed
from shared.models.recommendation import ProductSimilarity
from sqlalchemy import select, and_, desc, func, or_

logger = structlog.get_logger()

class AdvancedRecommendationEngine:
    """Professional-grade recommendation engine with multiple algorithms"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.products_cache = {}
        self.user_interactions = {}
        
    async def get_personalized_recommendations(
        self,
        user_id: str,
        context: str = "home",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations using collaborative filtering + content-based
        """
        try:
            # Strategy 1: User-based collaborative filtering
            collaborative_recs = await self._collaborative_filtering_recommendations(
                user_id, limit // 2, context
            )
            
            # Strategy 2: Content-based recommendations based on user history
            content_recs = await self._content_based_user_recommendations(
                user_id, limit // 2, context
            )
            
            # Strategy 3: Hybrid approach combining both
            hybrid_recs = await self._hybrid_personalized_recommendations(
                user_id, collaborative_recs, content_recs, limit
            )
            
            # Apply filters if provided
            if filters:
                hybrid_recs = self._apply_filters(hybrid_recs, filters)
            
            return hybrid_recs[:limit]
            
        except Exception as e:
            logger.error("Error getting personalized recommendations", error=str(e))
            # Fallback to popular products
            return await self._popular_products_fallback(limit, context)
    
    async def get_similar_products_advanced(
        self,
        product_id: str,
        limit: int = 10,
        algorithm: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Advanced similar products with multiple similarity algorithms
        """
        try:
            if algorithm == "content":
                return await self._content_similarity_recommendations(product_id, limit)
            elif algorithm == "behavioral":
                return await self._behavioral_similarity_recommendations(product_id, limit)
            elif algorithm == "hybrid":
                return await self._hybrid_similarity_recommendations(product_id, limit)
            else:
                return await self._content_similarity_recommendations(product_id, limit)
                
        except Exception as e:
            logger.error("Error getting similar products", error=str(e))
            return await self._category_similarity_fallback(product_id, limit)
    
    async def get_trending_recommendations(
        self,
        context: str = "home",
        time_window: int = 7,  # days
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending products (Disabled: products not in Postgres)
        """
        logger.warning("Trending recommendations skipped - products not in PostgreSQL")
        return await self._popular_products_fallback(limit, context)
    
    async def _collaborative_filtering_recommendations(
        self,
        user_id: str,
        limit: int,
        context: str
    ) -> List[Dict[str, Any]]:
        """
        User-based collaborative filtering recommendations (Disabled: products not in Postgres)
        """
        logger.warning("Collaborative filtering skipped - products not in PostgreSQL")
        return []
    
    async def _content_based_user_recommendations(
        self,
        user_id: str,
        limit: int,
        context: str
    ) -> List[Dict[str, Any]]:
        """
        Content-based recommendations (Disabled: products not in Postgres)
        """
        logger.warning("Content-based user recommendations skipped - products not in PostgreSQL")
        return []
    
    async def _hybrid_personalized_recommendations(
        self,
        user_id: str,
        collaborative_recs: List[Dict[str, Any]],
        content_recs: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Combine collaborative and content-based recommendations
        """
        try:
            # Merge and diversify recommendations
            all_recs = {}
            
            # Add collaborative filtering results with higher weight
            for rec in collaborative_recs:
                product_id = rec["product_id"]
                all_recs[product_id] = rec.copy()
                all_recs[product_id]["score"] *= 1.2  # Boost collaborative score
                all_recs[product_id]["metadata"]["hybrid_component"] = "collaborative"
            
            # Add content-based results
            for rec in content_recs:
                product_id = rec["product_id"]
                if product_id in all_recs:
                    # Combine scores if product appears in both
                    all_recs[product_id]["score"] = (all_recs[product_id]["score"] + rec["score"]) / 2
                    all_recs[product_id]["metadata"]["hybrid_component"] = "combined"
                else:
                    all_recs[product_id] = rec.copy()
                    all_recs[product_id]["metadata"]["hybrid_component"] = "content"
            
            # Sort by score and return top recommendations
            sorted_recs = sorted(all_recs.values(), key=lambda x: x["score"], reverse=True)
            
            # Update algorithm metadata
            for rec in sorted_recs:
                rec["metadata"]["algorithm"] = "hybrid_personalized"
                rec["metadata"]["algorithm_used"] = "collaborative_content_hybrid"
                rec["reason"] = "Personalized recommendation based on your preferences and similar users"
            
            return sorted_recs[:limit]
            
        except Exception as e:
            logger.error("Error in hybrid recommendations", error=str(e))
            return collaborative_recs + content_recs
    
    async def _content_similarity_recommendations(
        self,
        product_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Content-based similar products using pre-computed similarities
        """
        try:
            async with get_database_session() as session:
                # Get pre-computed similarities
                # Note: Product join removed as products are not in Postgres
                query = select(
                    ProductSimilarity.similar_product_id,
                    ProductSimilarity.similarity_score
                ).where(
                    and_(
                        ProductSimilarity.product_id == int(product_id),
                        ProductSimilarity.similarity_score > 0.1
                    )
                ).order_by(desc(ProductSimilarity.similarity_score)).limit(limit)
                
                result = await session.execute(query)
                similarities = result.all()
                
                recommendations = []
                for sim in similarities:
                    recommendations.append({
                        "product_id": str(sim.similar_product_id),
                        "score": float(sim.similarity_score),
                        "reason": f"Similar features and content (match: {sim.similarity_score:.1%})",
                        "metadata": {
                            "algorithm": "content_similarity",
                            "similarity_score": float(sim.similarity_score),
                            "ml_powered": True,
                            "personalized": False,
                            "algorithm_used": "feature_similarity",
                            "confidence_score": float(sim.similarity_score)
                        }
                    })
                
                return recommendations
                
        except Exception as e:
            logger.error("Error in content similarity recommendations", error=str(e))
            return []
    
    async def _popular_products_fallback(
        self,
        limit: int,
        context: str
    ) -> List[Dict[str, Any]]:
        """
        Fallback to popular products (Disabled: products not in Postgres)
        """
        logger.warning("Popular products fallback skipped - products not in PostgreSQL")
        return []
    
    async def _category_similarity_fallback(
        self,
        product_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback to category-based similarity (Disabled: products not in Postgres)
        """
        logger.warning("Category similarity fallback skipped - products not in PostgreSQL")
        return []
    
    def _apply_filters(
        self,
        recommendations: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to recommendations
        """
        # Implementation for price range, categories, etc.
        # This is a simplified version
        return recommendations

# Global instance
advanced_recommendation_engine = AdvancedRecommendationEngine()
