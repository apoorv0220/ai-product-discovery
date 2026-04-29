"""
AI Product Discovery Suite - Recommendation Engine

@category    Backend
@package     RecommendationService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import asyncio
import uuid
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import json

from shared.config.redis import get_redis_client
from shared.database.base import get_database_session
from .ml_engine import advanced_ml_engine

logger = structlog.get_logger()


class RecommendationEngine:
    """Main recommendation engine for generating product recommendations"""
    
    def __init__(self):
        self.redis_client = None
        self.database = None
        self.algorithms = {
            "collaborative_filtering": self._collaborative_filtering,
            "content_based": self._content_based_filtering,
            "hybrid": self._hybrid_recommendations,
            "trending": self._trending_products,
            "similar": self._similar_products
                }
        
    async def initialize(self):
        """Initialize the recommendation engine with ML capabilities"""
        try:
            # Try to connect to Redis - make it optional
            try:
                self.redis_client = get_redis_client()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning("Redis connection failed, continuing without cache", error=str(e))
                self.redis_client = None
            
            # Initialize ML engine
            try:
                await advanced_ml_engine.initialize()
                logger.info("Advanced ML engine initialized")
            except Exception as e:
                logger.warning("ML engine initialization failed, using basic algorithms", error=str(e))
            
            # Database connection is already handled gracefully in init_database
            logger.info("Recommendation engine initialized with ML capabilities")
            
        except Exception as e:
            logger.error("Failed to initialize recommendation engine", error=str(e))
            # Don't raise - allow service to start without full initialization
            pass
    
    async def get_similar_products(
        self,
        product_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get similar products for a specific product using category and feature similarity
        """
        try:
            from .simple_similar_products import get_similar_products_simple
            return get_similar_products_simple(product_id, limit)
        except Exception as e:
            logger.error("Error getting similar products", error=str(e), product_id=product_id)
            # Fallback to basic category-based similarity
            return await self._basic_similar_products_fallback(product_id, limit)
    
    async def _basic_similar_products_fallback(self, product_id: str, limit: int) -> List[Dict[str, Any]]:
        """Basic fallback for similar products (Disabled: products not in Postgres)"""
        logger.warning("Basic similar products fallback skipped - products not in PostgreSQL")
        return []
    
    async def cleanup(self):
        """Clean up resources"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Recommendation engine cleaned up")
    
    async def get_recommendations(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        exclude_viewed: bool = True,
        exclude_purchased: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on context and user preferences
        
        Args:
            user_id: User ID for personalized recommendations
            context: Recommendation context (home, product_detail, cart, etc.)
            product_ids: Product IDs for context-based recommendations
            category_ids: Category IDs to filter recommendations
            limit: Maximum number of recommendations
            filters: Additional filters
            exclude_viewed: Exclude products already viewed by user
            exclude_purchased: Exclude products already purchased by user
            
        Returns:
            List of recommendation dictionaries
        """
        try:
            logger.info(
                "Generating recommendations",
                user_id=user_id,
                context=context,
                limit=limit
            )
            
            # Choose algorithm based on context and available data
            algorithm = self._select_algorithm(context, user_id, product_ids)
            
            # Generate recommendations using selected algorithm
            recommendations = await self.algorithms[algorithm](
                user_id=user_id,
                context=context,
                product_ids=product_ids,
                category_ids=category_ids,
                limit=limit * 2,  # Get more than needed for filtering
                filters=filters
            )
            
            # Apply filters
            filtered_recommendations = await self._apply_filters(
                recommendations,
                user_id=user_id,
                exclude_viewed=exclude_viewed,
                exclude_purchased=exclude_purchased,
                filters=filters
            )
            
            # Limit results
            final_recommendations = filtered_recommendations[:limit]
            
            # Add metadata
            for rec in final_recommendations:
                rec.update({
                    "algorithm": algorithm,
                    "timestamp": datetime.utcnow().isoformat(),
                    "context": context
                })
            
            logger.info(
                "Recommendations generated",
                count=len(final_recommendations),
                algorithm=algorithm
            )
            
            return final_recommendations
            
        except Exception as e:
            logger.error("Error generating recommendations", error=str(e))
            # Return fallback recommendations
            return await self._fallback_recommendations(limit)
    
    async def train_ml_models(self) -> None:
        """
        Train ML models with latest data
        NOTE: Product data loading from Postgres is disabled.
        """
        try:
            logger.info("Starting ML model training")
            
            # Load data from database
            from shared.models.personalization import UserProductViews
            from shared.database.base import get_database_session
            from sqlalchemy import select
            
            async with get_database_session() as session:
                # Load products - TODO: Load from ElasticSearch
                products_data = []
                
                # Load user interactions from UserProductViews (collaborative filtering data)
                # Note: CollaborativeFiltering model doesn't exist, using UserProductViews instead
                interaction_query = select(UserProductViews)
                interaction_result = await session.execute(interaction_query)
                interactions = interaction_result.scalars().all()
                
                # Convert to ML format
                interactions_data = []
                for interaction in interactions:
                    # Use view_duration as implicit rating (longer views = higher interest)
                    implicit_rating = min(1.0, (interaction.view_duration or 0) / 60.0)  # Normalize to 0-1
                    interactions_data.append({
                        'user_id': str(interaction.user_id or interaction.session_id),
                        'product_id': str(interaction.product_id),
                        'rating': implicit_rating,
                        'timestamp': interaction.created_at.isoformat() if interaction.created_at else datetime.utcnow().isoformat()
                    })
                
                # Train ML models
                await advanced_ml_engine.train_models(interactions_data, products_data)
                
                logger.info("ML model training completed", 
                           products_count=len(products_data),
                           interactions_count=len(interactions_data))
                
        except Exception as e:
            logger.error("Error training ML models", error=str(e))
    
    async def record_user_interaction(self, user_id: str, product_id: str, 
                                    interaction_type: str, rating: float = None,
                                    context: Dict[str, Any] = None) -> None:
        """Record user interaction for real-time learning"""
        try:
            await advanced_ml_engine.record_interaction(
                user_id=user_id,
                product_id=product_id,
                interaction_type=interaction_type,
                rating=rating,
                context=context
            )
            
            logger.info("User interaction recorded", 
                       user_id=user_id, product_id=product_id, 
                       interaction_type=interaction_type)
            
        except Exception as e:
            logger.error("Error recording user interaction", error=str(e))
    
    async def get_similar_products(
        self,
        product_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get products similar to a given product"""
        try:
            logger.info("Getting similar products", product_id=product_id)
            
            # Use content-based similarity
            similar_products = await self._similar_products(
                product_ids=[product_id],
                limit=limit
            )
            
            logger.info("Similar products found", count=len(similar_products))
            return similar_products
            
        except Exception as e:
            logger.error("Error getting similar products", error=str(e))
            return []
    
    async def track_event(
        self,
        user_id: Optional[str],
        event_type: str,
        product_id: str,
        session_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track user interaction events"""
        try:
            event_id = str(uuid.uuid4())
            event_data = {
                "event_id": event_id,
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type,
                "product_id": product_id,
                "recommendation_id": recommendation_id,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store in Redis for real-time processing
            await self.redis_client.lpush(
                "recommendation_events",
                json.dumps(event_data)
            )
            
            # Store in database for analytics
            # TODO: Add database storage
            
            logger.info("Event tracked", event_id=event_id, event_type=event_type)
            return {"event_id": event_id}
            
        except Exception as e:
            logger.error("Error tracking event", error=str(e))
            raise
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get recommendation statistics for a user"""
        try:
            # TODO: Implement user stats retrieval
            return {
                "user_id": user_id,
                "total_recommendations": 0,
                "total_clicks": 0,
                "total_purchases": 0,
                "conversion_rate": 0.0,
                "last_activity": None
            }
        except Exception as e:
            logger.error("Error getting user stats", error=str(e))
            return {}
    
    async def get_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get recommendation performance metrics"""
        try:
            # TODO: Implement performance metrics calculation
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "metrics": {
                    "total_recommendations": 0,
                    "total_clicks": 0,
                    "total_purchases": 0,
                    "click_through_rate": 0.0,
                    "conversion_rate": 0.0,
                    "revenue": 0.0
                }
            }
        except Exception as e:
            logger.error("Error getting performance metrics", error=str(e))
            return {}
    
    async def get_conversion_metrics(
        self,
        algorithm: Optional[str] = None,
        context: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get conversion metrics for recommendations"""
        try:
            # TODO: Implement conversion metrics calculation
            return {
                "algorithm": algorithm,
                "context": context,
                "days": days,
                "metrics": {
                    "impressions": 0,
                    "clicks": 0,
                    "purchases": 0,
                    "ctr": 0.0,
                    "conversion_rate": 0.0
                }
            }
        except Exception as e:
            logger.error("Error getting conversion metrics", error=str(e))
            return {}
    
    async def get_popular_recommendations(
        self,
        time_period: str = "24h",
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get most popular recommended products"""
        try:
            # TODO: Implement popular recommendations retrieval
            return []
        except Exception as e:
            logger.error("Error getting popular recommendations", error=str(e))
            return []
    
    def _select_algorithm(
        self,
        context: str,
        user_id: Optional[str],
        product_ids: Optional[List[str]]
    ) -> str:
        """Select the best algorithm based on context and available data"""
        if context == "product_detail" and product_ids:
            return "similar"
        elif user_id:
            return "hybrid"
        else:
            return "trending"
    
    async def _collaborative_filtering(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Collaborative filtering recommendations"""
        # TODO: Implement collaborative filtering algorithm
        return await self._mock_recommendations(limit, "collaborative_filtering")
    
    async def _content_based_filtering(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Content-based filtering recommendations"""
        # TODO: Implement content-based filtering algorithm
        return await self._mock_recommendations(limit, "content_based")
    
    async def _hybrid_recommendations(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid recommendations combining multiple algorithms (Disabled: products not in Postgres)"""
        logger.warning("Hybrid recommendations skipped - products not in PostgreSQL")
        return await self._basic_recommendations(limit, context)
    
    async def _basic_recommendations(self, limit: int, context: str) -> List[Dict[str, Any]]:
        """Basic fallback recommendations (Disabled: products not in Postgres)"""
        logger.warning("Basic recommendations fallback skipped - products not in PostgreSQL")
        return await self._mock_recommendations(limit, "fallback")
    
    async def _trending_products(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Trending products recommendations"""
        # TODO: Implement trending products algorithm
        return await self._mock_recommendations(limit, "trending")
    
    async def _similar_products(
        self,
        user_id: Optional[str] = None,
        context: str = "home",
        product_ids: Optional[List[str]] = None,
        category_ids: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Similar products recommendations using real database data"""
        try:
            # Import models here to avoid import issues
            from shared.models.recommendation import ProductSimilarity
            from shared.database.base import get_database_session
            from sqlalchemy import select, desc, and_
            
            # Handle direct product_id parameter (for similar products API)
            if hasattr(self, '_current_similar_product_id'):
                reference_product_id = int(self._current_similar_product_id)
            elif product_ids and len(product_ids) > 0:
                reference_product_id = int(product_ids[0])
            else:
                return []
            
            async with get_database_session() as session:
                # First try to get pre-computed similarities
                # Note: Product join removed as products are not in Postgres
                similarity_query = select(ProductSimilarity).where(
                    and_(
                        ProductSimilarity.product_id == reference_product_id,
                        ProductSimilarity.similarity_score > 0.1,
                    )
                ).order_by(desc(ProductSimilarity.similarity_score)).limit(limit)
                
                result = await session.execute(similarity_query)
                similarities = result.scalars().all()
                
                recommendations = []
                for similarity in similarities:
                    recommendations.append({
                        "product_id": str(similarity.similar_product_id),
                        "score": float(similarity.similarity_score),
                        "reason": f"Similar to product {reference_product_id}",
                        "metadata": {
                            "algorithm": "content_similarity",
                            "reference_product": reference_product_id,
                            "similarity_type": "combined",
                            "similarity_score": float(similarity.similarity_score)
                        }
                    })
                
                return recommendations[:limit]
                
        except Exception as e:
            logger.error("Error getting similar products from database", error=str(e))
            return []
    
    async def _basic_similar_products(self, product_id: int, limit: int) -> List[Dict[str, Any]]:
        """Basic fallback for similar products (Disabled: products not in Postgres)"""
        logger.warning("Basic similar products fallback skipped - products not in PostgreSQL")
        return []
    
    async def _apply_filters(
        self,
        recommendations: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        exclude_viewed: bool = True,
        exclude_purchased: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Apply filters to recommendations"""
        # TODO: Implement filtering logic
        return recommendations
    
    async def _fallback_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """Fallback recommendations when algorithms fail"""
        return await self._mock_recommendations(limit, "fallback")
    
    async def _mock_recommendations(self, limit: int, algorithm: str) -> List[Dict[str, Any]]:
        """Generate mock recommendations for testing"""
        recommendations = []
        for i in range(limit):
            recommendations.append({
                "product_id": f"product_{i+1}",
                "score": max(0.1, 1.0 - (i * 0.1)),
                "reason": f"Recommended by {algorithm}",
                "metadata": {
                    "algorithm": algorithm,
                    "position": i + 1
                }
            })
        return recommendations