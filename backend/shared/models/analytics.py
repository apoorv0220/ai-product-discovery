"""
Analytics Event Model
Event tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from shared.database.base import Base


class AnalyticsEvent(Base):
    """Analytics Event model for tracking events"""
    __tablename__ = 'analytics_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(
        Integer, 
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    session_id = Column(String(36), index=True)  # Session identifier
    product_id = Column(
        Integer, 
        ForeignKey('products.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    event_metadata = Column(JSONB, name='metadata')  # Additional event metadata (stored as 'metadata' in DB)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", lazy="select")
    product = relationship("Product", lazy="select")

    __table_args__ = (
        Index('idx_analytics_events_event_id', 'event_id'),
        Index('idx_analytics_events_timestamp', 'timestamp'),
        Index('idx_analytics_events_type', 'event_type'),
        Index('idx_analytics_events_user_id', 'user_id'),
        Index('idx_analytics_events_session_id', 'session_id'),
        Index('idx_analytics_events_product_id', 'product_id'),
    )

