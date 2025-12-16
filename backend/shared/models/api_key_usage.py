"""
API Key Usage Model
API usage tracking and analytics
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database.base import Base


class APIKeyUsage(Base):
    """API Key Usage model for tracking API calls"""
    __tablename__ = 'api_key_usage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey('api_keys.id', ondelete='CASCADE'), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey('merchants.id', ondelete='CASCADE'), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    ip_address = Column(String(45))  # IPv6 max length
    user_agent = Column(String(500))
    request_id = Column(String(255))  # Unique request ID for tracing
    correlation_id = Column(String(255))  # Correlation ID for distributed tracing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    api_key = relationship(
        "APIKey", 
        back_populates="usage_records",
        lazy="select"
    )
    merchant = relationship(
        "Merchant",
        back_populates="api_key_usage",
        lazy="select"
    )

    __table_args__ = (
        Index('idx_api_key_usage_api_key_id', 'api_key_id'),
        Index('idx_api_key_usage_merchant_id', 'merchant_id'),
        Index('idx_api_key_usage_timestamp', 'timestamp'),
        Index('idx_api_key_usage_endpoint', 'endpoint'),
    )


