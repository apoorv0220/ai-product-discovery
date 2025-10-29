"""
AI Product Discovery Suite - Recommendation Service

@category    Backend
@package     RecommendationService
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

from shared.config.settings import RecommendationServiceSettings
from shared.database.base import init_database, close_database
from shared.middleware.correlation_id import CorrelationIDMiddleware
from shared.middleware.auth import APIKeyAuthMiddleware
from shared.middleware.rate_limiter import RateLimitMiddleware
from shared.monitoring.metrics import PrometheusMetricsMiddleware, metrics_endpoint
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import recommendations, health, analytics, sync
from core.engine import RecommendationEngine
from core.ml_models import MLModelManager


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Recommendation Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize recommendation engine
        app.state.recommendation_engine = RecommendationEngine()
        await app.state.recommendation_engine.initialize()
        logger.info("Recommendation engine initialized")
        
        # Initialize ML models
        app.state.ml_models = MLModelManager()
        await app.state.ml_models.load_models()
        logger.info("ML models loaded")
        
        logger.info("Recommendation Service startup complete")
        yield
        
    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise
        
    # Shutdown
    logger.info("Shutting down Recommendation Service...")
    
    try:
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Clean up recommendation engine
        if hasattr(app.state, 'recommendation_engine'):
            await app.state.recommendation_engine.cleanup()
            logger.info("Recommendation engine cleaned up")
        
        # Clean up ML models
        if hasattr(app.state, 'ml_models'):
            await app.state.ml_models.cleanup()
            logger.info("ML models cleaned up")
        
        logger.info("Recommendation Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Initialize settings
settings = RecommendationServiceSettings()

# Create FastAPI application
app = FastAPI(
    title="AI Product Discovery - Recommendation Service",
    description="AI-powered product recommendation service for e-commerce",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

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
app.add_middleware(PrometheusMetricsMiddleware, service_name="recommendation-service")

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
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Product Discovery - Recommendation Service",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


if __name__ == "__main__":
    # Configure logging
    log_level = settings.LOG_LEVEL.upper()
    
    # Run server
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=log_level.lower(),
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4
    )