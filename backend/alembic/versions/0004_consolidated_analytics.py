"""consolidated_analytics_and_personalization

Revision ID: 0004_consolidated_analytics
Revises: 0003_split_conditions
Create Date: 2025-01-XX

Consolidates analytics, recommendation, and legacy personalization tables 
without user/product foreign keys.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_consolidated_analytics'
down_revision = '0003_split_conditions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Analytics Tables
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analytics_events_event_id', 'analytics_events', ['event_id'], unique=True)
    op.create_index('idx_analytics_events_merchant_id', 'analytics_events', ['merchant_id'])
    op.create_index('idx_analytics_events_timestamp', 'analytics_events', ['timestamp'])
    op.create_index('idx_analytics_events_type', 'analytics_events', ['event_type'])
    op.create_index('idx_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('idx_analytics_events_session_id', 'analytics_events', ['session_id'])
    op.create_index('idx_analytics_events_product_id', 'analytics_events', ['product_id'])

    op.create_table(
        'analytics_aggregations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('aggregation_type', sa.String(length=20), nullable=False),
        sa.Column('time_window_start', sa.DateTime(), nullable=False),
        sa.Column('time_window_end', sa.DateTime(), nullable=False),
        sa.Column('total_events', sa.Integer(), server_default='0', nullable=True),
        sa.Column('unique_users', sa.Integer(), server_default='0', nullable=True),
        sa.Column('unique_sessions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('page_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('product_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('searches', sa.Integer(), server_default='0', nullable=True),
        sa.Column('add_to_carts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=True),
        sa.Column('revenue', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('conversion_rate', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analytics_agg_merchant_window', 'analytics_aggregations', ['merchant_id', 'time_window_start'])

    op.create_table(
        'user_behavior_aggregations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('total_events', sa.Integer(), server_default='0', nullable=True),
        sa.Column('page_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('product_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('searches', sa.Integer(), server_default='0', nullable=True),
        sa.Column('add_to_carts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_revenue', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('session_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('avg_session_duration', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('behavior_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_behavior_merchant_user', 'user_behavior_aggregations', ['merchant_id', 'user_id'])
    op.create_index('idx_user_behavior_merchant_session', 'user_behavior_aggregations', ['merchant_id', 'session_id'])

    op.create_table(
        'session_analytics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('page_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('product_views', sa.Integer(), server_default='0', nullable=True),
        sa.Column('searches', sa.Integer(), server_default='0', nullable=True),
        sa.Column('add_to_carts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=True),
        sa.Column('revenue', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('entry_page', sa.String(length=500), nullable=True),
        sa.Column('exit_page', sa.String(length=500), nullable=True),
        sa.Column('bounce', sa.String(length=10), server_default='true', nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('journey', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_analytics_merchant_session', 'session_analytics', ['merchant_id', 'session_id'], unique=True)

    op.create_table(
        'analytics_events_archive',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analytics_archive_merchant_timestamp', 'analytics_events_archive', ['merchant_id', 'timestamp'])

    # 2. Recommendation Tables
    op.create_table(
        'product_similarities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('similar_product_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('algorithm', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'similar_product_id', 'algorithm', name='uq_product_similarity')
    )
    op.create_index('idx_product_similarities_product_id', 'product_similarities', ['product_id'])
    op.create_index('idx_product_similarities_similar_product_id', 'product_similarities', ['similar_product_id'])

    # 3. Legacy Personalization Tables (Deprecated but kept for reference/compatibility)
    op.create_table(
        'user_search_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('results_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('clicked_products', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'user_product_views',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('product_id', sa.String(length=255), nullable=False),
        sa.Column('product_name', sa.String(length=500), nullable=True),
        sa.Column('product_sku', sa.String(length=255), nullable=True),
        sa.Column('categories', sa.JSON(), nullable=True),
        sa.Column('category_ids', sa.JSON(), nullable=True),
        sa.Column('view_duration', sa.Integer(), server_default='0', nullable=True),
        sa.Column('came_from_search', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('search_query', sa.String(length=500), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'user_search_clicks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('search_query', sa.String(length=500), nullable=False),
        sa.Column('clicked_product_id', sa.String(length=255), nullable=False),
        sa.Column('clicked_product_name', sa.String(length=500), nullable=True),
        sa.Column('position_in_results', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'personalized_search_weights',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('product_id', sa.String(length=255), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('interaction_count', sa.Integer(), server_default='1', nullable=True),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_weights_merchant_user_session_product', 'personalized_search_weights', ['merchant_id', 'user_id', 'session_id', 'product_id'], unique=True)


def downgrade() -> None:
    op.drop_table('personalized_search_weights')
    op.drop_table('user_search_clicks')
    op.drop_table('user_product_views')
    op.drop_table('user_search_history')
    op.drop_table('product_similarities')
    op.drop_table('analytics_events_archive')
    op.drop_table('session_analytics')
    op.drop_table('user_behavior_aggregations')
    op.drop_table('analytics_aggregations')
    op.drop_table('analytics_events')
