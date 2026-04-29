"""
API Key Model
API key authentication and management
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database.base import Base


class APIKey(Base):
    """API Key model for authentication"""
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)  # Bcrypt hash of the API key
    key_prefix = Column(String(8), nullable=False, index=True)  # First 8 chars for identification
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rate_limit_per_minute = Column(Integer, nullable=False, default=100)
    status = Column(String(50), nullable=False, default='active', index=True)  # active, revoked
    scopes = Column(Text)  # JSON string of scopes: ["read", "write"]
    expires_at = Column(DateTime, index=True)  # Optional expiration
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer)  # User ID who created the key
    revoked_at = Column(DateTime)
    revoked_by = Column(Integer)  # User ID who revoked the key
    revoked_reason = Column(Text)

    # Relationships
    merchant = relationship(
        "Merchant", 
        back_populates="api_keys",
        lazy="select"
    )
    usage_records = relationship(
        "APIKeyUsage", 
        back_populates="api_key", 
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index('idx_api_keys_merchant_id', 'merchant_id'),
        Index('idx_api_keys_key_prefix', 'key_prefix'),
        Index('idx_api_keys_status', 'status'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )


