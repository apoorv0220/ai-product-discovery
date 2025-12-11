"""
User Interaction Models for Personalized Search
SQLAlchemy models for tracking user behavior and search interactions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class UserSearchHistory(Base):
    """Tracks user search queries for personalization"""
    __tablename__ = 'user_search_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, nullable=False, index=True)  # FK to merchants.id (constraint created manually)
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    query = Column(String(500), nullable=False, index=True)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    clicked_products = Column(JSON, default=list)  # Store clicked product IDs

    # Indexes for performance
    __table_args__ = (
        Index('idx_merchant_user_created_at', 'merchant_id', 'user_id', 'created_at'),
        Index('idx_merchant_session_created_at', 'merchant_id', 'session_id', 'created_at'),
        Index('idx_merchant_query_created_at', 'merchant_id', 'query', 'created_at'),
    )

class UserProductViews(Base):
    """Tracks product page views for personalization"""
    __tablename__ = 'user_product_views'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, nullable=False, index=True)  # FK to merchants.id (constraint created manually)
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    product_id = Column(String(255), nullable=False, index=True)
    product_name = Column(String(500))
    product_sku = Column(String(255))
    categories = Column(JSON, default=list)  # Store as JSON array of names: ["Electronics", "Laptops"]
    category_ids = Column(JSON, default=list)  # Store as JSON array of IDs: ["123", "456"]
    view_duration = Column(Integer, default=0)  # Duration in seconds
    came_from_search = Column(Boolean, default=False)
    search_query = Column(String(500))
    # Platform context for better personalization
    platform = Column(String(50))  # "magento", "woocommerce", "shopify", etc.
    device_type = Column(String(50))  # "mobile", "desktop", "tablet"
    user_agent = Column(String(500))  # Browser/device user agent
    referrer = Column(String(500))  # Referring page URL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_merchant_user_created_at', 'merchant_id', 'user_id', 'created_at'),
        Index('idx_merchant_session_created_at', 'merchant_id', 'session_id', 'created_at'),
        Index('idx_merchant_product_created_at', 'merchant_id', 'product_id', 'created_at'),
    )

class UserSearchClicks(Base):
    """Tracks clicks on search results for personalization"""
    __tablename__ = 'user_search_clicks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, nullable=False, index=True)  # FK to merchants.id (constraint created manually)
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    search_query = Column(String(500), nullable=False, index=True)
    clicked_product_id = Column(String(255), nullable=False, index=True)
    clicked_product_name = Column(String(500))
    position_in_results = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_merchant_user_created_at', 'merchant_id', 'user_id', 'created_at'),
        Index('idx_merchant_session_created_at', 'merchant_id', 'session_id', 'created_at'),
        Index('idx_merchant_query_created_at', 'merchant_id', 'search_query', 'created_at'),
    )

class PersonalizedSearchWeights(Base):
    """Stores personalized search weights for users/products"""
    __tablename__ = 'personalized_search_weights'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, nullable=False, index=True)  # FK to merchants.id (constraint created manually)
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    product_id = Column(String(255), nullable=False, index=True)
    weight = Column(Float, default=1.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    interaction_count = Column(Integer, default=1)

    # Unique constraint to ensure one weight per merchant + user/session + product
    __table_args__ = (
        Index('idx_merchant_user_session_product_weight', 'merchant_id', 'user_id', 'session_id', 'product_id', unique=True),
        Index('idx_merchant_weight_updated_at', 'merchant_id', 'weight', 'updated_at'),
    )

# Create __init__.py to make it a package
__all__ = [
    'Base',
    'UserSearchHistory',
    'UserProductViews',
    'UserSearchClicks',
    'PersonalizedSearchWeights'
]
