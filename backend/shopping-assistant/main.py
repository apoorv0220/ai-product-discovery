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