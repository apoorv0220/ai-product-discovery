"""
AI Product Discovery Suite - Prometheus Metrics

Defines and exposes Prometheus metrics for monitoring.

@category    Backend
@package     Shared/Monitoring
@license     MIT License
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
import structlog

logger = structlog.get_logger()


# Create a custom registry (or use default)
REGISTRY = CollectorRegistry()

# ============================================================================
# APPLICATION INFO
# ============================================================================
app_info = Info(
    'app',
    'Application information',
    registry=REGISTRY
)

# ============================================================================
# REQUEST METRICS
# ============================================================================
# Counter for total requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service'],
    registry=REGISTRY
)

# Histogram for request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=REGISTRY
)

# Gauge for active requests
http_requests_active = Gauge(
    'http_requests_active',
    'Number of active HTTP requests',
    ['method', 'service'],
    registry=REGISTRY
)

# ============================================================================
# RATE LIMITING METRICS
# ============================================================================
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total number of rate limit exceeded events',
    ['merchant_id', 'tier', 'service'],
    registry=REGISTRY
)

# ============================================================================
# AUTHENTICATION METRICS
# ============================================================================
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result', 'service'],
    registry=REGISTRY
)

auth_failures_total = Counter(
    'auth_failures_total',
    'Total authentication failures',
    ['reason', 'service'],
    registry=REGISTRY
)

# API Key validation metrics
api_key_validation_duration_seconds = Histogram(
    'api_key_validation_duration_seconds',
    'API key validation duration in seconds',
    ['result', 'service'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0),
    registry=REGISTRY
)

api_key_validation_total = Counter(
    'api_key_validation_total',
    'Total API key validation attempts',
    ['result', 'cache_status', 'service'],
    registry=REGISTRY
)

# ============================================================================
# CACHE METRICS
# ============================================================================
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result', 'service'],
    registry=REGISTRY
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (0-1)',
    ['cache_type', 'service'],
    registry=REGISTRY
)

# ============================================================================
# DATABASE METRICS
# ============================================================================
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type', 'service'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    ['service'],
    registry=REGISTRY
)

db_errors_total = Counter(
    'db_errors_total',
    'Total database errors',
    ['error_type', 'service'],
    registry=REGISTRY
)

# ============================================================================
# ELASTICSEARCH METRICS
# ============================================================================
elasticsearch_query_duration_seconds = Histogram(
    'elasticsearch_query_duration_seconds',
    'Elasticsearch query duration in seconds',
    ['query_type', 'service'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY
)

elasticsearch_errors_total = Counter(
    'elasticsearch_errors_total',
    'Total Elasticsearch errors',
    ['error_type', 'service'],
    registry=REGISTRY
)

# ============================================================================
# QDRANT METRICS
# ============================================================================
qdrant_query_duration_seconds = Histogram(
    'qdrant_query_duration_seconds',
    'Qdrant vector query duration in seconds',
    ['operation', 'service'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY
)

qdrant_errors_total = Counter(
    'qdrant_errors_total',
    'Total Qdrant errors',
    ['error_type', 'service'],
    registry=REGISTRY
)

# ============================================================================
# SEARCH METRICS
# ============================================================================
search_queries_total = Counter(
    'search_queries_total',
    'Total search queries',
    ['search_type', 'merchant_id', 'service'],
    registry=REGISTRY
)

search_zero_results_total = Counter(
    'search_zero_results_total',
    'Total searches with zero results',
    ['search_type', 'service'],
    registry=REGISTRY
)

search_results_count = Histogram(
    'search_results_count',
    'Number of search results returned',
    ['search_type', 'service'],
    buckets=(0, 1, 5, 10, 20, 50, 100, 500, 1000),
    registry=REGISTRY
)

# ============================================================================
# RECOMMENDATION METRICS
# ============================================================================
recommendations_generated_total = Counter(
    'recommendations_generated_total',
    'Total recommendations generated',
    ['recommendation_type', 'merchant_id', 'service'],
    registry=REGISTRY
)

recommendation_quality_score = Histogram(
    'recommendation_quality_score',
    'Quality score of recommendations',
    ['recommendation_type', 'service'],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=REGISTRY
)

# ============================================================================
# EMBEDDING METRICS
# ============================================================================
embeddings_generated_total = Counter(
    'embeddings_generated_total',
    'Total embeddings generated',
    ['model', 'service'],
    registry=REGISTRY
)

embedding_generation_duration_seconds = Histogram(
    'embedding_generation_duration_seconds',
    'Embedding generation duration in seconds',
    ['model', 'batch_size', 'service'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY
)


# ============================================================================
# MIDDLEWARE FOR AUTOMATIC METRICS COLLECTION
# ============================================================================
class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect HTTP metrics for Prometheus.
    
    Tracks:
    - Request counts by endpoint, method, and status
    - Request duration histograms
    - Active request gauge
    """
    
    def __init__(self, app, service_name: str = "unknown"):
        """
        Initialize Prometheus metrics middleware
        
        Args:
            app: FastAPI application
            service_name: Name of the service for metric labels
        """
        super().__init__(app)
        self.service_name = service_name
        
        # Set application info
        app_info.info({
            'service': service_name,
            'version': '1.0.0'
        })
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and collect metrics
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip metrics for /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track active requests
        method = request.method
        endpoint = request.url.path
        
        http_requests_active.labels(
            method=method,
            service=self.service_name
        ).inc()
        
        # Track request timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            status_code = response.status_code
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                service=self.service_name
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                service=self.service_name
            ).observe(duration)
            
            # Store metrics in request state for logging
            request.state.response_time_ms = int(duration * 1000)
            
            return response
            
        except Exception as e:
            # Record error
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500,
                service=self.service_name
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                service=self.service_name
            ).observe(duration)
            
            logger.error("Request failed",
                        method=method,
                        endpoint=endpoint,
                        duration_seconds=duration,
                        error=str(e))
            
            raise
        
        finally:
            # Decrement active requests
            http_requests_active.labels(
                method=method,
                service=self.service_name
            ).dec()


