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
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

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
    
    def __init__(self, db: AsyncSession):
        """
        Initialize API Key Manager
        
        Args:
            db: Async database session
        """
        self.db = db
    
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
            from sqlalchemy import text
            result = await self.db.execute(
                text("SELECT tier FROM merchants WHERE id = :merchant_id"),
                {"merchant_id": merchant_id}
            )
            row = result.fetchone()
            if row:
                tier = row[0]
            else:
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
        
        # Insert into database
        from sqlalchemy import text
        insert_query = text("""
            INSERT INTO api_keys (
                merchant_id, key_hash, key_prefix, name, description,
                rate_limit_per_minute, status, scopes, expires_at, created_by
            ) VALUES (
                :merchant_id, :key_hash, :key_prefix, :name, :description,
                :rate_limit, 'active', :scopes, :expires_at, :created_by
            )
            RETURNING id, merchant_id, key_prefix, name, rate_limit_per_minute, 
                      status, scopes, created_at, expires_at
        """)
        
        result = await self.db.execute(insert_query, {
            "merchant_id": merchant_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": name,
            "description": description,
            "rate_limit": rate_limit,
            "scopes": json.dumps(scopes),  # Store as JSON text
            "expires_at": expires_at,
            "created_by": created_by
        })
        
        row = result.fetchone()
        await self.db.commit()
        
        # Prepare response
        key_record = {
            "id": row[0],
            "merchant_id": row[1],
            "key_prefix": row[2],
            "name": row[3],
            "rate_limit_per_minute": row[4],
            "status": row[5],
            "scopes": row[6],
            "created_at": row[7],
            "expires_at": row[8]
        }
        
        logger.info("API key created",
                   merchant_id=merchant_id,
                   key_prefix=key_prefix,
                   name=name,
                   tier=tier)
        
        return api_key, key_record
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return merchant context
        
        Args:
            api_key: Plain text API key to validate
            
        Returns:
            Dictionary with merchant context if valid, None otherwise
        """
        try:
            key_prefix = self.extract_prefix(api_key)
            
            # Find potential matching keys by prefix
            from sqlalchemy import text
            query = text("""
                SELECT ak.id, ak.merchant_id, ak.key_hash, ak.name,
                       ak.rate_limit_per_minute, ak.status, ak.scopes,
                       ak.expires_at, m.name as merchant_name, m.tier, m.status as merchant_status
                FROM api_keys ak
                JOIN merchants m ON ak.merchant_id = m.id
                WHERE ak.key_prefix = :key_prefix
                  AND ak.status = 'active'
                  AND m.status = 'active'
                  AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)
            """)
            
            result = await self.db.execute(query, {"key_prefix": key_prefix})
            rows = result.fetchall()
            
            # Try to verify against each potential match
            for row in rows:
                if self.verify_key(api_key, row[2]):  # row[2] is key_hash
                    # Update last used timestamp
                    update_query = text("""
                        UPDATE api_keys 
                        SET last_used_at = CURRENT_TIMESTAMP,
                            usage_count = usage_count + 1
                        WHERE id = :key_id
                    """)
                    await self.db.execute(update_query, {"key_id": row[0]})
                    await self.db.commit()
                    
                    # Return merchant context
                    context = {
                        "api_key_id": row[0],
                        "merchant_id": row[1],
                        "merchant_name": row[8],
                        "merchant_tier": row[9],
                        "merchant_status": row[10],
                        "key_name": row[3],
                        "rate_limit_per_minute": row[4],
                        "scopes": row[6]
                    }
                    
                    logger.info("API key validated",
                               merchant_id=context["merchant_id"],
                               key_prefix=key_prefix)
                    
                    return context
            
            # No matching key found
            logger.warning("API key validation failed", key_prefix=key_prefix)
            return None
            
        except Exception as e:
            logger.error("API key validation error", error=str(e))
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
            from sqlalchemy import text
            query = text("""
                UPDATE api_keys
                SET status = 'revoked',
                    revoked_at = CURRENT_TIMESTAMP,
                    revoked_by = :revoked_by,
                    revoked_reason = :reason
                WHERE id = :key_id
                RETURNING merchant_id, key_prefix
            """)
            
            result = await self.db.execute(query, {
                "key_id": key_id,
                "revoked_by": revoked_by,
                "reason": reason
            })
            
            row = result.fetchone()
            await self.db.commit()
            
            if row:
                logger.info("API key revoked",
                           key_id=key_id,
                           merchant_id=row[0],
                           key_prefix=row[1],
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
            from sqlalchemy import text
            
            status_filter = "" if include_revoked else "AND status != 'revoked'"
            
            query = text(f"""
                SELECT id, key_prefix, name, description, rate_limit_per_minute,
                       status, scopes, last_used_at, usage_count, created_at,
                       expires_at, revoked_at, revoked_reason
                FROM api_keys
                WHERE merchant_id = :merchant_id
                {status_filter}
                ORDER BY created_at DESC
            """)
            
            result = await self.db.execute(query, {"merchant_id": merchant_id})
            rows = result.fetchall()
            
            keys = []
            for row in rows:
                keys.append({
                    "id": row[0],
                    "key_prefix": row[1],
                    "name": row[2],
                    "description": row[3],
                    "rate_limit_per_minute": row[4],
                    "status": row[5],
                    "scopes": row[6],
                    "last_used_at": row[7],
                    "usage_count": row[8],
                    "created_at": row[9],
                    "expires_at": row[10],
                    "revoked_at": row[11],
                    "revoked_reason": row[12]
                })
            
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
            from sqlalchemy import text
            
            query = text("""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                    MAX(timestamp) as last_request
                FROM api_key_usage
                WHERE api_key_id = :key_id
                  AND timestamp > CURRENT_TIMESTAMP - INTERVAL ':days days'
            """)
            
            result = await self.db.execute(query, {"key_id": key_id, "days": days})
            row = result.fetchone()
            
            if row:
                return {
                    "total_requests": row[0] or 0,
                    "active_days": row[1] or 0,
                    "avg_response_time_ms": float(row[2]) if row[2] else 0,
                    "error_count": row[3] or 0,
                    "last_request": row[4],
                    "period_days": days
                }
            
            return {
                "total_requests": 0,
                "active_days": 0,
                "avg_response_time_ms": 0,
                "error_count": 0,
                "last_request": None,
                "period_days": days
            }
            
        except Exception as e:
            logger.error("Failed to get usage stats", key_id=key_id, error=str(e))
            return {}

