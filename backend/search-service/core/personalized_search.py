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

import sys
import os
# Add backend directory to path for models import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)
from models.user_interactions import (
    UserSearchHistory, UserProductViews, UserSearchClicks, PersonalizedSearchWeights
)
from core.database import get_async_session

logger = logging.getLogger(__name__)

class PersonalizedSearchEngine:
    """
    Personalized search engine that boosts products based on user behavior
    
    Key features:
    - Tracks user product views and search history
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
        """Track a product view for personalization"""
        try:
            async with get_async_session() as session:
                # Create product view record
                view_record = UserProductViews(
                    merchant_id=merchant_id,
                    user_id=user_id,
                    session_id=session_id or f"anon_{datetime.now().timestamp()}",
                    product_id=product_id,
                    product_name=product_name,
                    product_sku=product_sku,
                    categories=json.dumps(categories or []),
                    category_ids=json.dumps(category_ids or []),
                    view_duration=view_duration,
                    came_from_search=came_from_search,
                    search_query=search_query,
                    platform=platform or None,
                    device_type=device_type or None,
                    user_agent=user_agent or None,
                    referrer=referrer or None,
                    created_at=datetime.utcnow()
                )
                
                session.add(view_record)
                
                # Update or create personalized weight
                await self._update_personalized_weight(
                    session, merchant_id, user_id, session_id, product_id,
                    interaction_type="view", boost_factor=self.view_boost_factor
                )
                
                await session.commit()
                
                logger.info(f"Tracked product view: {product_id} for user/session: {user_id or session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error tracking product view: {str(e)}")
            return False
    
    async def track_search_query(
        self,
        merchant_id: int,
        query: str,
        user_id: Optional[str] = None,
        session_id: str = None,
        results: List[Dict] = None
    ) -> bool:
        """Track a search query"""
        try:
            async with get_async_session() as session:
                # Create search history record
                search_record = UserSearchHistory(
                    merchant_id=merchant_id,
                    user_id=user_id,
                    session_id=session_id or f"anon_{datetime.now().timestamp()}",
                    query=query.lower().strip(),
                    results_count=len(results or []),
                    created_at=datetime.utcnow()
                )
                
                session.add(search_record)
                await session.commit()
                
                logger.info(f"Tracked search query: '{query}' for user/session: {user_id or session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error tracking search query: {str(e)}")
            return False
    
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
        """Track a click on search result"""
        try:
            async with get_async_session() as session:
                # Create search click record
                click_record = UserSearchClicks(
                    merchant_id=merchant_id,
                    user_id=user_id,
                    session_id=session_id or f"anon_{datetime.now().timestamp()}",
                    search_query=search_query.lower().strip(),
                    clicked_product_id=clicked_product_id,
                    clicked_product_name=clicked_product_name,
                    position_in_results=position_in_results,
                    created_at=datetime.utcnow()
                )
                
                session.add(click_record)
                
                # Update personalized weight with search click boost
                await self._update_personalized_weight(
                    session, merchant_id, user_id, session_id, clicked_product_id,
                    interaction_type="search_click", boost_factor=self.search_click_boost
                )
                
                await session.commit()
                
                logger.info(f"Tracked search click: {clicked_product_id} for query: '{search_query}'")
                return True
                
        except Exception as e:
            logger.error(f"Error tracking search click: {str(e)}")
            return False
    
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
            
            # Get product IDs from results
            product_ids = [str(result.get('id', result.get('product_id', ''))) for result in search_results]
            product_ids = [pid for pid in product_ids if pid]  # Remove empty IDs
            
            if not product_ids:
                return search_results
            
            # Get personalized weights
            weights = await self.get_personalized_search_weights(user_id, session_id, product_ids)
            
            logger.info(f"🎯 Personalization Debug - Session: {session_id}, Weights found: {len(weights)}, Products: {product_ids[:3]}...")
            if weights:
                logger.info(f"📊 Weights: {weights}")
            
            if not weights:
                # No personalization data, return original results
                logger.info(f"⚠️ No personalization weights found for session: {session_id}")
                return search_results

            # Process user context for enhanced personalization
            context_adjustments = self._process_user_context(user_context, product_ids)
            logger.info(f"📱 User context processed: {len(context_adjustments)} adjustments")

            # Apply weights to results
            personalized_results = []
            for result in search_results:
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
            
            logger.info(f"Applied personalized ranking to {len(search_results)} results")
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
        """Get user's recent search history"""
        try:
            async with get_async_session() as session:
                query = select(UserSearchHistory).order_by(desc(UserSearchHistory.created_at)).limit(limit)
                
                if user_id:
                    query = query.where(UserSearchHistory.user_id == user_id)
                elif session_id:
                    query = query.where(UserSearchHistory.session_id == session_id)
                else:
                    return []
                
                result = await session.execute(query)
                history = []
                
                for record in result.scalars():
                    history.append({
                        'query': record.query,
                        'results_count': record.results_count,
                        'timestamp': record.created_at.isoformat(),
                        'clicked_products': json.loads(record.clicked_products or '[]')
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting user search history: {str(e)}")
            return []
    
    async def get_user_viewed_products(
        self,
        user_id: Optional[str] = None,
        session_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get user's recently viewed products"""
        try:
            async with get_async_session() as session:
                query = select(UserProductViews).order_by(desc(UserProductViews.created_at)).limit(limit)
                
                if user_id:
                    query = query.where(UserProductViews.user_id == user_id)
                elif session_id:
                    query = query.where(UserProductViews.session_id == session_id)
                else:
                    return []
                
                # Only get recent views
                cutoff_date = datetime.utcnow() - timedelta(days=self.max_history_days)
                query = query.where(UserProductViews.created_at >= cutoff_date)
                
                result = await session.execute(query)
                viewed_products = []
                
                for record in result.scalars():
                    viewed_products.append({
                        'product_id': record.product_id,
                        'product_name': record.product_name,
                        'product_sku': record.product_sku,
                        'categories': json.loads(record.categories or '[]'),
                        'view_duration': record.view_duration,
                        'came_from_search': record.came_from_search,
                        'search_query': record.search_query,
                        'timestamp': record.created_at.isoformat()
                    })
                
                return viewed_products
                
        except Exception as e:
            logger.error(f"Error getting user viewed products: {str(e)}")
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
