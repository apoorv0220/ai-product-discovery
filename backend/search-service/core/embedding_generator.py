"""
AI Product Discovery Suite - Embedding Generator

Coordinates embedding generation for products and storage in Qdrant.

@category    Backend
@package     SearchService/Core
@license     MIT License
"""

from typing import List, Dict, Any, Optional
import structlog
import zlib

from .embedding_service import EmbeddingService
from .qdrant_client import QdrantManager
from shared.config.qdrant import DEFAULT_EMBEDDING_MODEL

logger = structlog.get_logger()


class EmbeddingGenerator:
    """
    Coordinates embedding generation and storage for products.
    
    Handles:
    - Batch embedding generation
    - Storing embeddings in Qdrant
    - Updating product embeddings
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_manager: QdrantManager
    ):
        """
        Initialize embedding generator
        
        Args:
            embedding_service: Embedding service instance
            qdrant_manager: Qdrant manager instance
        """
        self.embedding_service = embedding_service
        self.qdrant_manager = qdrant_manager
        self.batch_size = 100  # Process 100 products at a time
    
    def _prepare_embedding_text(self, product: Dict[str, Any]) -> str:
        """
        Prepare product text for embedding generation

        Format: [PRODUCT_TYPE] [CATEGORY] [NAME] [DESCRIPTION] [ATTRIBUTES]

        This prioritizes product type and category over individual word matches
        to fix semantic search quality issues (e.g., "warm tops" returning pants)

        Args:
            product: Product dictionary

        Returns:
            Combined text for embedding
        """
        parts = []

        # 1. EXTRACT PRODUCT TYPE FROM NAME (most important for semantic matching)
        product_type = self._extract_product_type(product.get("name", ""))
        if product_type:
            parts.append(product_type.upper())  # Make it prominent

        # 2. CATEGORIES (repeated for stronger signal)
        categories = product.get("categories", [])
        category_names = []
        if categories:
            # Extract category names if they're objects
            if isinstance(categories, list) and len(categories) > 0:
                if isinstance(categories[0], dict):
                    category_names = [cat.get("name", cat.get("title", "")) for cat in categories if isinstance(cat, dict) and (cat.get("name") or cat.get("title"))]
                else:
                    category_names = [str(cat) for cat in categories if cat]
            else:
                category_names = [str(categories)] if categories else []

        if category_names:
            # Repeat category for stronger signal
            category_text = f"Category: {', '.join(category_names)}"
            parts.append(category_text)
            parts.append(category_text)  # Repeat for emphasis

        # 3. Product name
        if product.get("name"):
            parts.append(product["name"])

        # 4. Description (truncated)
        if product.get("description"):
            desc = product["description"]
            # Limit description length
            if len(desc) > 500:
                desc = desc[:500] + "..."
            parts.append(desc)
        elif product.get("short_description"):
            parts.append(product["short_description"])

        # 5. Brand
        if product.get("brand"):
            parts.append(f"Brand: {product['brand']}")

        # 6. Key attributes (color, size, material, pattern, climate, etc.)
        attributes = product.get("attributes", {})
        if isinstance(attributes, dict):
            key_attrs = []
            for key in ["color", "size", "material", "pattern", "climate", "style", "type"]:
                if key in attributes and attributes[key]:
                    key_attrs.append(f"{key}: {attributes[key]}")
            if key_attrs:
                parts.append("Attributes: " + ", ".join(key_attrs))

        return " | ".join(parts)

    def _extract_product_type(self, product_name: str) -> str:
        """
        Extract product type from product name for better semantic matching

        Args:
            product_name: Product name string

        Returns:
            Product type (top, pant, hoodie, etc.) or empty string
        """
        if not product_name:
            return ""

        name_lower = product_name.lower()

        # Product type keywords in order of specificity
        type_keywords = [
            # Tops
            "top", "tee", "t-shirt", "shirt", "blouse", "tank", "camisole", "crop top",
            # Bottoms
            "pant", "pants", "trouser", "leggings", "capri", "shorts", "skirt",
            # Outerwear
            "hoodie", "sweater", "jacket", "coat", "vest", "cardigan",
            # Footwear
            "shoe", "sneaker", "boot", "sandal",
            # Accessories
            "bag", "hat", "cap", "glove", "scarf", "belt"
        ]

        for keyword in type_keywords:
            if keyword in name_lower:
                return keyword

        return ""
    
    async def generate_and_store_embeddings(
        self,
        merchant_id: int,
        products: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for products and store them in Qdrant
        
        Args:
            merchant_id: Merchant ID
            products: List of product dictionaries
            batch_size: Optional batch size (defaults to self.batch_size)
            
        Returns:
            Dictionary with success count, failure count, and errors
        """
        if not products:
            return {"success_count": 0, "failure_count": 0, "errors": []}
        
        batch_size = batch_size or self.batch_size
        success_count = 0
        failure_count = 0
        errors = []
        
        # Ensure collection exists
        await self.qdrant_manager.ensure_collection(merchant_id)
        
        # Process products in batches
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            try:
                # Prepare texts for embedding
                texts = [self._prepare_embedding_text(product) for product in batch]
                
                # Generate embeddings
                embeddings = await self.embedding_service.generate_embeddings_batch(
                    texts,
                    show_progress=False
                )
                
                # Prepare points for Qdrant
                points = []
                for product, embedding in zip(batch, embeddings):
                    product_id = str(product.get("id") or product.get("product_id") or product.get("sku"))
                    # Generate a unique integer ID for Qdrant (must be unsigned int or UUID)
                    # Use CRC32 hash to convert merchant_id + product_id to a consistent integer
                    point_id_str = f"{merchant_id}_{product_id}"
                    # CRC32 returns a signed 32-bit int, convert to unsigned by masking
                    point_id = zlib.crc32(point_id_str.encode('utf-8')) & 0xffffffff
                    
                    # Prepare payload
                    # Handle categories - can be list of strings or list of dicts
                    categories = product.get("categories", [])
                    category_id = product.get("primary_category_id")
                    category_name = None
                    
                    if categories and isinstance(categories, list) and len(categories) > 0:
                        first_cat = categories[0]
                        if isinstance(first_cat, dict):
                            category_id = category_id or first_cat.get("id")
                            category_name = first_cat.get("name")
                        else:
                            # Category is a string/ID
                            category_id = category_id or str(first_cat)
                    
                    payload = {
                        "product_id": product_id,
                        "merchant_id": merchant_id,
                        "sku": product.get("sku", ""),
                        "name": product.get("name", ""),
                        "description": product.get("description", ""),
                        "short_description": product.get("short_description", ""),
                        "category_id": category_id,
                        "category_name": category_name,
                        "price": product.get("price", 0.0),
                        "special_price": product.get("special_price"),
                        "is_in_stock": bool(product.get("stock", {}).get("is_in_stock", True)) if isinstance(product.get("stock"), dict) else bool(product.get("in_stock", True)),
                        "image_url": product.get("image_url", ""),
                        "url_key": product.get("url", "").split("/")[-1] if product.get("url") else "",
                        "attributes": product.get("attributes", {}),
                        "status": product.get("status", 1),
                    }
                    
                    points.append((point_id, embedding, payload))
                
                # Store in Qdrant
                success = await self.qdrant_manager.upsert_vectors(merchant_id, points)
                
                if success:
                    success_count += len(batch)
                    logger.info("Embeddings generated and stored",
                              merchant_id=merchant_id,
                              batch_size=len(batch),
                              batch_start=i,
                              batch_end=i + len(batch))
                else:
                    failure_count += len(batch)
                    errors.append({
                        "batch_start": i,
                        "batch_end": i + len(batch),
                        "error": "Failed to store embeddings in Qdrant"
                    })
                    
            except Exception as e:
                failure_count += len(batch)
                errors.append({
                    "batch_start": i,
                    "batch_end": i + len(batch),
                    "error": str(e)
                })
                logger.error("Failed to generate embeddings for batch",
                           merchant_id=merchant_id,
                           batch_start=i,
                           error=str(e))
        
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        }
    
    async def generate_and_store_embedding(
        self,
        merchant_id: int,
        product: Dict[str, Any]
    ) -> bool:
        """
        Generate embedding for a single product and store in Qdrant
        
        Args:
            merchant_id: Merchant ID
            product: Product dictionary
            
        Returns:
            True if successful
        """
        result = await self.generate_and_store_embeddings(merchant_id, [product])
        return result["failure_count"] == 0

