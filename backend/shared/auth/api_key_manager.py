"""
AI Product Discovery Suite - API Key Management

Handles API key generation, validation, and lifecycle management.

@category    Backend
@package     Shared/Auth
@license     MIT License
"""

import secrets
import string
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import bcrypt
import json
import time
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.models import Merchant, APIKey, APIKeyUsage

logger = structlog.get_logger()


class APIKeyManager:
    """
    Manages API key lifecycle: generation, validation, rotation, and revocation.
    
    API Key Format: ak_{env}_{random32}
    - ak: prefix indicating API key
    - env: environment (live, test)
    - random32: 32 character random string
    
    Example: ak_live_7x9k2m5p8q3w6e1r4t7y0u9i8o7p6a5s
    """
    
    # API key configuration
    KEY_PREFIX = "ak"
    KEY_LENGTH = 32
    PREFIX_LENGTH = 8  # Length of prefix stored for identification
    
    # Rate limit tiers (requests per minute)
    RATE_LIMITS = {
        'free': 100,
        'basic': 1000,
        'pro': 5000,
        'enterprise': 10000
    }
    
    def __init__(self, db: AsyncSession, redis_client=None):
        """
        Initialize API Key Manager
        
        Args:
            db: Async database session
            redis_client: Optional Redis client for caching API keys
        """
        self.db = db
        self.redis_client = redis_client
        self.CACHE_TTL = 600  # 10 minutes cache TTL
        self.CACHE_PREFIX = "api_key:"
    
    @staticmethod
    def generate_key(environment: str = 'live') -> str:
        """
        Generate a new API key with secure random characters
        
        Args:
            environment: Environment type (live, test)
            
        Returns:
            Generated API key string
        """
        # Use cryptographically secure random generation
        alphabet = string.ascii_lowercase + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(APIKeyManager.KEY_LENGTH))
        
        return f"{APIKeyManager.KEY_PREFIX}_{environment}_{random_part}"
    
    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash API key using bcrypt for secure storage
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Bcrypt hash of the key
        """
        # Use bcrypt with salt for secure hashing
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(api_key.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_key(api_key: str, key_hash: str) -> bool:
        """
        Verify API key against stored hash
        
        Args:
            api_key: Plain text API key to verify
            key_hash: Stored bcrypt hash
            
        Returns:
            True if key matches hash
        """
        try:
            return bcrypt.checkpw(api_key.encode('utf-8'), key_hash.encode('utf-8'))
        except Exception as e:
            logger.error("API key verification failed", error=str(e))
            return False
    
    @staticmethod
    def extract_prefix(api_key: str) -> str:
        """
        Extract identifiable prefix from API key
        
        Args:
            api_key: Full API key
            
        Returns:
            First 8 characters for identification
        """
        return api_key[:APIKeyManager.PREFIX_LENGTH]
    
    async def create_api_key(
        self,
        merchant_id: int,
        name: str,
        description: Optional[str] = None,
        tier: Optional[str] = None,
        environment: str = 'live',
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a new API key for a merchant
        
        Args:
            merchant_id: ID of the merchant
            name: Descriptive name for the key
            description: Optional description
            tier: Rate limit tier (free, basic, pro, enterprise)
            environment: Environment (live, test)
            scopes: List of permitted scopes
            expires_in_days: Optional expiration in days
            created_by: User ID who created the key
            
        Returns:
            Tuple of (plain_text_key, key_record_dict)
        """
        # Get merchant tier if not specified
        if tier is None:
            result = await self.db.execute(
                select(Merchant.tier).where(Merchant.id == merchant_id)
            )
            tier = result.scalar_one_or_none()
            if tier is None:
                raise ValueError(f"Merchant {merchant_id} not found")
        
        # Generate API key
        api_key = self.generate_key(environment)
        key_hash = self.hash_key(api_key)
        key_prefix = self.extract_prefix(api_key)
        
        # Set rate limit based on tier
        rate_limit = self.RATE_LIMITS.get(tier, self.RATE_LIMITS['free'])
        
        # Default scopes
        if scopes is None:
            scopes = ['read', 'write']
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Insert into database via ORM
        api_key_obj = APIKey(
            merchant_id=merchant_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            description=description,
            rate_limit_per_minute=rate_limit,
            status="active",
            scopes=scopes,
            expires_at=expires_at,
            created_by=created_by,
        )

        self.db.add(api_key_obj)
        await self.db.flush()
        await self.db.refresh(api_key_obj)
        await self.db.commit()
        
        # Prepare response
        key_record = {
            "id": api_key_obj.id,
            "merchant_id": api_key_obj.merchant_id,
            "key_prefix": api_key_obj.key_prefix,
            "name": api_key_obj.name,
            "rate_limit_per_minute": api_key_obj.rate_limit_per_minute,
            "status": api_key_obj.status,
            "scopes": api_key_obj.scopes,
            "created_at": api_key_obj.created_at,
            "expires_at": api_key_obj.expires_at,
        }
        
        logger.info("API key created",
                   merchant_id=merchant_id,
                   key_prefix=key_prefix,
                   name=name,
                   tier=tier)
        
        return api_key, key_record
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return merchant context with Redis caching.
        
        Args:
            api_key: Plain text API key to validate
            
        Returns:
            Dictionary with merchant context if valid, None otherwise
        """
        start_time = time.time()
        key_prefix = self.extract_prefix(api_key)
        cache_key = f"{self.CACHE_PREFIX}{api_key}"
        
        try:
            # Try to get from cache first
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.get(cache_key)
                    if cached_data:
                        cache_duration = time.time() - start_time
                        logger.info("API key validated (cache hit)",
                                   key_prefix=key_prefix,
                                   cache_duration_ms=cache_duration * 1000)
                        # Record cache hit metric
                        try:
                            from shared.monitoring.metrics import record_api_key_validation
                            record_api_key_validation("cache_hit", cache_duration, cache_status="hit")
                        except ImportError:
                            pass
                        return json.loads(cached_data)
                except Exception as cache_error:
                    logger.debug("Cache lookup failed, falling back to database",
                                error=str(cache_error))
            
            # Cache miss or no Redis - query database
            db_start = time.time()

            stmt = (
                select(
                    APIKey.id,
                    APIKey.merchant_id,
                    APIKey.key_hash,
                    APIKey.name,
                    APIKey.rate_limit_per_minute,
                    APIKey.status,
                    APIKey.scopes,
                    APIKey.expires_at,
                    Merchant.name.label("merchant_name"),
                    Merchant.tier,
                    Merchant.status.label("merchant_status"),
                )
                .join(Merchant, APIKey.merchant_id == Merchant.id)
                .where(
                    APIKey.key_prefix == key_prefix,
                    APIKey.status == "active",
                    Merchant.status == "active",
                    func.coalesce(APIKey.expires_at > func.now(), True),
                )
            )
            
            result = await self.db.execute(stmt)
            rows = result.fetchall()
            db_query_duration = time.time() - db_start
            
            logger.info("API key lookup by prefix",
                        key_prefix=key_prefix,
                        candidate_count=len(rows),
                        db_query_duration_ms=db_query_duration * 1000)
            
            # Try to verify against each potential match
            for row in rows:
                verify_start = time.time()
                if self.verify_key(api_key, row.key_hash):
                    verify_duration = time.time() - verify_start
                    total_duration = time.time() - start_time
                    
                    # Update last used timestamp (async, don't block)
                    await self.db.execute(
                        update(APIKey)
                        .where(APIKey.id == row.id)
                        .values(
                            last_used_at=func.now(),
                            usage_count=APIKey.usage_count + 1,
                        )
                    )
                    await self.db.commit()
                    
                    # Return merchant context
                    context = {
                        "api_key_id": row.id,
                        "merchant_id": row.merchant_id,
                        "merchant_name": row.merchant_name,
                        "merchant_tier": row.tier,
                        "merchant_status": row.merchant_status,
                        "key_name": row.name,
                        "rate_limit_per_minute": row.rate_limit_per_minute,
                        "scopes": row.scopes,
                    }
                    
                    # Cache the result
                    if self.redis_client:
                        try:
                            await self.redis_client.setex(
                                cache_key,
                                self.CACHE_TTL,
                                json.dumps(context)
                            )
                        except Exception as cache_error:
                            logger.debug("Failed to cache API key validation",
                                       error=str(cache_error))
                    
                    logger.info("API key validated",
                               merchant_id=context["merchant_id"],
                               key_prefix=key_prefix,
                               total_duration_ms=total_duration * 1000,
                               db_query_duration_ms=db_query_duration * 1000,
                               verify_duration_ms=verify_duration * 1000)
                    
                    # Record metrics
                    try:
                        from shared.monitoring.metrics import record_api_key_validation
                        cache_status = "miss" if not self.redis_client else "miss"
                        record_api_key_validation("cache_miss", total_duration, cache_status=cache_status)
                    except ImportError:
                        pass
                    
                    return context
            
            # No matching key found
            total_duration = time.time() - start_time
            logger.warning("API key validation failed",
                           key_prefix=key_prefix,
                           reason="no candidates matched or bcrypt verify failed",
                           total_duration_ms=total_duration * 1000)
            
            # Record failed validation metric
            try:
                from shared.monitoring.metrics import record_api_key_validation
                cache_status = "unavailable" if not self.redis_client else "miss"
                record_api_key_validation("failed", total_duration, cache_status=cache_status)
            except ImportError:
                pass
            
            return None
            
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error("API key validation error",
                         error=str(e),
                         key_prefix=key_prefix,
                         total_duration_ms=total_duration * 1000)
            return None
    
    async def revoke_api_key(
        self,
        key_id: int,
        revoked_by: Optional[int] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Revoke an API key
        
        Args:
            key_id: ID of the key to revoke
            revoked_by: User ID who revoked the key
            reason: Reason for revocation
            
        Returns:
            True if successful
        """
        try:
            result = await self.db.execute(
                update(APIKey)
                .where(APIKey.id == key_id)
                .values(
                    status="revoked",
                    revoked_at=func.now(),
                    revoked_by=revoked_by,
                    revoked_reason=reason,
                )
                .returning(APIKey.merchant_id, APIKey.key_prefix)
            )
            
            row = result.fetchone()
            await self.db.commit()
            
            if row:
                logger.info("API key revoked",
                           key_id=key_id,
                           merchant_id=row.merchant_id,
                           key_prefix=row.key_prefix,
                           reason=reason)
                return True
            
            return False
            
        except Exception as e:
            logger.error("API key revocation failed", key_id=key_id, error=str(e))
            await self.db.rollback()
            return False
    
    async def list_merchant_keys(
        self,
        merchant_id: int,
        include_revoked: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all API keys for a merchant
        
        Args:
            merchant_id: ID of the merchant
            include_revoked: Include revoked keys in results
            
        Returns:
            List of API key records
        """
        try:
            stmt = select(APIKey).where(APIKey.merchant_id == merchant_id)
            if not include_revoked:
                stmt = stmt.where(APIKey.status != "revoked")
            stmt = stmt.order_by(APIKey.created_at.desc())
            
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            
            keys: List[Dict[str, Any]] = []
            for key in rows:
                keys.append(
                    {
                        "id": key.id,
                        "merchant_id": key.merchant_id,
                        "key_prefix": key.key_prefix,
                        "name": key.name,
                        "description": key.description,
                        "rate_limit_per_minute": key.rate_limit_per_minute,
                        "status": key.status,
                        "scopes": key.scopes,
                        "last_used_at": key.last_used_at,
                        "usage_count": key.usage_count,
                        "created_at": key.created_at,
                        "expires_at": key.expires_at,
                        "revoked_at": key.revoked_at,
                        "revoked_reason": key.revoked_reason,
                    }
                )
            
            return keys
            
        except Exception as e:
            logger.error("Failed to list API keys", merchant_id=merchant_id, error=str(e))
            return []
    
    async def get_key_usage_stats(
        self,
        key_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage statistics for an API key
        
        Args:
            key_id: ID of the API key
            days: Number of days to analyze
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            stmt = (
                select(
                    func.count(APIKeyUsage.id),
                    func.count(func.distinct(func.date(APIKeyUsage.timestamp))),
                    func.avg(APIKeyUsage.response_time_ms),
                    func.count(
                        func.nullif(
                            func.case(
                                (APIKeyUsage.status_code >= 400, 1),
                                else_=0,
                            ),
                            0,
                        )
                    ),
                    func.max(APIKeyUsage.timestamp),
                )
                .where(
                    APIKeyUsage.api_key_id == key_id,
                    APIKeyUsage.timestamp > cutoff,
                )
            )
            
            result = await self.db.execute(stmt)
            row = result.fetchone()
            
            if row:
                return {
                    "total_requests": row[0] or 0,
                    "active_days": row[1] or 0,
                    "avg_response_time_ms": float(row[2]) if row[2] else 0,
                    "error_count": row[3] or 0,
                    "last_request": row[4],
                    "period_days": days,
                }
            
            return {
                "total_requests": 0,
                "active_days": 0,
                "avg_response_time_ms": 0,
                "error_count": 0,
                "last_request": None,
                "period_days": days,
            }
            
        except Exception as e:
            logger.error("Failed to get usage stats", key_id=key_id, error=str(e))
            return {}

