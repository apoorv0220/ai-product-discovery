"""
Merchant Model
Multi-tenant merchant accounts
"""

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database.base import Base


class Merchant(Base):
    """Merchant model for multi-tenant accounts"""
    __tablename__ = 'merchants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    company_name = Column(String(255))
    tier = Column(String(50), nullable=False, default='free', index=True)  # free, basic, pro, enterprise
    status = Column(String(50), nullable=False, default='active', index=True)  # active, inactive, suspended
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_keys = relationship(
        "APIKey", 
        back_populates="merchant", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    api_key_usage = relationship(
        "APIKeyUsage",
        back_populates="merchant",
        lazy="select"
    )

    __table_args__ = (
        Index('idx_merchants_email', 'email'),
        Index('idx_merchants_tier', 'tier'),
        Index('idx_merchants_status', 'status'),
    )