def metrics_endpoint() -> Response:
    """
    Endpoint handler to expose Prometheus metrics
    
    Returns:
        Response with metrics in Prometheus format
    """
    metrics_data = generate_latest(REGISTRY)
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# HELPER FUNCTIONS FOR MANUAL METRIC RECORDING
# ============================================================================
def record_cache_operation(operation: str, result: str, service: str):
    """
    Record cache operation metric
    
    Args:
        operation: Operation type (get, set, delete, etc.)
        result: Result (hit, miss, success, error)
        service: Service name
    """
    cache_operations_total.labels(
        operation=operation,
        result=result,
        service=service
    ).inc()


def record_db_query(query_type: str, duration: float, service: str):
    """
    Record database query metric
    
    Args:
        query_type: Type of query (select, insert, update, delete)
        duration: Query duration in seconds
        service: Service name
    """
    db_query_duration_seconds.labels(
        query_type=query_type,
        service=service
    ).observe(duration)


def record_elasticsearch_query(query_type: str, duration: float, service: str):
    """
    Record Elasticsearch query metric
    
    Args:
        query_type: Type of query (search, autocomplete, etc.)
        duration: Query duration in seconds
        service: Service name
    """
    elasticsearch_query_duration_seconds.labels(
        query_type=query_type,
        service=service
    ).observe(duration)


def record_qdrant_query(operation: str, duration: float, service: str):
    """
    Record Qdrant query metric
    
    Args:
        operation: Operation type (search, upsert, etc.)
        duration: Query duration in seconds
        service: Service name
    """
    qdrant_query_duration_seconds.labels(
        operation=operation,
        service=service
    ).observe(duration)


def record_search_query(search_type: str, merchant_id: int, results_count: int, service: str):
    """
    Record search query metrics
    
    Args:
        search_type: Type of search (keyword, semantic, hybrid)
        merchant_id: Merchant ID
        results_count: Number of results returned
        service: Service name
    """
    search_queries_total.labels(
        search_type=search_type,
        merchant_id=str(merchant_id),
        service=service
    ).inc()
    
    search_results_count.labels(
        search_type=search_type,
        service=service
    ).observe(results_count)
    
    if results_count == 0:
        search_zero_results_total.labels(
            search_type=search_type,
            service=service
        ).inc()


def record_rate_limit_exceeded(merchant_id: int, tier: str, service: str):
    """
    Record rate limit exceeded event
    
    Args:
        merchant_id: Merchant ID
        tier: Merchant tier
        service: Service name
    """
    rate_limit_exceeded_total.labels(
        merchant_id=str(merchant_id),
        tier=tier,
        service=service
    ).inc()


def record_api_key_validation(result: str, duration: float, service: str = "search-service", cache_status: str = "unknown"):
    """
    Record API key validation metrics
    
    Args:
        result: Validation result (cache_hit, cache_miss, failed)
        duration: Validation duration in seconds
        service: Service name
        cache_status: Cache status (hit, miss, unavailable)
    """
    api_key_validation_duration_seconds.labels(
        result=result,
        service=service
    ).observe(duration)
    
    api_key_validation_total.labels(
        result=result,
        cache_status=cache_status,
        service=service
    ).inc()

