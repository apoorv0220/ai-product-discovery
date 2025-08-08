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
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://discovery:discovery123@localhost:5432/discovery_suite"
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
    
    # Weaviate
    WEAVIATE_URL: str = "http://localhost:8065"
    WEAVIATE_API_KEY: Optional[str] = None
    
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
    API_PORT: int = 8001
    SERVICE_NAME: str = "search-service"


class RecommendationServiceSettings(Settings):
    """Recommendation service specific settings"""
    API_PORT: int = 8002
    SERVICE_NAME: str = "recommendation-service"


class ListingOptimizerSettings(Settings):
    """Listing optimizer specific settings"""
    API_PORT: int = 8003
    SERVICE_NAME: str = "listing-optimizer"


class AnalyticsServiceSettings(Settings):
    """Analytics service specific settings"""
    API_PORT: int = 8004
    SERVICE_NAME: str = "analytics-service"


class ShoppingAssistantSettings(Settings):
    """Shopping assistant specific settings"""
    API_PORT: int = 8005
    SERVICE_NAME: str = "shopping-assistant"