"""
AI Product Discovery Suite - Embedding Service

Generates embeddings for products using sentence transformers.

@category    Backend
@package     SearchService/Core
@license     MIT License
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Union
from sentence_transformers import SentenceTransformer
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
import numpy as np
import structlog

from shared.config.qdrant import (
    EMBEDDING_MODELS,
    DEFAULT_EMBEDDING_MODEL,
    BATCH_CONFIG
)

logger = structlog.get_logger()


class EmbeddingService:
    """
    Service for generating product embeddings using sentence transformers.
    
    Supports:
    - Multiple embedding models
    - Batch processing
    - Caching for performance
    - Fallback to OpenAI embeddings
    """
    
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        """
        Initialize embedding service
        
        Args:
            model_name: Name of the embedding model to use
        """
        self.model_name = model_name
        self.model_config = EMBEDDING_MODELS.get(
            model_name,
            EMBEDDING_MODELS[DEFAULT_EMBEDDING_MODEL]
        )
        self.provider = self.model_config.get("provider", "sentence-transformers")
        self.model: Optional[SentenceTransformer] = None
        self.openai_service: Optional[OpenAIEmbeddingService] = None
        self.initialized = False
        
        # Cache directory
        self.cache_dir = os.getenv(
            'MODEL_CACHE_DIR',
            '/tmp/models'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def initialize(self):
        """Load embedding model"""
        try:
            if self.provider == "openai":
                logger.info("Initializing OpenAI embedding service",
                           model=self.model_name)
                self.openai_service = OpenAIEmbeddingService(
                    model_name=self.model_config["model_name"],
                    vector_size=self.model_config["vector_size"]
                )

                if not self.openai_service.is_available:
                    raise RuntimeError(
                        "OPENAI_API_KEY not configured; OpenAI embeddings unavailable"
                    )

                self.initialized = True
                logger.info("OpenAI embedding service initialized",
                           model=self.model_name,
                           vector_size=self.model_config["vector_size"])
            else:
                logger.info("Loading embedding model",
                           model=self.model_name,
                           cache_dir=self.cache_dir)
                
                # Load model in thread pool to avoid blocking
                self.model = await asyncio.to_thread(
                    SentenceTransformer,
                    self.model_config["model_name"],
                    cache_folder=self.cache_dir
                )
                
                # Set max sequence length
                if "max_seq_length" in self.model_config:
                    self.model.max_seq_length = self.model_config["max_seq_length"]
                
                logger.info("Embedding model loaded",
                           model=self.model_name,
                           vector_size=self.model_config["vector_size"],
                           max_seq_length=self.model_config.get("max_seq_length", "default"))
                
                self.initialized = True
            
        except Exception as e:
            logger.error("Failed to load embedding model",
                        model=self.model_name,
                        error=str(e))
            raise
    
    def prepare_text(self, product: Dict[str, Any]) -> str:
        """
        Prepare product text for embedding
        
        Combines name, description, and category into single text
        
        Args:
            product: Product dictionary
            
        Returns:
            Combined text string
        """
        parts = []
        
        # Product name (most important)
        if product.get("name"):
            parts.append(product["name"])
        
        # Category name
        if product.get("category_name"):
            parts.append(f"Category: {product['category_name']}")
        elif product.get("category_names"):
            category_names = product.get("category_names")
            if isinstance(category_names, list):
                parts.append("Categories: " + ", ".join(category_names))
            else:
                parts.append(f"Category: {category_names}")
        
        # Short description or description
        if product.get("short_description"):
            parts.append(product["short_description"])
        elif product.get("description"):
            # Limit description length
            desc = product["description"]
            if len(desc) > 500:
                desc = desc[:500] + "..."
            parts.append(desc)
        
        # SKU (for exact matching)
        if product.get("sku"):
            parts.append(f"SKU: {product['sku']}")
        
        return " | ".join(parts)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            if self.provider == "openai":
                if not self.openai_service:
                    raise RuntimeError("OpenAI embedding service not available")
                embedding = await self.openai_service.generate_embedding(text)
                if embedding is None:
                    raise RuntimeError("OpenAI embedding generation returned None")
                return embedding
            else:
                if not self.model:
                    raise RuntimeError("Embedding model not loaded")
                embedding = await asyncio.to_thread(
                    self.model.encode,
                    text,
                    convert_to_numpy=True
                )
                return embedding.tolist()
            
        except Exception as e:
            logger.error("Failed to generate embedding",
                        error=str(e),
                        text_length=len(text))
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to embed
            show_progress: Show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not self.initialized:
            raise RuntimeError("Embedding service not initialized")
        
        try:
            logger.info("Generating embeddings batch",
                       count=len(texts),
                       model=self.model_name)
            
            if self.provider == "openai":
                if not self.openai_service:
                    raise RuntimeError("OpenAI embedding service not available")
                embeddings = await self.openai_service.generate_embeddings_batch(texts)
                if any(emb is None for emb in embeddings):
                    raise RuntimeError("OpenAI batch embedding returned None for one or more entries")
                return embeddings
            else:
                if not self.model:
                    raise RuntimeError("Embedding model not loaded")
                embeddings = await asyncio.to_thread(
                    self.model.encode,
                    texts,
                    batch_size=32,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True
                )
                return embeddings.tolist()
            
        except Exception as e:
            logger.error("Failed to generate embeddings batch",
                        error=str(e),
                        count=len(texts))
            raise
    
    async def generate_product_embedding(
        self,
        product: Dict[str, Any]
    ) -> List[float]:
        """
        Generate embedding for a product
        
        Args:
            product: Product dictionary
            
        Returns:
            Embedding vector
        """
        text = self.prepare_text(product)
        return await self.generate_embedding(text)
    
    async def generate_product_embeddings_batch(
        self,
        products: List[Dict[str, Any]],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple products in batch
        
        Args:
            products: List of product dictionaries
            show_progress: Show progress bar
            
        Returns:
            List of embedding vectors
        """
        # Prepare texts
        texts = [self.prepare_text(product) for product in products]
        
        # Generate embeddings
        return await self.generate_embeddings_batch(texts, show_progress)
    
    async def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0-1)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range
        return float(max(0.0, min(1.0, (similarity + 1) / 2)))
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model
        
        Returns:
            Model information dictionary
        """
        return {
            "model_name": self.model_name,
            "vector_size": self.model_config["vector_size"],
            "max_seq_length": self.model_config.get("max_seq_length"),
            "initialized": self.initialized
        }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.provider == "openai":
            self.openai_service = None
            logger.info("OpenAI embedding service cleaned up", model=self.model_name)
        elif self.model:
            self.model = None
            logger.info("Embedding model unloaded", model=self.model_name)


class OpenAIEmbeddingService:
    """Embedding service backed by OpenAI's embedding API."""

    def __init__(self, model_name: str = "text-embedding-3-small", vector_size: int = 1536):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = model_name
        self.vector_size = vector_size
        self.client: Optional[OpenAI] = None
        self.is_available = bool(self.api_key) and OpenAI is not None

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. OpenAI embeddings unavailable.")
        elif OpenAI is None:
            logger.warning("openai package >=1.0.0 is required for OpenAI embeddings.")
        else:
            self.client = OpenAI(api_key=self.api_key)
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding using OpenAI API
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not self.is_available or not self.client:
            return None
        
        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            return list(embedding)
            
        except Exception as e:
            logger.error("OpenAI embedding failed", error=str(e))
            return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts using OpenAI
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.is_available or not self.client:
            return [None] * len(texts)
        
        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                input=texts
            )
            
            # Extract embeddings in order
            embeddings = [list(item.embedding) for item in response.data]
            return embeddings
            
        except Exception as e:
            logger.error("OpenAI batch embedding failed", error=str(e))
            return [None] * len(texts)

