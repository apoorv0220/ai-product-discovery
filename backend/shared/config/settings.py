"""
AI Product Discovery Suite - Shared Settings

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "AI Product Discovery Suite"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 7099
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "discovery"
    ELASTICSEARCH_USERNAME: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ELASTICSEARCH_REQUEST_TIMEOUT: int = 30
    ELASTICSEARCH_MAX_RETRIES: int = 3
    ELASTICSEARCH_RETRY_ON_TIMEOUT: bool = True
    
    # Qdrant (Vector Database)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_GRPC_PORT: int = 6334
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8065"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None
    
    # ML Models
    MODEL_CACHE_DIR: str = "/tmp/models"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    RATE_LIMIT_FREE: int = 100
    RATE_LIMIT_BASIC: int = 1000
    RATE_LIMIT_PRO: int = 5000
    RATE_LIMIT_ENTERPRISE: int = 10000
    
    # Search Service Specific
    SEARCH_DEFAULT_LIMIT: int = 20
    SEARCH_MAX_LIMIT: int = 100
    AUTOCOMPLETE_DEFAULT_LIMIT: int = 10
    AUTOCOMPLETE_MAX_LIMIT: int = 50
    
    # Recommendation Service Specific
    RECOMMENDATION_DEFAULT_LIMIT: int = 12
    RECOMMENDATION_MAX_LIMIT: int = 50
    RECOMMENDATION_MIN_SCORE: float = 0.1
    
    # Analytics Service Specific
    ANALYTICS_BATCH_SIZE: int = 1000
    ANALYTICS_FLUSH_INTERVAL: int = 60  # seconds
    
    # Shopping Assistant Specific
    ASSISTANT_MAX_SESSION_TIME: int = 3600  # seconds
    ASSISTANT_MAX_MESSAGES_PER_SESSION: int = 100
    
    # OpenAI (Optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Service Ports (used in .env but overridden by service-specific classes)
    SEARCH_SERVICE_PORT: Optional[int] = None
    RECOMMENDATION_SERVICE_PORT: Optional[int] = None
    LISTING_OPTIMIZER_PORT: Optional[int] = None
    ANALYTICS_SERVICE_PORT: Optional[int] = None
    SHOPPING_ASSISTANT_PORT: Optional[int] = None
    
    # Magento Integration
    MAGENTO_BASE_URL: str = "http://localhost/magento2"
    MAGENTO_API_TOKEN: Optional[str] = None
    MAGENTO_API_USER: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Service-specific settings classes
class SearchServiceSettings(Settings):
    """Search service specific settings"""
    SERVICE_NAME: str = "search-service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use environment variable or default to 7099
        self.API_PORT = int(os.getenv('SEARCH_SERVICE_PORT', 7099))


class RecommendationServiceSettings(Settings):
    """Recommendation service specific settings"""
    SERVICE_NAME: str = "recommendation-service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.API_PORT = int(os.getenv('RECOMMENDATION_SERVICE_PORT', 7099))


class ListingOptimizerSettings(Settings):
    """Listing optimizer specific settings"""
    SERVICE_NAME: str = "listing-optimizer"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.API_PORT = int(os.getenv('LISTING_OPTIMIZER_PORT', 7099))


class AnalyticsServiceSettings(Settings):
    """Analytics service specific settings"""
    SERVICE_NAME: str = "analytics-service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.API_PORT = int(os.getenv('ANALYTICS_SERVICE_PORT', 7099))


class ShoppingAssistantSettings(Settings):
    """Shopping assistant specific settings"""
    SERVICE_NAME: str = "shopping-assistant"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.API_PORT = int(os.getenv('SHOPPING_ASSISTANT_PORT', 7099))