"""
AI Product Discovery Suite - Qdrant Client

Client for interacting with Qdrant vector database.

@category    Backend
@package     SearchService/Core
@license     MIT License
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import structlog

from shared.config.qdrant import (
    QDRANT_CONFIG,
    PRODUCT_COLLECTION_CONFIG,
    get_product_collection_name,
    get_collection_config,
    SEARCH_PARAMS,
    BATCH_CONFIG,
    DEFAULT_EMBEDDING_MODEL
)

logger = structlog.get_logger()


class QdrantManager:
    """
    Manages Qdrant vector database operations for product search.
    
    Handles:
    - Collection creation and management
    - Vector upsert and deletion
    - Similarity search
    - Health checks
    """
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Qdrant manager
        
        Args:
            url: Qdrant server URL (defaults to config)
            api_key: API key for Qdrant Cloud (optional)
        """
        self.url = url or QDRANT_CONFIG["url"]
        self.api_key = api_key or QDRANT_CONFIG["api_key"]
        self.client: Optional[QdrantClient] = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize Qdrant client and verify connection"""
        try:
            # Create synchronous client (Qdrant Python client doesn't have async yet)
            # Optimized for performance with connection pooling
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=QDRANT_CONFIG["timeout"],
                prefer_grpc=QDRANT_CONFIG["prefer_grpc"],
                https=QDRANT_CONFIG["https"]
            )
            
            # Verify connection
            collections = await asyncio.to_thread(self.client.get_collections)
            logger.info("Qdrant initialized",
                       url=self.url,
                       collections_count=len(collections.collections))
            
            self.initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize Qdrant", error=str(e), url=self.url)
            raise
    
    async def health_check(self) -> bool:
        """
        Check if Qdrant is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.client:
                return False
            
            # Try to get collections as health check
            await asyncio.to_thread(self.client.get_collections)
            return True
            
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False
    
    async def ensure_collection(
        self,
        merchant_id: int,
        model_name: str = DEFAULT_EMBEDDING_MODEL
    ) -> bool:
        """
        Ensure product collection exists for a merchant (creates if missing)
        
        Args:
            merchant_id: Merchant ID
            model_name: Embedding model name
            
        Returns:
            True if collection exists or was created successfully
        """
        return await self.create_collection(merchant_id, model_name)
    
    async def create_collection(
        self,
        merchant_id: int,
        model_name: str = DEFAULT_EMBEDDING_MODEL
    ) -> bool:
        """
        Create product collection for a merchant
        
        Args:
            merchant_id: Merchant ID
            model_name: Embedding model name
            
        Returns:
            True if created successfully
        """
        try:
            collection_name = get_product_collection_name(merchant_id)
            config = get_collection_config(model_name)
            
            # Check if collection already exists
            collections = await asyncio.to_thread(self.client.get_collections)
            existing = [c.name for c in collections.collections]
            
            if collection_name in existing:
                logger.info("Collection already exists",
                           collection=collection_name,
                           merchant_id=merchant_id)
                return True
            
            # Create collection
            await asyncio.to_thread(
                self.client.create_collection,
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=config["vector_size"],
                    distance=models.Distance.COSINE
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=config["hnsw_config"]["m"],
                    ef_construct=config["hnsw_config"]["ef_construct"],
                    full_scan_threshold=config["hnsw_config"]["full_scan_threshold"]
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    deleted_threshold=config["optimizers_config"]["deleted_threshold"],
                    vacuum_min_vector_number=config["optimizers_config"]["vacuum_min_vector_number"],
                    default_segment_number=config["optimizers_config"]["default_segment_number"]
                ),
                wal_config=models.WalConfigDiff(
                    wal_capacity_mb=config["wal_config"]["wal_capacity_mb"],
                    wal_segments_ahead=config["wal_config"]["wal_segments_ahead"]
                ),
                on_disk_payload=config["on_disk_payload"]
            )
            
            logger.info("Collection created",
                       collection=collection_name,
                       merchant_id=merchant_id,
                       vector_size=config["vector_size"])
            
            return True
            
        except Exception as e:
            logger.error("Failed to create collection",
                        merchant_id=merchant_id,
                        error=str(e))
            return False
    
    async def upsert_vectors(
        self,
        merchant_id: int,
        points: List[Tuple[str, List[float], Dict[str, Any]]]
    ) -> bool:
        """
        Upsert product vectors into collection
        
        Args:
            merchant_id: Merchant ID
            points: List of (id, vector, payload) tuples
            
        Returns:
            True if successful
        """
        try:
            collection_name = get_product_collection_name(merchant_id)
            
            # Ensure collection exists
            await self.create_collection(merchant_id)
            
            # Convert to Qdrant points
            qdrant_points = [
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                for point_id, vector, payload in points
            ]
            
            # Batch upsert
            batch_size = BATCH_CONFIG["upsert_batch_size"]
            for i in range(0, len(qdrant_points), batch_size):
                batch = qdrant_points[i:i + batch_size]
                
                await asyncio.to_thread(
                    self.client.upsert,
                    collection_name=collection_name,
                    points=batch
                )
            
            logger.info("Vectors upserted",
                       collection=collection_name,
                       merchant_id=merchant_id,
                       count=len(points))
            
            return True
            
        except Exception as e:
            logger.error("Failed to upsert vectors",
                        merchant_id=merchant_id,
                        error=str(e))
            return False
    
    async def search(
        self,
        merchant_id: int,
        query_vector: List[float],
        limit: int = 20,
        score_threshold: float = 0.5,
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar products using vector similarity
        
        Args:
            merchant_id: Merchant ID
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filter conditions
            
        Returns:
            List of search results with scores
        """
        try:
            collection_name = get_product_collection_name(merchant_id)
            
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                        for key, value in filter_conditions.items()
                    ]
                )
            
            # Search
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=min(limit, SEARCH_PARAMS["max_limit"]),
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for scored_point in search_result:
                result = {
                    "id": scored_point.id,
                    "score": scored_point.score,
                    **scored_point.payload
                }
                results.append(result)
            
            logger.info("Vector search completed",
                       collection=collection_name,
                       merchant_id=merchant_id,
                       results_count=len(results),
                       limit=limit)
            
            return results
            
        except UnexpectedResponse as e:
            if "Not found: Collection" in str(e):
                logger.warning("Collection not found for search",
                             merchant_id=merchant_id)
                return []
            raise
        except Exception as e:
            logger.error("Vector search failed",
                        merchant_id=merchant_id,
                        error=str(e))
            return []
    
    async def delete_vectors(
        self,
        merchant_id: int,
        point_ids: List[str]
    ) -> bool:
        """
        Delete product vectors from collection
        
        Args:
            merchant_id: Merchant ID
            point_ids: List of point IDs to delete
            
        Returns:
            True if successful
        """
        try:
            collection_name = get_product_collection_name(merchant_id)
            
            # Batch delete
            batch_size = BATCH_CONFIG["delete_batch_size"]
            for i in range(0, len(point_ids), batch_size):
                batch = point_ids[i:i + batch_size]
                
                await asyncio.to_thread(
                    self.client.delete,
                    collection_name=collection_name,
                    points_selector=models.PointIdsList(points=batch)
                )
            
            logger.info("Vectors deleted",
                       collection=collection_name,
                       merchant_id=merchant_id,
                       count=len(point_ids))
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete vectors",
                        merchant_id=merchant_id,
                        error=str(e))
            return False
    
    async def get_collection_info(self, merchant_id: int) -> Optional[Dict]:
        """
        Get information about collection
        
        Args:
            merchant_id: Merchant ID
            
        Returns:
            Collection info dictionary
        """
        try:
            collection_name = get_product_collection_name(merchant_id)
            
            info = await asyncio.to_thread(
                self.client.get_collection,
                collection_name=collection_name
            )
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status
            }
            
        except Exception as e:
            logger.error("Failed to get collection info",
                        merchant_id=merchant_id,
                        error=str(e))
            return None
    
    async def close(self):
        """Close Qdrant client connection"""
        if self.client:
            # Qdrant client doesn't need explicit closing
            self.client = None
            logger.info("Qdrant client closed")

