"""
AI Product Discovery Suite - Rate Limiting Middleware

Implements token bucket algorithm for API rate limiting.

@category    Backend
@package     Shared/Middleware
@license     MIT License
"""

import time
from typing import Callable, Optional, Set
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis_async
import structlog

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting using Redis token bucket algorithm.
    
    Tracks requests per API key and enforces tiered rate limits.
    """
    
    # Paths exempt from rate limiting (typically health checks and metrics)
    EXEMPT_PATHS: Set[str] = {
        "/health",
        "/health/",
        "/metrics",
        "/metrics/"
    }
    
    def __init__(
        self,
        app,
        redis_url: str,
        burst_allowance: int = 20,
        exempt_paths: Optional[Set[str]] = None
    ):
        """
        Initialize rate limiting middleware
        
        Args:
            app: FastAPI application
            redis_url: Redis connection URL
            burst_allowance: Additional burst capacity beyond rate limit
            exempt_paths: Additional paths to exempt from rate limiting
        """
        super().__init__(app)
        self.redis_url = redis_url
        self.burst_allowance = burst_allowance
        self.redis_client: Optional[redis_async.Redis] = None
        
        # Merge custom exempt paths
        if exempt_paths:
            self.EXEMPT_PATHS = self.EXEMPT_PATHS.union(exempt_paths)
    
    async def get_redis_client(self) -> redis_async.Redis:
        """Get or create Redis client"""
        if self.redis_client is None:
            self.redis_client = await redis_async.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from rate limiting
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt
        """
        return path in self.EXEMPT_PATHS or any(
            path.startswith(exempt) for exempt in self.EXEMPT_PATHS
        )
    
    async def check_rate_limit(
        self,
        api_key_id: int,
        rate_limit: int
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit using token bucket algorithm
        
        Args:
            api_key_id: API key ID
            rate_limit: Maximum requests per minute
            
        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        try:
            redis_client = await self.get_redis_client()
            
            # Redis keys
            tokens_key = f"rate_limit:tokens:{api_key_id}"
            timestamp_key = f"rate_limit:timestamp:{api_key_id}"
            
            current_time = time.time()
            
            # Get current tokens and last update time
            pipe = redis_client.pipeline()
            pipe.get(tokens_key)
            pipe.get(timestamp_key)
            results = await pipe.execute()
            
            tokens = float(results[0]) if results[0] else rate_limit
            last_update = float(results[1]) if results[1] else current_time
            
            # Calculate time elapsed and tokens to add
            time_elapsed = current_time - last_update
            tokens_to_add = (time_elapsed / 60.0) * rate_limit
            
            # Refill tokens (cap at rate_limit + burst)
            max_tokens = rate_limit + self.burst_allowance
            tokens = min(tokens + tokens_to_add, max_tokens)
            
            # Check if request can be allowed
            if tokens >= 1:
                # Consume one token
                tokens -= 1
                allowed = True
                
                # Update Redis
                pipe = redis_client.pipeline()
                pipe.setex(tokens_key, 120, str(tokens))  # Expire in 2 minutes
                pipe.setex(timestamp_key, 120, str(current_time))
                await pipe.execute()
                
                return allowed, {
                    "allowed": True,
                    "remaining": int(tokens),
                    "limit": rate_limit,
                    "reset_in": 60 - (time_elapsed % 60)
                }
            else:
                # Rate limit exceeded
                return False, {
                    "allowed": False,
                    "remaining": 0,
                    "limit": rate_limit,
                    "reset_in": 60 - (time_elapsed % 60),
                    "retry_after": int(60 - (time_elapsed % 60))
                }
        
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), api_key_id=api_key_id)
            # On error, allow request (fail open)
            return True, {
                "allowed": True,
                "remaining": rate_limit,
                "limit": rate_limit,
                "reset_in": 60,
                "error": "Rate limit check failed"
            }
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through rate limiting middleware
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip rate limiting for exempt paths
        if self.is_path_exempt(request.url.path):
            return await call_next(request)
        
        # Check if authentication has set API key info
        api_key_id = getattr(request.state, "api_key_id", None)
        merchant_id = getattr(request.state, "merchant_id", None)
        rate_limit = getattr(request.state, "rate_limit", 100)
        
        if api_key_id is None:
            # No API key in request state - either exempt or auth failed
            # Let it pass (auth middleware will handle if needed)
            return await call_next(request)
        
        # Check rate limit
        allowed, limit_info = await self.check_rate_limit(api_key_id, rate_limit)
        
        # Add rate limit headers to response
        async def add_rate_limit_headers(response):
            """Add rate limit headers to response"""
            response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + limit_info["reset_in"]))
            return response
        
        if not allowed:
            # Rate limit exceeded
            logger.warning("Rate limit exceeded",
                          api_key_id=api_key_id,
                          merchant_id=merchant_id,
                          path=request.url.path,
                          method=request.method)
            
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded",
                    "limit": limit_info["limit"],
                    "retry_after": limit_info.get("retry_after", 60)
                }
            )
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + limit_info["reset_in"]))
            response.headers["Retry-After"] = str(limit_info.get("retry_after", 60))
            
            return response
        
        # Request allowed - continue processing
        logger.debug("Rate limit check passed",
                    api_key_id=api_key_id,
                    merchant_id=merchant_id,
                    remaining=limit_info["remaining"])
        
        # Store limit info in request state for potential use in handlers
        request.state.rate_limit_info = limit_info
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response = await add_rate_limit_headers(response)
        
        return response
    
    async def close(self):
        """Clean up Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


async def track_api_usage(
    api_key_id: int,
    merchant_id: int,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """
    Track API usage for analytics and billing
    
    This function should be called after request completion to log usage.
    Can be done asynchronously in background for better performance.
    
    Args:
        api_key_id: API key ID
        merchant_id: Merchant ID
        endpoint: Request endpoint
        method: HTTP method
        status_code: Response status code
        response_time_ms: Response time in milliseconds
        ip_address: Client IP address
        user_agent: Client user agent
        request_id: Unique request ID
        correlation_id: Correlation ID for tracing
    """
    try:
        from shared.database.base import get_db
        from shared.models import APIKeyUsage
        
        async for db in get_db():
            usage = APIKeyUsage(
                api_key_id=api_key_id,
                merchant_id=merchant_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                correlation_id=correlation_id,
            )
            db.add(usage)
            await db.commit()
    except Exception as e:
        logger.error(
            "Failed to track API usage",
                    error=str(e),
                    api_key_id=api_key_id,
            merchant_id=merchant_id,
        )

