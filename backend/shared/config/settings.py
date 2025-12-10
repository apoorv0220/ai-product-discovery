"""
AI Product Discovery Suite - Shared Settings

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import os
import socket
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set environment-aware defaults after initialization
        self._configure_environment_specific_settings()

    def _configure_environment_specific_settings(self):
        """Configure settings based on environment detection"""
        environment = os.getenv('ENVIRONMENT', 'development')

        # Database configuration
        if not hasattr(self, '_db_configured') or not self._db_configured:
            self._configure_database()

        # Redis configuration
        if not hasattr(self, '_redis_configured') or not self._redis_configured:
            self._configure_redis()

        # Elasticsearch configuration
        if not hasattr(self, '_es_configured') or not self._es_configured:
            self._configure_elasticsearch()

        # Qdrant configuration
        if not hasattr(self, '_qdrant_configured') or not self._qdrant_configured:
            self._configure_qdrant()

    def _configure_database(self):
        """Configure database connection based on environment"""
        environment = os.getenv('ENVIRONMENT', 'development')

        if environment == 'production':
            # Production: Use internal Docker network names
            default_db_url = "postgresql+asyncpg://ai_user:ai_password_2024@postgres:5432/ai_discovery"
        else:
            # Development: Use external mapped ports
            db_host = os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', 'localhost'))
            db_port = os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', '7010'))
            db_name = os.getenv('POSTGRES_DB', os.getenv('DB_NAME', 'ai_discovery'))
            db_user = os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'ai_user'))
            db_password = os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', 'ai_password'))
            default_db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        self.DATABASE_URL = os.getenv('DATABASE_URL', default_db_url)
        self._db_configured = True

    def _configure_redis(self):
        """Configure Redis connection based on environment"""
        environment = os.getenv('ENVIRONMENT', 'development')

        if environment == 'production':
            # Production: Use internal Docker network names
            default_redis_url = "redis://:redis_password_2024@redis:6379/0"
            default_celery_broker = "redis://:redis_password_2024@redis:6379/1"
            default_celery_backend = "redis://:redis_password_2024@redis:6379/2"
        else:
            # Development: Use external mapped ports
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = os.getenv('REDIS_PORT', '6379')
            redis_password = os.getenv('REDIS_PASSWORD', '')

            auth_part = f":{redis_password}@" if redis_password else ""
            default_redis_url = f"redis://{auth_part}{redis_host}:{redis_port}/0"
            default_celery_broker = f"redis://{auth_part}{redis_host}:{redis_port}/1"
            default_celery_backend = f"redis://{auth_part}{redis_host}:{redis_port}/2"

        self.REDIS_URL = os.getenv('REDIS_URL', default_redis_url)
        self.CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', default_celery_broker)
        self.CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', default_celery_backend)
        self._redis_configured = True

    def _configure_elasticsearch(self):
        """Configure Elasticsearch connection based on environment"""
        environment = os.getenv('ENVIRONMENT', 'development')

        if environment == 'production':
            # Production: Use internal Docker network names
            default_es_url = "http://elasticsearch:9200"
        else:
            # Development: Use external mapped ports
            es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
            es_port = os.getenv('ELASTICSEARCH_PORT', os.getenv('ELASTICSEARCH_EXTERNAL_PORT', '7020'))
            default_es_url = f"http://{es_host}:{es_port}"

        self.ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', default_es_url)
        self._es_configured = True

    def _configure_qdrant(self):
        """Configure Qdrant connection based on environment"""
        environment = os.getenv('ENVIRONMENT', 'development')

        if environment == 'production':
            # Production: Use internal Docker network names
            default_qdrant_url = "http://qdrant:6333"
            default_qdrant_grpc = 6334
        else:
            # Development: Use external mapped ports
            qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
            qdrant_port = os.getenv('QDRANT_PORT', os.getenv('QDRANT_EXTERNAL_PORT', '7021'))
            qdrant_grpc_port = os.getenv('QDRANT_GRPC_PORT', os.getenv('QDRANT_GRPC_EXTERNAL_PORT', '7022'))
            default_qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
            default_qdrant_grpc = int(qdrant_grpc_port)

        self.QDRANT_URL = os.getenv('QDRANT_URL', default_qdrant_url)
        self.QDRANT_GRPC_PORT = int(os.getenv('QDRANT_GRPC_PORT', default_qdrant_grpc))
        self._qdrant_configured = True

    # Application
    APP_NAME: str = "AI Product Discovery Suite"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 7099
    API_PREFIX: str = "/api/v1"
    
    # Database (configured dynamically above)
    DATABASE_URL: str = ""  # Set by _configure_database
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis (configured dynamically above)
    REDIS_URL: str = ""  # Set by _configure_redis
    REDIS_MAX_CONNECTIONS: int = 10
    
    # Elasticsearch (configured dynamically above)
    ELASTICSEARCH_URL: str = ""  # Set by _configure_elasticsearch
    ELASTICSEARCH_INDEX_PREFIX: str = "discovery"
    ELASTICSEARCH_USERNAME: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ELASTICSEARCH_REQUEST_TIMEOUT: int = 30
    ELASTICSEARCH_MAX_RETRIES: int = 3
    ELASTICSEARCH_RETRY_ON_TIMEOUT: bool = True
    
    # Qdrant (Vector Database) (configured dynamically above)
    QDRANT_URL: str = ""  # Set by _configure_qdrant
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_GRPC_PORT: int = 6334  # Set by _configure_qdrant

    # Celery (configured dynamically above)
    CELERY_BROKER_URL: str = ""  # Set by _configure_redis
    CELERY_RESULT_BACKEND: str = ""  # Set by _configure_redis
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', "your-secret-key-change-in-production")
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', "your-jwt-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = os.getenv('CORS_ORIGINS',
        '["http://localhost:3000", "http://localhost:8065", "http://localhost:7099", "http://localhost:8091"]'
    ).strip('[]').replace('"', '').split(',')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', 'json')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE')
    
    # Monitoring
    ENABLE_METRICS: bool = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_PORT: int = int(os.getenv('METRICS_PORT', '9090'))
    SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')
    
    # ML Models
    MODEL_CACHE_DIR: str = os.getenv('MODEL_CACHE_DIR', '/tmp/models')
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
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
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Service Ports (used in .env but overridden by service-specific classes)
    SEARCH_SERVICE_PORT: Optional[int] = None
    RECOMMENDATION_SERVICE_PORT: Optional[int] = None
    LISTING_OPTIMIZER_PORT: Optional[int] = None
    ANALYTICS_SERVICE_PORT: Optional[int] = None
    SHOPPING_ASSISTANT_PORT: Optional[int] = None
    
    # Magento Integration
    MAGENTO_BASE_URL: str = os.getenv('MAGENTO_BASE_URL', 'http://localhost/magento2')
    MAGENTO_API_TOKEN: Optional[str] = os.getenv('MAGENTO_API_TOKEN')
    MAGENTO_API_USER: Optional[str] = os.getenv('MAGENTO_API_USER')
    MAGENTO_DB_HOST: Optional[str] = os.getenv('MAGENTO_DB_HOST')
    MAGENTO_DB_PORT: int = int(os.getenv('MAGENTO_DB_PORT', '3306'))
    MAGENTO_DB_NAME: Optional[str] = os.getenv('MAGENTO_DB_NAME')
    MAGENTO_DB_USER: Optional[str] = os.getenv('MAGENTO_DB_USER')
    MAGENTO_DB_PASSWORD: Optional[str] = os.getenv('MAGENTO_DB_PASSWORD')
    
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