"""
Product Similarity Model
Product similarity scores for recommendations
"""

from sqlalchemy import Column, Integer, Numeric, String, DateTime, Index, UniqueConstraint
from datetime import datetime
from shared.database.base import Base


class ProductSimilarity(Base):
    """Product Similarity model for recommendations"""
    __tablename__ = 'product_similarities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer, 
        nullable=False, 
        index=True
    ) # No longer a ForeignKey
    similar_product_id = Column(
        Integer, 
        nullable=False, 
        index=True
    ) # No longer a ForeignKey
    similarity_score = Column(Numeric(5, 4), nullable=False)  # Score between 0 and 1
    algorithm = Column(String(50), nullable=False)  # Algorithm used: 'content_based', 'collaborative', etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('product_id', 'similar_product_id', 'algorithm', name='uq_product_similarity'),
        Index('idx_product_similarities_product_id', 'product_id'),
        Index('idx_product_similarities_similar_product_id', 'similar_product_id'),
        Index('idx_product_similarities_score', 'similarity_score'),
    )


class ProductAffinity(Base):
    """Product Affinity model for co-occurrence tracking"""
    __tablename__ = 'product_affinities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, index=True, nullable=False)
    product_a_id = Column(Integer, nullable=False, index=True)
    product_b_id = Column(Integer, nullable=False, index=True)
    
    # Co-occurrence metrics
    view_co_occurrence = Column(Integer, default=0)
    purchase_co_occurrence = Column(Integer, default=0)
    
    # Statistical scores
    affinity_score = Column(Numeric(5, 4), default=0.0) # Normalized 0-1
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('merchant_id', 'product_a_id', 'product_b_id', name='uq_product_affinity'),
        Index('idx_product_affinity_merchant_a', 'merchant_id', 'product_a_id'),
        Index('idx_product_affinity_merchant_b', 'merchant_id', 'product_b_id'),
    )
