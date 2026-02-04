"""add_experiments_and_funnels

Revision ID: 0005_add_experiments_and_funnels
Revises: 0004_consolidated_analytics
Create Date: 2026-01-14

Adds tables for A/B testing experiments and customizable conversion funnels.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005_add_experiments_and_funnels'
down_revision = '0004_consolidated_analytics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Experiments Table
    op.create_table(
        'experiments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('traffic_allocation', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_experiments_merchant_status', 'experiments', ['merchant_id', 'status'])

    # 2. Experiment Variants Table
    op.create_table(
        'experiment_variants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), server_default='0.5', nullable=True),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_control', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Conversion Funnels Table
    op.create_table(
        'conversion_funnels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_funnels_merchant_active', 'conversion_funnels', ['merchant_id', 'is_active'])

    # 4. Funnel Steps Table
    op.create_table(
        'funnel_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('funnel_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('properties_filter', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['funnel_id'], ['conversion_funnels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_funnel_steps_funnel_order', 'funnel_steps', ['funnel_id', 'step_order'])

    # 5. Update Analytics Events Table
    op.add_column('analytics_events', sa.Column('experiment_id', sa.Integer(), nullable=True))
    op.add_column('analytics_events', sa.Column('variant_id', sa.Integer(), nullable=True))
    op.create_index('idx_analytics_events_experiment_id', 'analytics_events', ['experiment_id'])
    op.create_index('idx_analytics_events_variant_id', 'analytics_events', ['variant_id'])


def downgrade() -> None:
    op.drop_index('idx_analytics_events_variant_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_experiment_id', table_name='analytics_events')
    op.drop_column('analytics_events', 'variant_id')
    op.drop_column('analytics_events', 'experiment_id')
    op.drop_table('funnel_steps')
    op.drop_table('conversion_funnels')
    op.drop_table('experiment_variants')
    op.drop_table('experiments')
