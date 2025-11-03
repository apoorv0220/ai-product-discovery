"""
AI Product Discovery Suite - Search Service

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import logging
import sys
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import structlog

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config.settings import SearchServiceSettings
from shared.database.base import init_database, close_database
from shared.middleware.correlation_id import CorrelationIDMiddleware
from shared.middleware.auth import APIKeyAuthMiddleware
from shared.middleware.rate_limiter import RateLimitMiddleware
from shared.monitoring.metrics import PrometheusMetricsMiddleware, metrics_endpoint
from api import search, autocomplete, index, health
from core.elasticsearch_client import ElasticsearchManager
from core.ml_engine import MLEngine
from fastapi.openapi.utils import get_openapi
from core.cache import SearchCache
import redis.asyncio as redis_async

# Initialize settings first
settings = SearchServiceSettings()

# Map LOG_LEVEL string to logging constants
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Configure standard library logging first (required for structlog)
# Respect LOG_LEVEL from environment or settings
log_level_str = settings.LOG_LEVEL.upper()
log_level = LOG_LEVEL_MAP.get(log_level_str, logging.INFO)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=log_level
)

# Set root logger level to match our LOG_LEVEL (required for structlog filtering)
logging.getLogger().setLevel(log_level)

# Configure processors based on log level
# At INFO level, use simpler human-readable format; at DEBUG, use full JSON
if log_level == logging.DEBUG:
    # DEBUG: Full JSON with all details
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ]
else:
    # INFO and above: Human-readable format (not JSON)
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Human-readable console renderer for INFO level
        structlog.dev.ConsoleRenderer(colors=False)
    ]

# Configure structured logging
structlog.configure(
    processors=processors,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Search Service")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize Elasticsearch
        es_manager = ElasticsearchManager()
        await es_manager.initialize()
        app.state.elasticsearch = es_manager
        logger.info("Elasticsearch initialized")
        
        # Initialize Redis cache for search
        try:
            redis_client = await redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            app.state.search_cache = SearchCache(redis_client)
            logger.info("Search cache initialized")
        except Exception as e:
            logger.warning("Failed to initialize Redis cache for search", error=str(e))

        # Initialize ML Engine
        ml_engine = MLEngine()
        await ml_engine.initialize()
        app.state.ml_engine = ml_engine
        logger.info("ML Engine initialized")
        
        logger.info("Search Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start Search Service", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Search Service")
    
    try:
        # Cleanup ML Engine
        if hasattr(app.state, 'ml_engine'):
            await app.state.ml_engine.cleanup()
        
        # Cleanup Elasticsearch
        if hasattr(app.state, 'elasticsearch'):
            await app.state.elasticsearch.close()

        # Close Redis cache
        if hasattr(app.state, 'search_cache'):
            try:
                await app.state.search_cache.redis.close()
            except Exception:
                pass
        
        # Close database connections
        await close_database()
        
        logger.info("Search Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))

# Create FastAPI application
app = FastAPI(
    title="AI Product Discovery Suite - Search Service",
    description="""
    **Advanced AI-Powered Search Service**
    
    ## 🚀 Key Features
    - **OpenAI Integration**: Semantic understanding and intelligent typo correction
    - **Natural Language Processing**: Understands queries like "I want comfortable hoodies"
    - **Smart Typo Correction**: Automatically fixes "Hro Hoodie" → "Hero Hoodie" 
    - **Intent Recognition**: Detects buy, compare, browse, and specific search intents
    - **Real-time Autocomplete**: Instant suggestions with rich product metadata
    - **Magento Integration**: Perfect synchronization with Magento frontend
    
    ## 🔌 Main Endpoints
    - **GET/POST** `/api/v1/autocomplete/` - Get AI-enhanced autocomplete suggestions
    - **POST** `/api/v1/search/` - Perform semantic product search with NLP
    - **POST** `/api/v1/index/products` - Index products for intelligent search
    - **GET** `/health` - Service health and status check
    
    ## 📊 Response Format
    All APIs return standardized JSON with comprehensive AI enhancement metadata:
    - Typo correction indicators and confidence scores
    - Search intent detection results  
    - Semantic processing information
    - Performance metrics and timing data
    
    ## 🎯 AI Capabilities
    - **Typo Tolerance**: Handles any misspelling using OpenAI
    - **Semantic Search**: Extracts meaning from natural language
    - **Intent Detection**: Understands user purchase intent
    - **Fallback Protection**: Graceful degradation if AI services unavailable
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add global Bearer auth (Authorize button in Swagger) applied to all endpoints
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    components["APIKeyAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "APIKey",
        "description": "Paste your API key (ak_...)"
    }
    openapi_schema["security"] = [{"APIKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add middleware in execution order (FastAPI executes in reverse order of addition)
# Execution order: CorrelationID -> Auth -> RateLimit -> Metrics -> GZip -> CORS

# 1. CORS (executes last in response, first in request routing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 2. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. Metrics (needs to measure everything, executes after other middleware)
app.add_middleware(PrometheusMetricsMiddleware, service_name="search-service")

# 4. Rate Limiting (needs merchant context from auth)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.REDIS_URL,
    burst_allowance=20,
    exempt_paths={"/health", "/health/", "/metrics", "/metrics/", "/docs", "/redoc", "/openapi.json"}
)

# 5. Authentication (validates API key, sets merchant context)
app.add_middleware(
    APIKeyAuthMiddleware,
    exempt_paths={
        "/", "/health", "/health/", "/metrics", "/metrics/",
        "/docs", "/docs/", "/redoc", "/redoc/", "/openapi.json", "/favicon.ico"
    }
)

# 6. Correlation ID (executes first to set correlation ID for all downstream)
app.add_middleware(CorrelationIDMiddleware)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error("Unhandled exception", 
                 error=str(exc),
                 method=request.method,
                 url=str(request.url))
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else "An error occurred"}
    )


# Add metrics endpoint (must be exempt from auth)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(autocomplete.router, prefix="/api/v1/autocomplete", tags=["autocomplete"])
app.include_router(index.router, prefix="/api/v1/index", tags=["indexing"])
# tracking endpoints are temporarily disabled until personalization models are wired


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Product Discovery - Search Service",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import time
    
    # Configure logging
    log_level = settings.LOG_LEVEL.upper()
    
    # Run server
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=log_level.lower(),
        reload=settings.DEBUG,
        workers=1  # Single worker for development (avoids connection pool issues)
    )