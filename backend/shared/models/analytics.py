"""
Analytics Event Model
Event tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, Index, ForeignKey, Float
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
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Support both string and int user IDs
    session_id = Column(String(36), nullable=True, index=True)  # Made optional
    product_id = Column(Integer, nullable=True, index=True) # No longer a ForeignKey
    
    # Additional context fields
    platform = Column(String(50))  # e.g., "magento", "woocommerce"
    device_type = Column(String(50))  # "mobile", "desktop", "tablet"
    ip_address = Column(String(45))  # IPv4/IPv6 address
    user_agent = Column(String(500))  # Browser user agent
    referrer = Column(String(500))  # Referring page URL
    revenue = Column(Float)  # For purchase events
    properties = Column(JSONB, name='properties')  # Additional event properties
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    merchant = relationship("Merchant", lazy="select")

    __table_args__ = (
        Index('idx_analytics_events_event_id', 'event_id'),
        Index('idx_analytics_events_merchant_id', 'merchant_id'),
        Index('idx_analytics_events_timestamp', 'timestamp'),
        Index('idx_analytics_events_type', 'event_type'),
        Index('idx_analytics_events_user_id', 'user_id'),
        Index('idx_analytics_events_session_id', 'session_id'),
        Index('idx_analytics_events_product_id', 'product_id'),
        Index('idx_analytics_events_merchant_timestamp', 'merchant_id', 'timestamp'),
        Index('idx_analytics_events_merchant_type_timestamp', 'merchant_id', 'event_type', 'timestamp'),
        Index('idx_analytics_events_merchant_user_timestamp', 'merchant_id', 'user_id', 'timestamp'),
        Index('idx_analytics_events_merchant_session_timestamp', 'merchant_id', 'session_id', 'timestamp'),
    )


class AnalyticsAggregation(Base):
    """Time-windowed metrics aggregation"""
    __tablename__ = 'analytics_aggregations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    aggregation_type = Column(String(20), nullable=False)  # 'hourly', 'daily', 'weekly'
    time_window_start = Column(DateTime, nullable=False, index=True)
    time_window_end = Column(DateTime, nullable=False)
    
    # Metrics
    total_events = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    unique_sessions = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    searches = Column(Integer, default=0)
    add_to_carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    
    # Additional metrics stored as JSONB
    metrics = Column(JSONB)  # Flexible metrics storage
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    merchant = relationship("Merchant", lazy="select")

    __table_args__ = (
        Index('idx_analytics_agg_merchant_type_window', 'merchant_id', 'aggregation_type', 'time_window_start'),
        Index('idx_analytics_agg_merchant_window', 'merchant_id', 'time_window_start'),
        Index('idx_analytics_agg_type_window', 'aggregation_type', 'time_window_start'),
    )


class UserBehaviorAggregation(Base):
    """User-level behavior summaries"""
    __tablename__ = 'user_behavior_aggregations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = Column(String(255), nullable=True, index=True)  # String user IDs for plugin compatibility
    session_id = Column(String(255), nullable=False, index=True)  # For anonymous users
    
    # Behavior metrics
    total_events = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    searches = Column(Integer, default=0)
    add_to_carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    
    # Session metrics
    session_count = Column(Integer, default=0)
    avg_session_duration = Column(Float, default=0.0)  # in seconds
    last_activity = Column(DateTime, nullable=False, index=True)
    
    # Behavioral patterns stored as JSONB
    behavior_patterns = Column(JSONB)  # e.g., preferred categories, search patterns
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    merchant = relationship("Merchant", lazy="select")

    __table_args__ = (
        Index('idx_user_behavior_merchant_user', 'merchant_id', 'user_id'),
        Index('idx_user_behavior_merchant_session', 'merchant_id', 'session_id'),
        Index('idx_user_behavior_last_activity', 'merchant_id', 'last_activity'),
    )


class SessionAnalytics(Base):
    """Session-level analytics"""
    __tablename__ = 'session_analytics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True) # Changed from Integer FK to String
    
    # Session metrics
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, default=0.0)  # in seconds
    
    page_views = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    searches = Column(Integer, default=0)
    add_to_carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    # Session characteristics
    entry_page = Column(String(500))
    exit_page = Column(String(500))
    bounce = Column(String(10), default='true')  # 'true', 'false'
    device_type = Column(String(50))
    platform = Column(String(50))
    
    # Session journey stored as JSONB
    journey = Column(JSONB)  # List of page views and events in sequence
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    merchant = relationship("Merchant", lazy="select")

    __table_args__ = (
        Index('idx_session_analytics_merchant_session', 'merchant_id', 'session_id', unique=True),
        Index('idx_session_analytics_merchant_start', 'merchant_id', 'start_time'),
        Index('idx_session_analytics_merchant_user_start', 'merchant_id', 'user_id', 'start_time'),
    )


class AnalyticsEventArchive(Base):
    """Archived analytics events (for events >90 days old)"""
    __tablename__ = 'analytics_events_archive'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    merchant_id = Column(
        Integer,
        ForeignKey('merchants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True) # Changed from Integer FK to String
    session_id = Column(String(36), index=True)
    product_id = Column(Integer, nullable=True, index=True) # No longer a ForeignKey
    platform = Column(String(50))
    device_type = Column(String(50))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    referrer = Column(String(500))
    revenue = Column(Float)
    properties = Column(JSONB)
    timestamp = Column(DateTime, nullable=False, index=True)
    archived_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    merchant = relationship("Merchant", lazy="select")

    __table_args__ = (
        Index('idx_analytics_archive_merchant_timestamp', 'merchant_id', 'timestamp'),
        Index('idx_analytics_archive_event_id', 'event_id'),
    )
