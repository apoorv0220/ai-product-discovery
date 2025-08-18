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

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Log request
    logger.info("Request started", 
                method=request.method, 
                url=str(request.url),
                user_agent=request.headers.get("user-agent", ""))
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info("Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time)
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


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