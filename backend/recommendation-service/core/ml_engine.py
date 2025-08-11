"""
Advanced ML-Powered Recommendation Engine
Implements collaborative filtering, content-based recommendations, and real-time learning
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import structlog
import json
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

logger = structlog.get_logger()


@dataclass
class UserProfile:
    """User behavior profile for personalization"""
    user_id: str
    preferences: Dict[str, float] = field(default_factory=dict)
    category_weights: Dict[str, float] = field(default_factory=dict)
    brand_weights: Dict[str, float] = field(default_factory=dict)
    price_sensitivity: float = 0.5
    avg_rating_given: float = 3.0
    interaction_count: int = 0
    last_active: datetime = field(default_factory=datetime.utcnow)
    

@dataclass
class RecommendationResult:
    """Enhanced recommendation result with ML insights"""
    product_id: str
    score: float
    confidence: float
    reason: str
    algorithm: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class CollaborativeFilteringEngine:
    """Matrix factorization based collaborative filtering"""
    
    def __init__(self, n_factors: int = 50, learning_rate: float = 0.01, 
                 regularization: float = 0.02):
        self.n_factors = n_factors
        self.learning_rate = learning_rate
        self.regularization = regularization
        self.user_factors = None
        self.item_factors = None
        self.user_biases = None
        self.item_biases = None
        self.global_bias = 0.0
        self.user_to_idx = {}
        self.item_to_idx = {}
        self.idx_to_user = {}
        self.idx_to_item = {}
        self.is_trained = False
        
    async def train(self, interactions: List[Dict[str, Any]]) -> None:
        """Train collaborative filtering model"""
        try:
            logger.info("Training collaborative filtering model", interactions_count=len(interactions))
            
            if not interactions:
                logger.warning("No interactions available for training")
                return
            
            # Convert interactions to matrix format
            df = pd.DataFrame(interactions)
            if 'user_id' not in df.columns or 'product_id' not in df.columns or 'rating' not in df.columns:
                logger.error("Invalid interaction format")
                return
            
            # Create user and item mappings
            unique_users = df['user_id'].unique()
            unique_items = df['product_id'].unique()
            
            self.user_to_idx = {user: idx for idx, user in enumerate(unique_users)}
            self.item_to_idx = {item: idx for idx, item in enumerate(unique_items)}
            self.idx_to_user = {idx: user for user, idx in self.user_to_idx.items()}
            self.idx_to_item = {idx: item for item, idx in self.item_to_idx.items()}
            
            n_users = len(unique_users)
            n_items = len(unique_items)
            
            # Initialize factors and biases
            self.user_factors = np.random.normal(0, 0.1, (n_users, self.n_factors))
            self.item_factors = np.random.normal(0, 0.1, (n_items, self.n_factors))
            self.user_biases = np.zeros(n_users)
            self.item_biases = np.zeros(n_items)
            self.global_bias = df['rating'].mean()
            
            # Training using SGD
            logger.info("Starting matrix factorization training")
            await self._train_sgd(df, n_epochs=50)
            
            self.is_trained = True
            logger.info("Collaborative filtering training completed")
            
        except Exception as e:
            logger.error("Error training collaborative filtering model", error=str(e))
    
    async def _train_sgd(self, df: pd.DataFrame, n_epochs: int = 50) -> None:
        """Stochastic Gradient Descent training"""
        for epoch in range(n_epochs):
            total_error = 0
            
            # Shuffle data for each epoch
            shuffled_df = df.sample(frac=1).reset_index(drop=True)
            
            for _, row in shuffled_df.iterrows():
                user_idx = self.user_to_idx[row['user_id']]
                item_idx = self.item_to_idx[row['product_id']]
                rating = row['rating']
                
                # Predict rating
                prediction = (
                    self.global_bias + 
                    self.user_biases[user_idx] + 
                    self.item_biases[item_idx] + 
                    np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
                )
                
                # Calculate error
                error = rating - prediction
                total_error += error ** 2
                
                # Update biases
                self.user_biases[user_idx] += self.learning_rate * (error - self.regularization * self.user_biases[user_idx])
                self.item_biases[item_idx] += self.learning_rate * (error - self.regularization * self.item_biases[item_idx])
                
                # Update factors
                user_factors_copy = self.user_factors[user_idx].copy()
                self.user_factors[user_idx] += self.learning_rate * (error * self.item_factors[item_idx] - self.regularization * self.user_factors[user_idx])
                self.item_factors[item_idx] += self.learning_rate * (error * user_factors_copy - self.regularization * self.item_factors[item_idx])
            
            if epoch % 10 == 0:
                rmse = np.sqrt(total_error / len(shuffled_df))
                logger.info(f"Epoch {epoch}, RMSE: {rmse:.4f}")
    
    async def get_recommendations(self, user_id: str, n_recommendations: int = 10) -> List[RecommendationResult]:
        """Get collaborative filtering recommendations for user"""
        if not self.is_trained or user_id not in self.user_to_idx:
            return []
        
        user_idx = self.user_to_idx[user_id]
        recommendations = []
        
        # Calculate predictions for all items
        for item_id, item_idx in self.item_to_idx.items():
            prediction = (
                self.global_bias + 
                self.user_biases[user_idx] + 
                self.item_biases[item_idx] + 
                np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
            )
            
            # Calculate confidence based on factors magnitude
            confidence = min(1.0, np.linalg.norm(self.user_factors[user_idx]) * 
                           np.linalg.norm(self.item_factors[item_idx]) / 10)
            
            recommendations.append(RecommendationResult(
                product_id=item_id,
                score=min(5.0, max(1.0, prediction)),  # Clamp to rating range
                confidence=confidence,
                reason="Users with similar preferences also liked this",
                algorithm="collaborative_filtering",
                metadata={
                    "raw_prediction": prediction,
                    "user_bias": self.user_biases[user_idx],
                    "item_bias": self.item_biases[item_idx]
                }
            ))
        
        # Sort by score and return top N
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:n_recommendations]


class ContentBasedEngine:
    """Content-based recommendation engine using product features"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        self.product_features = None
        self.product_vectors = None
        self.products_df = None
        self.similarity_matrix = None
        self.is_trained = False
    
    async def train(self, products: List[Dict[str, Any]]) -> None:
        """Train content-based model on product features"""
        try:
            logger.info("Training content-based model", products_count=len(products))
            
            if not products:
                logger.warning("No products available for training")
                return
            
            # Convert to DataFrame
            self.products_df = pd.DataFrame(products)
            
            # Create text features from product data
            text_features = []
            for product in products:
                features = []
                
                # Add name and description
                if 'name' in product:
                    features.append(str(product['name']))
                if 'description' in product:
                    features.append(str(product['description']))
                
                # Add categories
                if 'categories' in product and product['categories']:
                    if isinstance(product['categories'], list):
                        features.extend([str(cat) for cat in product['categories']])
                    else:
                        features.append(str(product['categories']))
                
                # Add brand
                if 'brand' in product:
                    features.append(str(product['brand']))
                
                # Add attributes
                if 'attributes' in product and isinstance(product['attributes'], dict):
                    for key, value in product['attributes'].items():
                        features.append(f"{key}_{value}")
                
                text_features.append(' '.join(features))
            
            # Create TF-IDF vectors
            self.product_vectors = self.tfidf_vectorizer.fit_transform(text_features)
            
            # Calculate similarity matrix
            self.similarity_matrix = cosine_similarity(self.product_vectors)
            
            self.is_trained = True
            logger.info("Content-based model training completed")
            
        except Exception as e:
            logger.error("Error training content-based model", error=str(e))
    
    async def get_similar_products(self, product_id: str, n_recommendations: int = 10) -> List[RecommendationResult]:
        """Get content-based similar products"""
        if not self.is_trained or self.products_df is None:
            return []
        
        try:
            # Find product index
            product_idx = None
            for idx, product in self.products_df.iterrows():
                if str(product.get('id')) == str(product_id):
                    product_idx = idx
                    break
            
            if product_idx is None:
                return []
            
            # Get similarity scores
            similarity_scores = self.similarity_matrix[product_idx]
            
            # Get top similar products (excluding self)
            similar_indices = np.argsort(similarity_scores)[::-1][1:n_recommendations+1]
            
            recommendations = []
            for idx in similar_indices:
                if idx < len(self.products_df):
                    similar_product = self.products_df.iloc[idx]
                    score = similarity_scores[idx]
                    
                    recommendations.append(RecommendationResult(
                        product_id=str(similar_product.get('id', idx)),
                        score=score,
                        confidence=min(1.0, score * 2),  # Boost confidence for high similarity
                        reason=f"Similar content and features to viewed product",
                        algorithm="content_based",
                        metadata={
                            "similarity_score": score,
                            "categories": similar_product.get('categories', []),
                            "brand": similar_product.get('brand', '')
                        }
                    ))
            
            return recommendations
            
        except Exception as e:
            logger.error("Error getting content-based recommendations", error=str(e))
            return []


