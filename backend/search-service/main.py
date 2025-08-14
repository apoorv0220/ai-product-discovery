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
from api import search, autocomplete, index, health
from core.elasticsearch_client import ElasticsearchManager
from core.ml_engine import MLEngine


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
        
        # Close database connections
        await close_database()
        
        logger.info("Search Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Initialize settings
settings = SearchServiceSettings()

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
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(autocomplete.router, prefix="/api/v1/autocomplete", tags=["autocomplete"])
app.include_router(index.router, prefix="/api/v1/index", tags=["indexing"])


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
        workers=1 if settings.DEBUG else 4
    )