"""
AI Product Discovery Suite - Shopping Assistant Service

@category    Backend
@package     ShoppingAssistantService
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

from shared.config.settings import ShoppingAssistantSettings
from shared.database.base import init_database, close_database
from shared.middleware.correlation_id import CorrelationIDMiddleware
from shared.middleware.auth import APIKeyAuthMiddleware
from shared.middleware.rate_limiter import RateLimitMiddleware
from shared.monitoring.metrics import PrometheusMetricsMiddleware, metrics_endpoint
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import chat, sessions, health
from core.assistant import ShoppingAssistant
from core.conversation import ConversationManager


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
    logger.info("Starting Shopping Assistant Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize shopping assistant
        app.state.shopping_assistant = ShoppingAssistant()
        await app.state.shopping_assistant.initialize()
        logger.info("Shopping assistant initialized")
        
        # Initialize conversation manager
        app.state.conversation_manager = ConversationManager()
        await app.state.conversation_manager.initialize()
        logger.info("Conversation manager initialized")
        
        logger.info("Shopping Assistant Service startup complete")
        yield
        
    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise
        
    # Shutdown
    logger.info("Shutting down Shopping Assistant Service...")
    
    try:
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Clean up shopping assistant
        if hasattr(app.state, 'shopping_assistant'):
            await app.state.shopping_assistant.cleanup()
            logger.info("Shopping assistant cleaned up")
        
        # Clean up conversation manager
        if hasattr(app.state, 'conversation_manager'):
            await app.state.conversation_manager.cleanup()
            logger.info("Conversation manager cleaned up")
        
        logger.info("Shopping Assistant Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Initialize settings
settings = ShoppingAssistantSettings()

# Create FastAPI application
app = FastAPI(
    title="AI Product Discovery - Shopping Assistant Service",
    description="AI-powered shopping assistant for personalized shopping guidance",
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
app.add_middleware(PrometheusMetricsMiddleware, service_name="shopping-assistant-service")

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
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Product Discovery - Shopping Assistant Service",
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