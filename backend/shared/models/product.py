"""
Product Model
Product catalog
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Text, Index, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from shared.database.base import Base


class Product(Base):
    """Product model for catalog"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    magento_product_id = Column(Integer, unique=True, nullable=False, index=True)
    store_id = Column(Integer)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    short_description = Column(Text)
    price = Column(Numeric(10, 2))
    special_price = Column(Numeric(10, 2))
    status = Column(Integer, default=1, index=True)  # 1 = enabled, 0 = disabled
    visibility = Column(Integer, default=4, index=True)  # 1-4 visibility levels
    category_ids = Column(ARRAY(Integer))  # Array of category IDs
    qty = Column(Numeric(10, 2))  # Quantity in stock
    is_in_stock = Column(Boolean, default=True)
    image_url = Column(String(500))
    view_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)
    avg_rating = Column(Numeric(3, 2))
    review_count = Column(Integer, default=0)
    attributes = Column(JSONB)  # JSONB for flexible attributes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_synced_at = Column(DateTime)

    __table_args__ = (
        Index('idx_products_magento_id', 'magento_product_id'),
        Index('idx_products_sku', 'sku'),
        Index('idx_products_status', 'status'),
        Index('idx_products_visibility', 'visibility'),
        # GIN indexes for array and JSONB columns (created via migration)
    )














