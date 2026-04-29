"""
Personalized Search Engine
Implements user behavior-based search ranking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from collections import defaultdict
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import sessionmaker

# Note: UserSearchHistory, UserProductViews, UserSearchClicks tables have been replaced
# with analytics_events table. Personalization now queries analytics service data.
from shared.models import PersonalizedSearchWeights
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os
from core.database import get_async_session

logger = logging.getLogger(__name__)

class PersonalizedSearchEngine:
    """
    Personalized search engine that boosts products based on user behavior

    Key features:
    - Tracks user product views and search history via analytics_events
    - Boosts products user has viewed recently
    - Considers session-based behavior for anonymous users
    - Applies decay factor for older interactions
    """

    def __init__(self):
        self.view_boost_factor = 2.0  # Boost for viewed products
        self.recent_view_boost = 3.0  # Extra boost for recent views (< 1 day)
        self.search_click_boost = 1.5  # Boost for products clicked from search
        self.decay_days = 7  # Days after which boost starts decaying
        self.max_history_days = 30  # Maximum days to consider for personalization

        # Analytics database connection (same as search DB in development)
        from core.database import get_async_session
        # For now, use same database - analytics_events table is in same DB
        self.get_analytics_session = get_async_session
        
    async def track_product_view(
        self,
        merchant_id: int,
        product_id: str,
        user_id: Optional[str] = None,
        session_id: str = None,
        product_name: str = None,
        product_sku: str = None,
        categories: List[str] = None,  # ["Electronics", "Laptops"]
        category_ids: List[str] = None,  # ["123", "456"]
        came_from_search: bool = False,
        search_query: str = None,
        view_duration: int = 0,
        platform: str = None,  # "magento", "woocommerce", etc.
        device_type: str = None,  # "mobile", "desktop", "tablet"
        user_agent: str = None,  # Browser/device user agent
        referrer: str = None  # Referring page URL
    ) -> bool:
        """
        DEPRECATED: Product view tracking has been moved to analytics service.

        This method now logs the event but doesn't store it locally.
        Use analytics service API: POST /api/v1/tracking/product-view
        """
        logger.info(
            "Product view tracking called (deprecated)",
            product_id=product_id,
            user_id=user_id,
            session_id=session_id,
            note="Use analytics service API instead"
        )
        # Event is now handled by analytics service via Redis pub/sub or direct API calls
        return True
    
    async def track_search_query(
        self,
        merchant_id: int,
        query: str,
        user_id: Optional[str] = None,
        session_id: str = None,
        results: List[Dict] = None
    ) -> bool:
        """
        DEPRECATED: Search query tracking has been moved to analytics service.

        This method now logs the event but doesn't store it locally.
        Search queries are auto-tracked via Redis pub/sub in search service.
        """
        logger.info(
            "Search query tracking called (deprecated)",
            query=query,
            user_id=user_id,
            session_id=session_id,
            note="Search queries are auto-tracked via Redis pub/sub"
        )
        # Event is now handled by event_publisher in search service -> analytics service
        return True
    
    async def track_search_click(
        self,
        merchant_id: int,
        search_query: str,
        clicked_product_id: str,
        clicked_product_name: str = None,
        position_in_results: int = None,
        user_id: Optional[str] = None,
        session_id: str = None
    ) -> bool:
        """
        DEPRECATED: Search click tracking has been moved to analytics service.

        This method now logs the event but doesn't store it locally.
        Use analytics service API: POST /api/v1/tracking/search-click
        """
        logger.info(
            "Search click tracking called (deprecated)",
            search_query=search_query,
            clicked_product_id=clicked_product_id,
            user_id=user_id,
            session_id=session_id,
            note="Use analytics service API instead"
        )
        # Event is now handled by analytics service via direct API calls
        return True
    
    async def get_personalized_search_weights(
        self, 
        user_id: Optional[str] = None, 
        session_id: str = None,
        product_ids: List[str] = None
    ) -> Dict[str, float]:
        """Get personalized weights for products"""
        try:
            async with get_async_session() as session:
                # Build query to get weights
                query = select(PersonalizedSearchWeights.product_id, PersonalizedSearchWeights.weight)
                
                # Filter by user or session
                if user_id:
                    query = query.where(PersonalizedSearchWeights.user_id == user_id)
                elif session_id:
                    query = query.where(PersonalizedSearchWeights.session_id == session_id)
                else:
                    return {}
                
                # Filter by specific products if provided
                if product_ids:
                    query = query.where(PersonalizedSearchWeights.product_id.in_(product_ids))
                
                # Only get recent interactions
                cutoff_date = datetime.utcnow() - timedelta(days=self.max_history_days)
                query = query.where(PersonalizedSearchWeights.updated_at >= cutoff_date)
                
                result = await session.execute(query)
                weights = {}
                
                for product_id, weight in result.fetchall():
                    weights[product_id] = weight
                
                logger.info(f"Retrieved {len(weights)} personalized weights for user/session: {user_id or session_id}")
                return weights
                
        except Exception as e:
            logger.error(f"Error getting personalized weights: {str(e)}")
            return {}
    
    async def apply_personalized_ranking(
        self,
        search_results: List[Dict],
        user_id: Optional[str] = None,
        session_id: str = None,
        query: str = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """Apply personalized ranking to search results with user context awareness"""
        try:
            if not search_results:
                return search_results
            
            # Convert Pydantic models to dicts if needed
            results_as_dicts = []
            for result in search_results:
                if hasattr(result, 'dict'):
                    # Pydantic model - convert to dict
                    result_dict = result.dict()
                    # Map Pydantic model fields to expected dict keys
                    if 'product_id' not in result_dict and hasattr(result, 'product_id'):
                        result_dict['product_id'] = str(result.product_id)
                    if 'id' not in result_dict and 'product_id' in result_dict:
                        result_dict['id'] = result_dict['product_id']
                    if 'title' in result_dict and 'name' not in result_dict:
                        result_dict['name'] = result_dict['title']
                    results_as_dicts.append(result_dict)
                elif isinstance(result, dict):
                    # Already a dict
                    results_as_dicts.append(result.copy())
                else:
                    # Fallback: try to convert to dict
                    results_as_dicts.append(dict(result) if hasattr(result, '__dict__') else result)
            
            # Get product IDs from results
            product_ids = [str(result.get('id', result.get('product_id', ''))) for result in results_as_dicts]
            product_ids = [pid for pid in product_ids if pid]  # Remove empty IDs
            
            if not product_ids:
                return results_as_dicts
            
            # Get personalized weights
            weights = await self.get_personalized_search_weights(user_id, session_id, product_ids)
            
            logger.info(f"🎯 Personalization Debug - Session: {session_id}, Weights found: {len(weights)}, Products: {product_ids[:3]}...")
            if weights:
                logger.info(f"📊 Weights: {weights}")
            
            if not weights:
                # No personalization data, return original results
                logger.info(f"⚠️ No personalization weights found for session: {session_id}")
                return results_as_dicts

            # Process user context for enhanced personalization
            context_adjustments = self._process_user_context(user_context, product_ids)
            logger.info(f"📱 User context processed: {len(context_adjustments)} adjustments")

            # Apply weights to results
            personalized_results = []
            for result in results_as_dicts:
                result_copy = result.copy()
                product_id = str(result.get('id', result.get('product_id', '')))
                
                # Get base score (if available) or use default
                # For autocomplete suggestions, use count or set a default score
                base_score = result.get('score', result.get('relevance_score', result.get('count', 1.0)))
                
                # Apply personalization weight
                personalization_weight = weights.get(product_id, 1.0)

                # Apply context adjustments (cart items, recently viewed, etc.)
                context_multiplier = context_adjustments.get(product_id, 1.0)
                personalization_weight *= context_multiplier

                # Ensure weight doesn't go too low or high
                personalization_weight = max(0.1, min(5.0, personalization_weight))

                # Calculate final score
                final_score = base_score * personalization_weight
                
                result_copy['original_score'] = base_score
                result_copy['personalization_weight'] = personalization_weight
                result_copy['final_score'] = final_score
                result_copy['personalized'] = personalization_weight > 1.0
                
                # Log personalized items
                if personalization_weight > 1.0:
                    product_name = result.get('suggestion', result.get('title', result.get('name', 'Unknown')))
                    logger.info(f"🚀 Boosted: {product_name} (ID: {product_id}) - Weight: {personalization_weight:.1f}, Score: {base_score:.1f} → {final_score:.1f}")
                
                personalized_results.append(result_copy)
            
            # Sort by final score (descending)
            personalized_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
            
            # Track this search if query provided
            if query:
                await self.track_search_query(query, user_id, session_id, personalized_results)
            
            logger.info(f"Applied personalized ranking to {len(results_as_dicts)} results")
            return personalized_results
            
        except Exception as e:
            logger.error(f"Error applying personalized ranking: {str(e)}")
            return search_results  # Return original results on error
    
    async def get_user_search_history(
        self,
        user_id: Optional[str] = None,
        session_id: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get user's recent search history from analytics_events"""
        try:
            async with self.get_analytics_session() as session:
                # Query analytics_events for search_query events
                query = (
                    select(
                        text("properties->>'query' as query"),
                        text("properties->>'results_count' as results_count"),
                        text("timestamp"),
                        text("event_id")
                    )
                    .where(text("event_type = 'search_query'"))
                    .order_by(desc(text("timestamp")))
                    .limit(limit)
                )

                if user_id:
                    query = query.where(text("user_id = :user_id")).params(user_id=user_id)
                elif session_id:
                    query = query.where(text("session_id = :session_id")).params(session_id=session_id)
                else:
                    return []

                result = await session.execute(query)
                history = []

                for row in result:
                    history.append({
                        'query': row.query,
                        'results_count': int(row.results_count) if row.results_count else 0,
                        'timestamp': row.timestamp.isoformat() if hasattr(row.timestamp, 'isoformat') else str(row.timestamp),
                        'clicked_products': []  # TODO: Could be derived from search_click events
                    })

                return history

        except Exception as e:
            logger.error(f"Error getting user search history from analytics: {str(e)}")
            return []
    
    async def get_user_viewed_products(
        self,
        user_id: Optional[str] = None,
        session_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get user's recently viewed products from analytics_events"""
        try:
            async with self.get_analytics_session() as session:
                # Query analytics_events for product_view events
                query = (
                    select(
                        text("product_id"),
                        text("properties->>'product_name' as product_name"),
                        text("properties->>'product_sku' as product_sku"),
                        text("properties->>'categories' as categories"),
                        text("properties->>'category_ids' as category_ids"),
                        text("properties->>'view_duration' as view_duration"),
                        text("properties->>'came_from_search' as came_from_search"),
                        text("properties->>'search_query' as search_query"),
                        text("timestamp")
                    )
                    .where(text("event_type = 'product_view'"))
                    .order_by(desc(text("timestamp")))
                    .limit(limit)
                )

                if user_id:
                    query = query.where(text("user_id = :user_id")).params(user_id=user_id)
                elif session_id:
                    query = query.where(text("session_id = :session_id")).params(session_id=session_id)
                else:
                    return []

                # Only get recent views
                cutoff_date = datetime.utcnow() - timedelta(days=self.max_history_days)
                query = query.where(text("timestamp >= :cutoff")).params(cutoff=cutoff_date)

                result = await session.execute(query)
                viewed_products = []

                for row in result:
                    viewed_products.append({
                        'product_id': row.product_id,
                        'product_name': row.product_name,
                        'product_sku': row.product_sku,
                        'categories': json.loads(row.categories or '[]') if row.categories else [],
                        'category_ids': json.loads(row.category_ids or '[]') if row.category_ids else [],
                        'view_duration': int(row.view_duration) if row.view_duration else 0,
                        'came_from_search': row.came_from_search == 'true' if row.came_from_search else False,
                        'search_query': row.search_query,
                        'timestamp': row.timestamp.isoformat() if hasattr(row.timestamp, 'isoformat') else str(row.timestamp)
                    })

                return viewed_products

        except Exception as e:
            logger.error(f"Error getting user viewed products from analytics: {str(e)}")
            return []
    
    async def _update_personalized_weight(
        self,
        session: AsyncSession,
        merchant_id: int,
        user_id: Optional[str],
        session_id: str,
        product_id: str,
        interaction_type: str = "view",
        boost_factor: float = 1.5
    ):
        """Update personalized weight for a product"""
        try:
            # Check if weight record exists
            query = select(PersonalizedSearchWeights).where(
                PersonalizedSearchWeights.merchant_id == merchant_id
            )

            if user_id:
                query = query.where(and_(
                    PersonalizedSearchWeights.user_id == user_id,
                    PersonalizedSearchWeights.product_id == product_id
                ))
            else:
                query = query.where(and_(
                    PersonalizedSearchWeights.session_id == session_id,
                    PersonalizedSearchWeights.product_id == product_id
                ))
            
            result = await session.execute(query)
            weight_record = result.scalar_one_or_none()
            
            if weight_record:
                # Update existing record
                weight_record.interaction_count += 1
                weight_record.updated_at = datetime.utcnow()
                
                # Apply decay based on time since last interaction
                days_since_last = (datetime.utcnow() - weight_record.updated_at).days
                decay_factor = max(0.5, 1.0 - (days_since_last / self.decay_days))
                
                # Update weight with boost and decay
                new_weight = min(5.0, weight_record.weight * decay_factor + boost_factor * 0.1)
                weight_record.weight = new_weight
                
            else:
                # Create new record
                weight_record = PersonalizedSearchWeights(
                    merchant_id=merchant_id,
                    user_id=user_id,
                    session_id=session_id or f"anon_{datetime.now().timestamp()}",
                    product_id=product_id,
                    weight=1.0 + boost_factor * 0.2,  # Initial boost
                    updated_at=datetime.utcnow(),
                    interaction_count=1
                )
                session.add(weight_record)
            
            logger.debug(f"Updated personalized weight for product {product_id}: {weight_record.weight}")
            
        except Exception as e:
            logger.error(f"Error updating personalized weight: {str(e)}")

    def _process_user_context(self, user_context: Optional[Dict[str, Any]], product_ids: List[str]) -> Dict[str, float]:
        """Process user context to create adjustment multipliers for personalization"""
        adjustments = {}

        if not user_context:
            return adjustments

        try:
            # Cart items - reduce likelihood of showing items already in cart
            cart_items = user_context.get('cart_items', [])
            if cart_items:
                for product_id in product_ids:
                    if str(product_id) in [str(item) for item in cart_items]:
                        adjustments[str(product_id)] = 0.3  # Reduce by 70%
                        logger.debug(f"🛒 Cart item {product_id} reduced to 30% weight")

            # Recently viewed - slight reduction to avoid repetition
            recently_viewed = user_context.get('recently_viewed', [])
            if recently_viewed:
                for product_id in product_ids:
                    if str(product_id) in [str(item) for item in recently_viewed]:
                        adjustments[str(product_id)] = adjustments.get(str(product_id), 1.0) * 0.7  # Reduce by 30%
                        logger.debug(f"👁️ Recently viewed {product_id} reduced to 70% weight")

            # Wishlist items - slight boost
            wishlist = user_context.get('wishlist', [])
            if wishlist:
                for product_id in product_ids:
                    if str(product_id) in [str(item) for item in wishlist]:
                        adjustments[str(product_id)] = adjustments.get(str(product_id), 1.0) * 1.2  # Boost by 20%
                        logger.debug(f"❤️ Wishlist item {product_id} boosted to 120% weight")

            # Purchase history - boost complementary items (simplified logic)
            purchase_history = user_context.get('purchase_history', [])
            if purchase_history:
                # For now, give slight boost to items not in purchase history
                # In future, could implement complementary product logic
                purchased_ids = set(str(item) for item in purchase_history)
                for product_id in product_ids:
                    if str(product_id) not in purchased_ids:
                        adjustments[str(product_id)] = adjustments.get(str(product_id), 1.0) * 1.1  # Slight boost
                        logger.debug(f"🛍️ New item {product_id} boosted to 110% weight")

            # Device type adjustments (optional)
            device_type = user_context.get('device_type')
            if device_type == 'mobile':
                # Mobile users might prefer different ranking
                for product_id in product_ids:
                    adjustments[str(product_id)] = adjustments.get(str(product_id), 1.0) * 1.05  # Slight mobile boost

            logger.info(f"Processed user context: {len(adjustments)} adjustments applied")
            return adjustments

        except Exception as e:
            logger.error(f"Error processing user context: {str(e)}")
            return {}

# Global instance
personalized_search_engine = PersonalizedSearchEngine()