class AdvancedRecommendationEngine:
    """Advanced ML-powered recommendation engine combining multiple algorithms"""
    
    def __init__(self):
        self.collaborative_engine = CollaborativeFilteringEngine()
        self.content_engine = ContentBasedEngine()
        self.user_profiles = {}
        self.interaction_buffer = []
        self.products_cache = {}
        self.real_time_weights = {
            'collaborative': 0.4,
            'content': 0.3,
            'popularity': 0.2,
            'diversity': 0.1
        }
        self.last_training_time = None
        self.training_threshold = 100  # Retrain after 100 new interactions
    
    async def initialize(self) -> None:
        """Initialize the recommendation engine"""
        try:
            logger.info("Initializing advanced recommendation engine")
            
            # Load existing models if available
            await self._load_models()
            
            # Load user profiles
            await self._load_user_profiles()
            
            logger.info("Advanced recommendation engine initialized")
            
        except Exception as e:
            logger.error("Error initializing recommendation engine", error=str(e))
    
    async def train_models(self, interactions: List[Dict[str, Any]], 
                          products: List[Dict[str, Any]]) -> None:
        """Train all recommendation models"""
        try:
            logger.info("Training recommendation models", 
                       interactions_count=len(interactions),
                       products_count=len(products))
            
            # Cache products
            self.products_cache = {str(p.get('id', i)): p for i, p in enumerate(products)}
            
            # Train collaborative filtering
            if interactions:
                await self.collaborative_engine.train(interactions)
            
            # Train content-based model
            if products:
                await self.content_engine.train(products)
            
            # Update user profiles from interactions
            await self._update_user_profiles(interactions)
            
            # Save models
            await self._save_models()
            
            self.last_training_time = datetime.utcnow()
            logger.info("Model training completed")
            
        except Exception as e:
            logger.error("Error training models", error=str(e))
    
    async def get_personalized_recommendations(
        self, 
        user_id: str, 
        context: str = "general",
        exclude_products: List[str] = None,
        n_recommendations: int = 10
    ) -> List[RecommendationResult]:
        """Get personalized recommendations using hybrid approach"""
        try:
            logger.info("Getting personalized recommendations", 
                       user_id=user_id, context=context)
            
            exclude_products = exclude_products or []
            all_recommendations = []
            
            # Get collaborative filtering recommendations
            cf_recs = await self.collaborative_engine.get_recommendations(user_id, n_recommendations * 2)
            for rec in cf_recs:
                rec.score *= self.real_time_weights['collaborative']
                all_recommendations.append(rec)
            
            # Get content-based recommendations (if user has interactions)
            user_profile = self.user_profiles.get(user_id)
            if user_profile and hasattr(user_profile, 'recent_products'):
                for product_id in user_profile.recent_products[:3]:  # Last 3 viewed products
                    content_recs = await self.content_engine.get_similar_products(product_id, n_recommendations)
                    for rec in content_recs:
                        rec.score *= self.real_time_weights['content']
                        all_recommendations.append(rec)
            
            # Add popularity-based recommendations
            popularity_recs = await self._get_popularity_recommendations(n_recommendations)
            for rec in popularity_recs:
                rec.score *= self.real_time_weights['popularity']
                all_recommendations.append(rec)
            
            # Merge and deduplicate recommendations
            merged_recs = self._merge_recommendations(all_recommendations)
            
            # Apply diversity and context filters
            filtered_recs = await self._apply_context_filters(merged_recs, context, user_id)
            
            # Exclude specified products
            filtered_recs = [rec for rec in filtered_recs if rec.product_id not in exclude_products]
            
            # Add diversity boost
            diverse_recs = self._boost_diversity(filtered_recs)
            
            # Return top recommendations
            final_recs = diverse_recs[:n_recommendations]
            
            logger.info("Generated personalized recommendations", 
                       user_id=user_id, recommendations_count=len(final_recs))
            
            return final_recs
            
        except Exception as e:
            logger.error("Error getting personalized recommendations", error=str(e))
            return []
    
    async def record_interaction(self, user_id: str, product_id: str, 
                               interaction_type: str, rating: float = None,
                               context: Dict[str, Any] = None) -> None:
        """Record user interaction for real-time learning"""
        try:
            interaction = {
                'user_id': user_id,
                'product_id': product_id,
                'interaction_type': interaction_type,
                'rating': rating or self._infer_rating(interaction_type),
                'timestamp': datetime.utcnow().isoformat(),
                'context': context or {}
            }
            
            self.interaction_buffer.append(interaction)
            
            # Update user profile in real-time
            await self._update_user_profile_realtime(user_id, interaction)
            
            # Trigger retraining if buffer is full
            if len(self.interaction_buffer) >= self.training_threshold:
                await self._incremental_training()
            
            logger.info("Recorded interaction", user_id=user_id, 
                       product_id=product_id, interaction_type=interaction_type)
            
        except Exception as e:
            logger.error("Error recording interaction", error=str(e))
    
    def _infer_rating(self, interaction_type: str) -> float:
        """Infer rating from interaction type"""
        rating_map = {
            'view': 2.0,
            'like': 4.0,
            'add_to_cart': 3.5,
            'purchase': 4.5,
            'share': 4.0,
            'save': 3.0,
            'review': 4.0
        }
        return rating_map.get(interaction_type, 2.5)
    
    async def _get_popularity_recommendations(self, n_recommendations: int) -> List[RecommendationResult]:
        """Get popularity-based recommendations"""
        recommendations = []
        
        # Sort products by popularity (view count, rating, etc.)
        products = list(self.products_cache.values())
        products.sort(key=lambda p: (
            p.get('view_count', 0) * 0.4 + 
            (p.get('avg_rating', 0) or 0) * 0.3 + 
            (p.get('purchase_count', 0) or 0) * 0.3
        ), reverse=True)
        
        for i, product in enumerate(products[:n_recommendations]):
            popularity_score = 0.9 - (i * 0.05)  # Decreasing score
            
            recommendations.append(RecommendationResult(
                product_id=str(product.get('id', i)),
                score=max(0.1, popularity_score),
                confidence=0.8,
                reason="Popular among all users",
                algorithm="popularity",
                metadata={
                    "view_count": product.get('view_count', 0),
                    "avg_rating": product.get('avg_rating', 0),
                    "purchase_count": product.get('purchase_count', 0)
                }
            ))
        
        return recommendations
    
    def _merge_recommendations(self, recommendations: List[RecommendationResult]) -> List[RecommendationResult]:
        """Merge recommendations from different algorithms"""
        merged = {}
        
        for rec in recommendations:
            if rec.product_id in merged:
                # Combine scores from different algorithms
                existing = merged[rec.product_id]
                existing.score = (existing.score + rec.score) / 2
                existing.confidence = max(existing.confidence, rec.confidence)
                existing.reason += f"; {rec.reason}"
                existing.algorithm += f"+{rec.algorithm}"
                existing.metadata.update(rec.metadata)
            else:
                merged[rec.product_id] = rec
        
        # Sort by score
        result = list(merged.values())
        result.sort(key=lambda x: x.score, reverse=True)
        return result
    
    async def _apply_context_filters(self, recommendations: List[RecommendationResult], 
                                   context: str, user_id: str) -> List[RecommendationResult]:
        """Apply context-specific filters"""
        filtered = []
        user_profile = self.user_profiles.get(user_id)
        
        for rec in recommendations:
            product = self.products_cache.get(rec.product_id)
            if not product:
                continue
            
            # Context-specific boosting
            if context == "category_view":
                # Boost products from same category
                if user_profile and hasattr(user_profile, 'preferred_categories'):
                    product_categories = product.get('categories', [])
                    if any(cat in user_profile.preferred_categories for cat in product_categories):
                        rec.score *= 1.2
            
            elif context == "product_view":
                # Boost similar products
                rec.score *= 1.1
            
            elif context == "cart":
                # Boost complementary products
                rec.score *= 1.15
            
            # Price sensitivity adjustment
            if user_profile and hasattr(user_profile, 'price_sensitivity'):
                product_price = product.get('price', 0)
                if user_profile.price_sensitivity < 0.3 and product_price > 100:
                    rec.score *= 0.8  # Reduce score for expensive items for price-sensitive users
                elif user_profile.price_sensitivity > 0.7 and product_price < 50:
                    rec.score *= 1.1  # Boost cheaper items for price-conscious users
            
            filtered.append(rec)
        
        return filtered
    
    def _boost_diversity(self, recommendations: List[RecommendationResult]) -> List[RecommendationResult]:
        """Boost diversity in recommendations"""
        if not recommendations:
            return recommendations
        
        diverse_recs = []
        seen_categories = set()
        seen_brands = set()
        
        # First pass: high-scoring diverse items
        for rec in recommendations:
            product = self.products_cache.get(rec.product_id)
            if not product:
                continue
            
            categories = product.get('categories', [])
            brand = product.get('brand', '')
            
            # Check diversity
            category_seen = any(cat in seen_categories for cat in categories)
            brand_seen = brand in seen_brands
            
            if not category_seen or not brand_seen or len(diverse_recs) < 3:
                diverse_recs.append(rec)
                seen_categories.update(categories)
                seen_brands.add(brand)
        
        # Second pass: fill remaining slots
        remaining_slots = len(recommendations) - len(diverse_recs)
        for rec in recommendations:
            if rec not in diverse_recs and remaining_slots > 0:
                diverse_recs.append(rec)
                remaining_slots -= 1
        
        return diverse_recs
    
    async def _update_user_profiles(self, interactions: List[Dict[str, Any]]) -> None:
        """Update user profiles from interactions"""
        for interaction in interactions:
            user_id = interaction['user_id']
            product_id = interaction['product_id']
            rating = interaction.get('rating', 2.5)
            
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(user_id=user_id)
            
            profile = self.user_profiles[user_id]
            product = self.products_cache.get(product_id)
            
            if product:
                # Update category preferences
                categories = product.get('categories', [])
                for category in categories:
                    if category not in profile.category_weights:
                        profile.category_weights[category] = 0.5
                    profile.category_weights[category] = (
                        profile.category_weights[category] * 0.8 + 
                        (rating / 5.0) * 0.2
                    )
                
                # Update brand preferences
                brand = product.get('brand', '')
                if brand:
                    if brand not in profile.brand_weights:
                        profile.brand_weights[brand] = 0.5
                    profile.brand_weights[brand] = (
                        profile.brand_weights[brand] * 0.8 + 
                        (rating / 5.0) * 0.2
                    )
                
                # Update price sensitivity
                price = product.get('price', 0)
                if price > 0:
                    price_factor = min(1.0, price / 100.0)  # Normalize price
                    profile.price_sensitivity = (
                        profile.price_sensitivity * 0.9 + 
                        (1.0 - price_factor) * 0.1
                    )
            
            profile.interaction_count += 1
            profile.last_active = datetime.utcnow()
    
    async def _update_user_profile_realtime(self, user_id: str, interaction: Dict[str, Any]) -> None:
        """Update user profile in real-time"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)
        
        profile = self.user_profiles[user_id]
        
        # Add to recent products
        if not hasattr(profile, 'recent_products'):
            profile.__dict__['recent_products'] = []
        
        product_id = interaction['product_id']
        if product_id not in profile.recent_products:
            profile.recent_products.insert(0, product_id)
            profile.recent_products = profile.recent_products[:10]  # Keep last 10
    
    async def _incremental_training(self) -> None:
        """Perform incremental training with new interactions"""
        try:
            logger.info("Starting incremental training", new_interactions=len(self.interaction_buffer))
            
            # For now, retrain periodically
            # In production, implement true incremental learning
            if len(self.interaction_buffer) >= self.training_threshold:
                products = list(self.products_cache.values())
                await self.train_models(self.interaction_buffer, products)
                self.interaction_buffer.clear()
            
        except Exception as e:
            logger.error("Error in incremental training", error=str(e))
    
    async def _save_models(self) -> None:
        """Save trained models to disk"""
        try:
            models_dir = "/tmp/ml_models"
            os.makedirs(models_dir, exist_ok=True)
            
            # Save user profiles
            profiles_file = os.path.join(models_dir, "user_profiles.json")
            profiles_data = {}
            for user_id, profile in self.user_profiles.items():
                profiles_data[user_id] = {
                    'preferences': profile.preferences,
                    'category_weights': profile.category_weights,
                    'brand_weights': profile.brand_weights,
                    'price_sensitivity': profile.price_sensitivity,
                    'interaction_count': profile.interaction_count
                }
            
            with open(profiles_file, 'w') as f:
                json.dump(profiles_data, f)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error("Error saving models", error=str(e))
    
    async def _load_models(self) -> None:
        """Load trained models from disk"""
        try:
            models_dir = "/tmp/ml_models"
            
            # Load user profiles
            profiles_file = os.path.join(models_dir, "user_profiles.json")
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r') as f:
                    profiles_data = json.load(f)
                
                for user_id, data in profiles_data.items():
                    profile = UserProfile(user_id=user_id)
                    profile.preferences = data.get('preferences', {})
                    profile.category_weights = data.get('category_weights', {})
                    profile.brand_weights = data.get('brand_weights', {})
                    profile.price_sensitivity = data.get('price_sensitivity', 0.5)
                    profile.interaction_count = data.get('interaction_count', 0)
                    self.user_profiles[user_id] = profile
                
                logger.info("User profiles loaded", profiles_count=len(self.user_profiles))
            
        except Exception as e:
            logger.error("Error loading models", error=str(e))
    
    async def _load_user_profiles(self) -> None:
        """Load user profiles - called during initialization"""
        # Already handled in _load_models
        pass


# Global instance
advanced_ml_engine = AdvancedRecommendationEngine()
