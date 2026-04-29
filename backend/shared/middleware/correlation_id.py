"""
AI Product Discovery Suite - Correlation ID Middleware

Generates and propagates correlation IDs for request tracing.

@category    Backend
@package     Shared/Middleware
@license     MIT License
"""

import uuid
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

# Configure structlog to include correlation_id in all logs
logger = structlog.get_logger()


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate correlation IDs across requests.
    
    Correlation IDs enable tracing requests across multiple services
    and make debugging distributed systems easier.
    
    Features:
    - Generates UUID for each request if not provided
    - Accepts existing correlation ID from upstream services
    - Injects correlation ID into all log statements
    - Returns correlation ID in response headers
    - Stores in request state for use in handlers
    """
    
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    REQUEST_ID_HEADER = "X-Request-ID"
    
    def __init__(self, app):
        """
        Initialize correlation ID middleware
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
    
    @staticmethod
    def generate_correlation_id() -> str:
        """
        Generate a new correlation ID
        
        Returns:
            UUID string for correlation ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_request_id() -> str:
        """
        Generate a new request ID
        
        Returns:
            UUID string for request ID
        """
        return str(uuid.uuid4())
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through correlation ID middleware
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with correlation ID headers
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            self.CORRELATION_ID_HEADER,
            self.generate_correlation_id()
        )
        
        # Always generate a unique request ID
        request_id = self.generate_request_id()
        
        # Store IDs in request state
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        
        # Bind IDs to logger context for this request
        # This ensures all logs from this request include these IDs
        logger_with_context = logger.bind(
            correlation_id=correlation_id,
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )
        
        # Store logger in request state
        request.state.logger = logger_with_context
        
        # Log request start
        logger_with_context.info(
            "Request started",
            user_agent=request.headers.get("user-agent", ""),
            client_host=request.client.host if request.client else None
        )
        
        # Process request
        response = await call_next(request)
        
        # Add correlation IDs to response headers
        response.headers[self.CORRELATION_ID_HEADER] = correlation_id
        response.headers[self.REQUEST_ID_HEADER] = request_id
        
        # Log request completion
        logger_with_context.info(
            "Request completed",
            status_code=response.status_code
        )
        
        return response


def get_correlation_id(request: Request) -> str:
    """
    Helper function to get correlation ID from request
    
    Args:
        request: FastAPI request
        
    Returns:
        Correlation ID string
    """
    return getattr(request.state, "correlation_id", "unknown")


def get_request_id(request: Request) -> str:
    """
    Helper function to get request ID from request
    
    Args:
        request: FastAPI request
        
    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")


def get_logger(request: Request) -> structlog.BoundLogger:
    """
    Helper function to get request-scoped logger with correlation context
    
    Args:
        request: FastAPI request
        
    Returns:
        Logger with correlation ID and request ID bound
    """
    # Return request-scoped logger if available
    request_logger = getattr(request.state, "logger", None)
    if request_logger:
        return request_logger
    
    # Fallback: create logger with available context
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    request_id = getattr(request.state, "request_id", "unknown")
    
    return logger.bind(
        correlation_id=correlation_id,
        request_id=request_id
    )

