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
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file (dual environment support) - MUST happen before imports
try:
    from dotenv import load_dotenv
    import pathlib

    # Detect if running in Docker container
    in_docker = (
        pathlib.Path('/.dockerenv').exists() or  # Docker container marker
        os.getenv('HOSTNAME', '').startswith('ai_discovery_') or  # Container naming pattern
        pathlib.Path('/app').exists()  # Docker working directory
    )

    if in_docker:
        print("[INFO] Running in Docker container - using Docker-provided environment variables")
    else:
        # Local development: load from .env files
        env_paths = [
            pathlib.Path(__file__).parent.parent.parent / '.env.local',  # Local overrides
            pathlib.Path(__file__).parent.parent.parent / '.env',  # Project root
            pathlib.Path(__file__).parent.parent.parent / '.env.dev',  # Development
            pathlib.Path(__file__).parent.parent.parent / '.env.production',  # Production
        ]

        env_loaded = False
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                print(f"[SUCCESS] Loaded environment variables from {env_path}")
                env_loaded = True
                break

        if not env_loaded:
            print("[INFO] No .env file found - using system environment variables or defaults")

except ImportError:
    print("[WARNING] python-dotenv not available, skipping .env loading")

from shared.config.settings import AnalyticsServiceSettings
from shared.database.base import init_database, close_database
from shared.middleware.correlation_id import CorrelationIDMiddleware
from shared.middleware.auth import APIKeyAuthMiddleware
from shared.middleware.rate_limiter import RateLimitMiddleware
from shared.monitoring.metrics import PrometheusMetricsMiddleware, metrics_endpoint
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import dashboard, reports, health, tracking, metrics
from core.processor import EventProcessor
from core.aggregator import DataAggregator
from core.event_subscriber import EventSubscriber


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
        
        # Initialize event subscriber for Redis pub/sub
        app.state.event_subscriber = EventSubscriber(app.state.event_processor)
        await app.state.event_subscriber.start()
        logger.info("Event subscriber initialized")
        
        
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
        
        # Clean up event subscriber
        if hasattr(app.state, 'event_subscriber'):
            await app.state.event_subscriber.stop()
            logger.info("Event subscriber cleaned up")
        
        logger.info("Analytics Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Initialize settings
settings = AnalyticsServiceSettings()

from fastapi.openapi.utils import get_openapi

# Create FastAPI application
app = FastAPI(
    title="AI Product Discovery - Analytics Service",
    description="""
    **AI Product Discovery Suite - Analytics Service**

    ## 🚀 Analytics & Business Intelligence

    ### Key Features
    - **Real-time Event Processing**: High-throughput analytics event ingestion
    - **Behavioral Analytics**: User segmentation and behavior analysis
    - **Business Intelligence**: Dashboards, reports, and time-series metrics
    - **A/B Testing Framework**: Statistical analysis and automated optimization
    - **Conversion Optimization**: Revenue attribution and funnel analysis

    ### Main Endpoints
    - **POST** `/api/v1/events/track` - Track analytics events
    - **GET** `/api/v1/dashboard/overview` - Dashboard overview metrics
    - **GET** `/api/v1/dashboard/metrics` - Time-series metrics
    - **GET** `/api/v1/reports/performance` - Performance reports

    ### Authentication
    All endpoints require Bearer token authentication. Use your API key (ak_...) in the Authorization header.

    ### Event Types Supported
    - `page_view` - Page views and navigation
    - `product_view` - Product detail page views
    - `search` - Search queries performed
    - `add_to_cart` - Items added to cart
    - `remove_from_cart` - Items removed from cart
    - `purchase` - Purchase completions
    - `wishlist_add` - Items added to wishlist
    - `recommendation_click` - Recommendation clicks
    - `filter_apply` - Filter applications
    - `session_start` - Session beginnings
    - `session_end` - Session endings
    """,
    version="1.0.0",
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

# 1. CORS (executes last in response, first in response routing)
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
app.add_middleware(PrometheusMetricsMiddleware, service_name="analytics-service")

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
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(tracking.router, prefix="/api/v1/tracking", tags=["tracking"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])  
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])


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