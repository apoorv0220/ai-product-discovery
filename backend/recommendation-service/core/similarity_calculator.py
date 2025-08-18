"""
Product Similarity Calculator for Content-Based Recommendations
Calculates product similarities based on features, categories, and attributes
"""

import json
import asyncio
from typing import List, Dict, Any, Tuple
import structlog
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from shared.database.base import get_database_session
from shared.models.product_similarity import ProductSimilarity
from sqlalchemy import delete, select

logger = structlog.get_logger()

class SimilarityCalculator:
    """Calculates and stores product similarities"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.scaler = StandardScaler()
    
    async def calculate_similarities(self, products_data: Dict[str, Any]):
        """Calculate similarities between all products"""
        try:
            if len(products_data) < 2:
                logger.warning("Not enough products for similarity calculation")
                return
                
            # Prepare feature matrices
            text_features = self._extract_text_features(products_data)
            numerical_features = self._extract_numerical_features(products_data)
            categorical_features = self._extract_categorical_features(products_data)
            
            # Calculate similarities
            similarities = self._calculate_combined_similarities(
                text_features, numerical_features, categorical_features, products_data
            )
            
            # Store similarities in database
            await self._store_similarities(similarities)
            
            logger.info("Product similarities calculated and stored", 
                       total_pairs=len(similarities))
            
        except Exception as e:
            logger.error("Similarity calculation failed", error=str(e))
            raise
    
    def _extract_text_features(self, products_data: Dict[str, Any]) -> np.ndarray:
        """Extract and vectorize text features"""
        texts = []
        product_ids = list(products_data.keys())
        
        for product_id in product_ids:
            product = products_data[product_id]
            
            # Combine text features
            text_parts = []
            
            # Product name (higher weight)
            name = product.get('name', '')
            text_parts.extend([name] * 3)  # Triple weight for name
            
            # Description
            description = product.get('description', '')
            if description:
                # Clean HTML tags if any
                import re
                description = re.sub(r'<[^>]+>', ' ', description)
                text_parts.append(description)
            
            # SKU as text feature
            sku = product.get('sku', '')
            if sku:
                text_parts.append(sku)
            
            # Attributes as text
            attributes = product.get('attributes', {})
            for key, value in attributes.items():
                if value and isinstance(value, str):
                    text_parts.append(f"{key}_{value}")
            
            combined_text = ' '.join(text_parts).lower()
            texts.append(combined_text)
        
        # Vectorize text features
        if texts and any(text.strip() for text in texts):
            text_vectors = self.vectorizer.fit_transform(texts)
            return text_vectors.toarray()
        else:
            # Return zero matrix if no text features
            return np.zeros((len(product_ids), 1))
    
    def _extract_numerical_features(self, products_data: Dict[str, Any]) -> np.ndarray:
        """Extract and normalize numerical features"""
        features = []
        product_ids = list(products_data.keys())
        
        for product_id in product_ids:
            product = products_data[product_id]
            
            feature_vector = []
            
            # Price (normalized)
            price = float(product.get('price', 0))
            feature_vector.append(price)
            
            # Special price ratio
            special_price = product.get('special_price')
            if special_price and price > 0:
                special_ratio = float(special_price) / price
            else:
                special_ratio = 1.0
            feature_vector.append(special_ratio)
            
            # Weight
            weight = product.get('attributes', {}).get('weight')
            if weight:
                try:
                    feature_vector.append(float(weight))
                except (ValueError, TypeError):
                    feature_vector.append(0.0)
            else:
                feature_vector.append(0.0)
            
            # Stock quantity (log scale)
            stock_qty = product.get('stock', {}).get('qty', 0)
            feature_vector.append(np.log1p(float(stock_qty)))
            
            features.append(feature_vector)
        
        # Normalize numerical features
        features_array = np.array(features)
        if features_array.size > 0:
            return self.scaler.fit_transform(features_array)
        else:
            return np.zeros((len(product_ids), 1))
    
    def _extract_categorical_features(self, products_data: Dict[str, Any]) -> np.ndarray:
        """Extract categorical features using one-hot encoding"""
        product_ids = list(products_data.keys())
        
        # Collect all unique categories and attributes
        all_categories = set()
        all_colors = set()
        all_sizes = set()
        all_manufacturers = set()
        
        for product in products_data.values():
            # Categories
            categories = product.get('categories', [])
            for cat in categories:
                if isinstance(cat, str) and cat.isdigit():
                    all_categories.add(cat)
            
            # Attributes
            attrs = product.get('attributes', {})
            if attrs.get('color'):
                all_colors.add(str(attrs['color']).lower())
            if attrs.get('size'):
                all_sizes.add(str(attrs['size']).lower())
            if attrs.get('manufacturer'):
                all_manufacturers.add(str(attrs['manufacturer']).lower())
        
        # Create feature vectors
        features = []
        
        for product_id in product_ids:
            product = products_data[product_id]
            feature_vector = []
            
            # Category features
            categories = product.get('categories', [])
            category_set = {str(cat) for cat in categories if isinstance(cat, (str, int))}
            
            for cat in sorted(all_categories):
                feature_vector.append(1.0 if cat in category_set else 0.0)
            
            # Color features
            attrs = product.get('attributes', {})
            product_color = str(attrs.get('color', '')).lower()
            for color in sorted(all_colors):
                feature_vector.append(1.0 if color == product_color else 0.0)
            
            # Size features
            product_size = str(attrs.get('size', '')).lower()
            for size in sorted(all_sizes):
                feature_vector.append(1.0 if size == product_size else 0.0)
            
            # Manufacturer features
            product_mfg = str(attrs.get('manufacturer', '')).lower()
            for mfg in sorted(all_manufacturers):
                feature_vector.append(1.0 if mfg == product_mfg else 0.0)
            
            features.append(feature_vector)
        
        return np.array(features) if features else np.zeros((len(product_ids), 1))
    
    def _calculate_combined_similarities(
        self, 
        text_features: np.ndarray, 
        numerical_features: np.ndarray,
        categorical_features: np.ndarray,
        products_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate combined similarities using weighted approach"""
        
        product_ids = list(products_data.keys())
        similarities = []
        
        # Calculate individual similarity matrices
        text_sim = cosine_similarity(text_features) if text_features.shape[1] > 1 else np.zeros((len(product_ids), len(product_ids)))
        num_sim = cosine_similarity(numerical_features) if numerical_features.shape[1] > 1 else np.zeros((len(product_ids), len(product_ids)))
        cat_sim = cosine_similarity(categorical_features) if categorical_features.shape[1] > 1 else np.zeros((len(product_ids), len(product_ids)))
        
        # Combine similarities with weights
        text_weight = 0.5  # Text similarity is most important
        num_weight = 0.3   # Numerical features (price, weight, etc.)
        cat_weight = 0.2   # Categorical features (color, size, etc.)
        
        combined_sim = (text_weight * text_sim + 
                       num_weight * num_sim + 
                       cat_weight * cat_sim)
        
        # Extract top similarities for each product
        for i, product_id in enumerate(product_ids):
            # Get similarity scores for this product
            scores = combined_sim[i]
            
            # Create list of (product_id, similarity_score) pairs
            product_similarities = []
            for j, other_product_id in enumerate(product_ids):
                if i != j:  # Don't include self-similarity
                    similarity_score = float(scores[j])
                    if similarity_score > 0.1:  # Only store meaningful similarities
                        product_similarities.append({
                            'product_id': int(product_id),
                            'similar_product_id': int(other_product_id),
                            'similarity_score': similarity_score,
                            'similarity_type': 'content_based',
                            'algorithm': 'combined_features'
                        })
            
            # Sort by similarity score and take top N
            product_similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            similarities.extend(product_similarities[:20])  # Top 20 similarities per product
        
        return similarities
    
    async def _store_similarities(self, similarities: List[Dict[str, Any]]):
        """Store similarities in database"""
        try:
            async with get_database_session() as session:
                # Clear existing similarities
                await session.execute(delete(ProductSimilarity))
                
                # Insert new similarities
                for sim in similarities:
                    similarity = ProductSimilarity(**sim)
                    session.add(similarity)
                
                await session.commit()
                logger.info("Product similarities stored in database", count=len(similarities))
                
        except Exception as e:
            logger.error("Failed to store similarities", error=str(e))
            raise
