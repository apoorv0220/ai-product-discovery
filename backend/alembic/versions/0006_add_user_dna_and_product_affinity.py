"""add user dna and product affinity

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006_user_dna_affinity'
down_revision = '0005_add_experiments_and_funnels'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Update user_behavior_aggregations with new columns
    op.add_column('user_behavior_aggregations', sa.Column('category_affinity', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('user_behavior_aggregations', sa.Column('brand_affinity', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('user_behavior_aggregations', sa.Column('behavioral_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2. Create product_affinities table
    op.create_table('product_affinities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('product_a_id', sa.Integer(), nullable=False),
        sa.Column('product_b_id', sa.Integer(), nullable=False),
        sa.Column('view_co_occurrence', sa.Integer(), nullable=True),
        sa.Column('purchase_co_occurrence', sa.Integer(), nullable=True),
        sa.Column('affinity_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merchant_id', 'product_a_id', 'product_b_id', name='uq_product_affinity')
    )
    op.create_index('idx_product_affinity_merchant_a', 'product_affinities', ['merchant_id', 'product_a_id'], unique=False)
    op.create_index('idx_product_affinity_merchant_b', 'product_affinities', ['merchant_id', 'product_b_id'], unique=False)
    op.create_index(op.f('idx_product_affinities_merchant_id'), 'product_affinities', ['merchant_id'], unique=False)
    op.create_index(op.f('idx_product_affinities_product_a_id'), 'product_affinities', ['product_a_id'], unique=False)
    op.create_index(op.f('idx_product_affinities_product_b_id'), 'product_affinities', ['product_b_id'], unique=False)


def downgrade():
    op.drop_index(op.f('idx_product_affinities_product_b_id'), table_name='product_affinities')
    op.drop_index(op.f('idx_product_affinities_product_a_id'), table_name='product_affinities')
    op.drop_index(op.f('idx_product_affinities_merchant_id'), table_name='product_affinities')
    op.drop_index('idx_product_affinity_merchant_b', table_name='product_affinities')
    op.drop_index('idx_product_affinity_merchant_a', table_name='product_affinities')
    op.drop_table('product_affinities')
    
    op.drop_column('user_behavior_aggregations', 'behavioral_tags')
    op.drop_column('user_behavior_aggregations', 'brand_affinity')
    op.drop_column('user_behavior_aggregations', 'category_affinity')
