"""
AI Product Discovery Suite - Qdrant Configuration

Configuration for Qdrant vector database.

@category    Backend
@package     Shared/Config
@license     MIT License
"""

from typing import Optional
from shared.config.settings import get_settings


# Qdrant connection configuration (lazy loaded)
def _get_qdrant_config():
    settings = get_settings()
    return {
        "url": settings.QDRANT_URL,
        "api_key": settings.QDRANT_API_KEY,  # Set if using Qdrant Cloud
        "timeout": 30,
        "prefer_grpc": False,  # Use HTTP by default
        "https": False
    }

def get_qdrant_config():
    return _get_qdrant_config()

# For backward compatibility
QDRANT_CONFIG = property(get_qdrant_config)


# Collection configurations
PRODUCT_COLLECTION_CONFIG = {
    "vector_size": 384,  # for all-MiniLM-L6-v2
    "distance": "Cosine",
    "on_disk_payload": True,  # Store payload on disk to save memory
    "hnsw_config": {
        "m": 16,  # Number of edges per node
        "ef_construct": 100,  # Size of the dynamic candidate list
        "full_scan_threshold": 10000  # Use full scan for small collections
    },
    "optimizers_config": {
        "deleted_threshold": 0.2,
        "vacuum_min_vector_number": 1000,
        "default_segment_number": 2
    },
    "wal_config": {
        "wal_capacity_mb": 32,
        "wal_segments_ahead": 0
    }
}


# Alternate configuration for OpenAI embeddings
PRODUCT_COLLECTION_CONFIG_OPENAI = {
    "vector_size": 1536,  # for text-embedding-ada-002
    "distance": "Cosine",
    "on_disk_payload": True,
    "hnsw_config": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
    }
}


# Index configurations for different models
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2": {
        "vector_size": 384,
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "max_seq_length": 256
    },
    "all-mpnet-base-v2": {
        "vector_size": 768,
        "model_name": "sentence-transformers/all-mpnet-base-v2",
        "max_seq_length": 384
    },
    "text-embedding-ada-002": {
        "vector_size": 1536,
        "model_name": "text-embedding-ada-002",
        "provider": "openai"
    },
    "text-embedding-3-small": {
        "vector_size": 1536,
        "model_name": "text-embedding-3-small",
        "provider": "openai"
    }
}


# Default model to use
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_collection_name(base_name: str, merchant_id: int) -> str:
    """
    Get collection name with merchant ID for multi-tenancy
    
    Args:
        base_name: Base collection name (e.g., 'products')
        merchant_id: Merchant ID
        
    Returns:
        Full collection name with merchant isolation
    """
    return f"{base_name}_merchant_{merchant_id}"


def get_product_collection_name(merchant_id: int) -> str:
    """
    Get product collection name for specific merchant
    
    Args:
        merchant_id: Merchant ID
        
    Returns:
        Product collection name
    """
    return get_collection_name("products", merchant_id)


def get_collection_config(model_name: str = DEFAULT_EMBEDDING_MODEL) -> dict:
    """
    Get collection configuration for specific embedding model
    
    Args:
        model_name: Name of embedding model
        
    Returns:
        Collection configuration dictionary
    """
    model_config = EMBEDDING_MODELS.get(model_name, EMBEDDING_MODELS[DEFAULT_EMBEDDING_MODEL])
    
    config = PRODUCT_COLLECTION_CONFIG.copy()
    config["vector_size"] = model_config["vector_size"]
    
    return config


# Search parameters
SEARCH_PARAMS = {
    "default_limit": 20,
    "max_limit": 100,
    "default_score_threshold": 0.5,  # Minimum similarity score
    "hnsw_ef": 128,  # Size of the dynamic candidate list for search
}


# Payload schema for products
PRODUCT_PAYLOAD_SCHEMA = {
    "product_id": "integer",
    "merchant_id": "integer",
    "sku": "keyword",
    "name": "text",
    "description": "text",
    "category_id": "integer",
    "category_name": "text",
    "price": "float",
    "special_price": "float",
    "is_in_stock": "bool",
    "image_url": "keyword",
    "url_key": "keyword",
    "created_at": "datetime",
    "updated_at": "datetime"
}


# Batch processing configuration
BATCH_CONFIG = {
    "upsert_batch_size": 100,
    "search_batch_size": 50,
    "delete_batch_size": 100,
    "max_retries": 3,
    "retry_delay": 1  # seconds
}

