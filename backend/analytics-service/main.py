"""
AI Product Discovery Suite - Analytics Service

@category    Backend
@package     AnalyticsService
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

from shared.config.settings import AnalyticsServiceSettings
from shared.database.base import init_database, close_database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import events, dashboard, reports, health
from core.processor import EventProcessor
from core.aggregator import DataAggregator


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
    logger.info("Starting Analytics Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize event processor
        app.state.event_processor = EventProcessor()
        await app.state.event_processor.initialize()
        logger.info("Event processor initialized")
        
        # Initialize data aggregator
        app.state.data_aggregator = DataAggregator()
        await app.state.data_aggregator.initialize()
        logger.info("Data aggregator initialized")
        
        logger.info("Analytics Service startup complete")
        yield
        
    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise
        
    # Shutdown
    logger.info("Shutting down Analytics Service...")
    
    try:
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Clean up event processor
        if hasattr(app.state, 'event_processor'):
            await app.state.event_processor.cleanup()
            logger.info("Event processor cleaned up")
        
        # Clean up data aggregator
        if hasattr(app.state, 'data_aggregator'):
            await app.state.data_aggregator.cleanup()
            logger.info("Data aggregator cleaned up")
        
        logger.info("Analytics Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Initialize settings
settings = AnalyticsServiceSettings()

# Create FastAPI application
app = FastAPI(
    title="AI Product Discovery - Analytics Service",
    description="Analytics and tracking service for e-commerce insights",
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
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])  
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Product Discovery - Analytics Service",
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