"""
Merchandising Rule Model
Merchant-controlled search result manipulation rules
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from shared.database.base import Base


class MerchandisingRule(Base):
    """Merchandising rule model for controlling search results"""
    __tablename__ = 'merchandising_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Rule configuration
    rule_type = Column(String(50), nullable=False)  # 'boost', 'pin', 'hide'
    priority = Column(Integer, default=500, nullable=False)  # 1-1000, higher = more important
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Trigger conditions - when should this rule activate? (JSONB)
    # Examples:
    # {"type": "query_match", "operator": "contains", "value": "laptop"}
    # {"type": "category", "operator": "equals", "value": "Electronics"} (legacy support)
    trigger_conditions = Column(JSONB, nullable=True)

    # Target conditions - which products should be affected? (JSONB)
    # Only used for boost rules. For pin/hide, products are specified in action_config
    # Examples:
    # {"type": "category", "operator": "equals", "value": "Electronics"}
    # {"type": "product_id", "operator": "in", "value": ["123", "456"]}
    target_conditions = Column(JSONB, nullable=True)

    # Legacy conditions field for backwards compatibility during migration
    # Will be removed after migration
    conditions = Column(JSONB, nullable=True)
    
    # Action configuration (JSONB)
    # For boost: {"boost_factor": 2.5}  # 0.1-10.0
    # For pin: {"position": 1, "product_id": "123"}  # 1-based position
    # For hide: {}  # No config needed
    action_config = Column(JSONB, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    merchant = relationship("Merchant", lazy="select")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_merchandising_rules_merchant_active', 'merchant_id', 'is_active'),
        Index('idx_merchandising_rules_priority', 'priority'),
        Index('idx_merchandising_rules_type', 'rule_type'),
    )


