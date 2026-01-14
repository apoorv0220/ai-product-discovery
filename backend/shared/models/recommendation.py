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
