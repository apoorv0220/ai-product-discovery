"""
AI Product Discovery Suite - Authentication Middleware

Validates API keys and injects merchant context into requests.

@category    Backend
@package     Shared/Middleware
@license     MIT License
"""

from typing import Callable, Optional, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.auth.api_key_manager import APIKeyManager
from shared.database.base import AsyncSessionLocal

logger = structlog.get_logger()


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests using API keys.
    
    Extracts API key from Authorization header, validates it,
    and injects merchant context into request state.
    """
    
    # Paths that don't require authentication
    EXEMPT_PATHS: Set[str] = {
        "/",
        "/health",
        "/health/",
        "/metrics",
        "/metrics/",
        "/docs",
        "/docs/",
        "/redoc",
        "/redoc/",
        "/openapi.json",
        "/favicon.ico"
    }
    
    def __init__(self, app, exempt_paths: Optional[Set[str]] = None):
        """
        Initialize authentication middleware
        
        Args:
            app: FastAPI application
            exempt_paths: Additional paths to exempt from authentication
        """
        super().__init__(app)
        
        # Merge custom exempt paths
        if exempt_paths:
            self.EXEMPT_PATHS = self.EXEMPT_PATHS.union(exempt_paths)
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from authentication
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt
        """
        # Exact match first
        if path in self.EXEMPT_PATHS:
            return True
        
        # Prefix-match for specific exempt prefixes, but avoid '/' catching everything
        for exempt_path in self.EXEMPT_PATHS:
            if exempt_path == "/":
                # Only exact '/' should be exempt, not every route
                continue
            if path.startswith(exempt_path):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through authentication middleware
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        try:
            # Skip authentication for exempt paths
            if self.is_path_exempt(request.url.path):
                logger.debug("Path exempt from authentication", path=request.url.path)
                return await call_next(request)
            
            # Extract API key from Authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header:
                logger.warning("Missing Authorization header",
                              path=request.url.path,
                              method=request.method)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Unauthorized",
                        "message": "Missing Authorization header",
                        "hint": "Include 'Authorization: Bearer <your_api_key>' in headers"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Parse Bearer token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                logger.warning("Invalid Authorization header format",
                              path=request.url.path,
                              method=request.method)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Unauthorized",
                        "message": "Invalid Authorization header format",
                        "hint": "Use format: 'Authorization: Bearer <your_api_key>'"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            api_key = parts[1]
            key_prefix = APIKeyManager.extract_prefix(api_key) if api_key else ""
            
            # Validate API key
            logger.debug("Validating API key",
                       path=request.url.path,
                       key_prefix=key_prefix)
            
            # Get database session (middleware optimization - create session directly)
            try:
                # Create session directly for middleware (more efficient than generator)
                async with AsyncSessionLocal() as db:
                    try:
                        # Get Redis client from app state if available (for API key caching)
                        redis_client = None
                        try:
                            # Try to get Redis client from app state
                            # Different services store it differently
                            if hasattr(request.app.state, 'search_cache'):
                                redis_client = request.app.state.search_cache.redis
                                logger.debug("Using Redis client from search_cache")
                            elif hasattr(request.app.state, 'redis_client'):
                                redis_client = request.app.state.redis_client
                                logger.debug("Using Redis client from redis_client")
                            else:
                                logger.debug("No Redis client found in app state")
                        except Exception as e:
                            logger.debug("Error getting Redis client", error=str(e))
                        
                        api_key_manager = APIKeyManager(db, redis_client=redis_client)
                        merchant_context = await api_key_manager.validate_api_key(api_key)
                    except Exception as e:
                        logger.error("API key validation raised exception",
                                     error=str(e),
                                     error_type=type(e).__name__,
                                     path=request.url.path,
                                     method=request.method,
                                     key_prefix=key_prefix,
                                     exc_info=True)
                        return JSONResponse(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={
                                "error": "Internal Server Error",
                                "message": "Authentication backend error"
                            }
                        )
                    
                    if not merchant_context:
                        logger.warning("Invalid API key",
                                      path=request.url.path,
                                      method=request.method,
                                      key_prefix=key_prefix)
                        return JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={
                                "error": "Unauthorized",
                                "message": "Invalid or expired API key",
                                "hint": "Check your API key or generate a new one"
                            },
                            headers={"WWW-Authenticate": "Bearer"}
                        )
                    
                    # Check merchant status
                    if merchant_context.get("merchant_status") != "active":
                        logger.warning("Inactive merchant",
                                      merchant_id=merchant_context.get("merchant_id"),
                                      status=merchant_context.get("merchant_status"))
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "error": "Forbidden",
                                "message": "Merchant account is not active",
                                "hint": "Contact support to reactivate your account"
                            }
                        )
                    
                    # Inject merchant context into request state
                    request.state.merchant_id = merchant_context["merchant_id"]
                    request.state.merchant_name = merchant_context["merchant_name"]
                    request.state.merchant_tier = merchant_context["merchant_tier"]
                    request.state.api_key_id = merchant_context["api_key_id"]
                    request.state.rate_limit = merchant_context["rate_limit_per_minute"]
                    request.state.scopes = merchant_context["scopes"]
                    
                    logger.debug("Request authenticated",
                                merchant_id=merchant_context["merchant_id"],
                                merchant_name=merchant_context["merchant_name"],
                                path=request.url.path,
                                method=request.method)
                    
                    # Continue to next middleware/handler
                    response = await call_next(request)
                    
                    # Add merchant context to response headers (for debugging)
                    response.headers["X-Merchant-ID"] = str(merchant_context["merchant_id"])
                    response.headers["X-Rate-Limit"] = str(merchant_context["rate_limit_per_minute"])
                    
                    return response
                    
            except Exception as e:
                logger.error("Failed to obtain database session for API key validation",
                           error=str(e),
                           error_type=type(e).__name__,
                           path=request.url.path,
                           method=request.method,
                           key_prefix=key_prefix,
                           exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "Internal Server Error",
                        "message": "Authentication service unavailable"
                    }
                )
        
        except Exception as e:
            logger.error("Authentication middleware error",
                        error=str(e),
                        error_type=type(e).__name__,
                        path=request.url.path,
                        method=request.method,
                        exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "Authentication failed due to server error"
                }
            )


def get_merchant_id(request: Request) -> int:
    """
    Helper function to get merchant ID from request state
    
    Args:
        request: FastAPI request
        
    Returns:
        Merchant ID
        
    Raises:
        HTTPException: If merchant ID not found in request state
    """
    merchant_id = getattr(request.state, "merchant_id", None)
    
    if merchant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return merchant_id


def get_merchant_context(request: Request) -> dict:
    """
    Helper function to get full merchant context from request state
    
    Args:
        request: FastAPI request
        
    Returns:
        Dictionary with merchant context
        
    Raises:
        HTTPException: If merchant context not found in request state
    """
    merchant_id = getattr(request.state, "merchant_id", None)
    
    if merchant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return {
        "merchant_id": request.state.merchant_id,
        "merchant_name": getattr(request.state, "merchant_name", ""),
        "merchant_tier": getattr(request.state, "merchant_tier", "free"),
        "api_key_id": getattr(request.state, "api_key_id", None),
        "rate_limit": getattr(request.state, "rate_limit", 100),
        "scopes": getattr(request.state, "scopes", [])
    }


def require_scope(required_scope: str):
    """
    Decorator to require specific scope for endpoint access
    
    Args:
        required_scope: Scope required (e.g., 'write', 'admin')
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            scopes = getattr(request.state, "scopes", [])
            
            if required_scope not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Scope '{required_scope}' required for this operation"
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator

