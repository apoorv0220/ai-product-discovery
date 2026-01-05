"""add_analytics_schema

Revision ID: 0004_add_analytics_schema
Revises: 0003_split_conditions
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_add_analytics_schema'
down_revision = '0003_split_conditions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add analytics schema with hybrid user/session tracking"""
    
    # Create analytics_events table
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),  # Hybrid: supports string user IDs
        sa.Column('user_id_int', sa.Integer(), nullable=True),  # Resolved integer for FK relationships
        sa.Column('session_id', sa.String(36), nullable=True),  # Optional session tracking
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id_int'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for analytics_events
    op.create_index('idx_analytics_events_event_id', 'analytics_events', ['event_id'], unique=True)
    op.create_index('idx_analytics_events_merchant_id', 'analytics_events', ['merchant_id'])
    op.create_index('idx_analytics_events_timestamp', 'analytics_events', ['timestamp'])
    op.create_index('idx_analytics_events_type', 'analytics_events', ['event_type'])
    op.create_index('idx_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('idx_analytics_events_user_id_int', 'analytics_events', ['user_id_int'])
    op.create_index('idx_analytics_events_session_id', 'analytics_events', ['session_id'])
    op.create_index('idx_analytics_events_product_id', 'analytics_events', ['product_id'])
    op.create_index('idx_analytics_events_merchant_timestamp', 'analytics_events', ['merchant_id', 'timestamp'])
    op.create_index('idx_analytics_events_merchant_type_timestamp', 'analytics_events', ['merchant_id', 'event_type', 'timestamp'])
    op.create_index('idx_analytics_events_merchant_user_timestamp', 'analytics_events', ['merchant_id', 'user_id', 'timestamp'])
    op.create_index('idx_analytics_events_merchant_session_timestamp', 'analytics_events', ['merchant_id', 'session_id', 'timestamp'])
    
    # Create analytics_aggregations table
    op.create_table(
        'analytics_aggregations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('aggregation_type', sa.String(20), nullable=False),
        sa.Column('time_window_start', sa.DateTime(), nullable=False),
        sa.Column('time_window_end', sa.DateTime(), nullable=False),
        sa.Column('total_events', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unique_users', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unique_sessions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('page_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('product_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('searches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('add_to_carts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('purchases', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('revenue', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('conversion_rate', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analytics_agg_merchant_type_window', 'analytics_aggregations', ['merchant_id', 'aggregation_type', 'time_window_start'])
    op.create_index('idx_analytics_agg_merchant_window', 'analytics_aggregations', ['merchant_id', 'time_window_start'])
    op.create_index('idx_analytics_agg_type_window', 'analytics_aggregations', ['aggregation_type', 'time_window_start'])
    
    # Create user_behavior_aggregations table
    op.create_table(
        'user_behavior_aggregations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('total_events', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('page_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('product_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('searches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('add_to_carts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('purchases', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_revenue', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('session_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_session_duration', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('behavior_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_behavior_merchant_user', 'user_behavior_aggregations', ['merchant_id', 'user_id'])
    op.create_index('idx_user_behavior_merchant_session', 'user_behavior_aggregations', ['merchant_id', 'session_id'])
    op.create_index('idx_user_behavior_last_activity', 'user_behavior_aggregations', ['merchant_id', 'last_activity'])
    
    # Create session_analytics table
    op.create_table(
        'session_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('page_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('product_views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('searches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('add_to_carts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('purchases', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('revenue', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('entry_page', sa.String(500), nullable=True),
        sa.Column('exit_page', sa.String(500), nullable=True),
        sa.Column('bounce', sa.String(10), nullable=True, server_default='true'),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('journey', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_analytics_merchant_session', 'session_analytics', ['merchant_id', 'session_id'], unique=True)
    op.create_index('idx_session_analytics_merchant_start', 'session_analytics', ['merchant_id', 'start_time'])
    op.create_index('idx_session_analytics_merchant_user_start', 'session_analytics', ['merchant_id', 'user_id', 'start_time'])
    
    # Create analytics_events_archive table
    op.create_table(
        'analytics_events_archive',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analytics_archive_merchant_timestamp', 'analytics_events_archive', ['merchant_id', 'timestamp'])
    op.create_index('idx_analytics_archive_event_id', 'analytics_events_archive', ['event_id'])


def downgrade() -> None:
    """Revert analytics schema"""
    
    # Drop archive table
    op.drop_index('idx_analytics_archive_event_id', table_name='analytics_events_archive')
    op.drop_index('idx_analytics_archive_merchant_timestamp', table_name='analytics_events_archive')
    op.drop_table('analytics_events_archive')
    
    # Drop session_analytics table
    op.drop_index('idx_session_analytics_merchant_user_start', table_name='session_analytics')
    op.drop_index('idx_session_analytics_merchant_start', table_name='session_analytics')
    op.drop_index('idx_session_analytics_merchant_session', table_name='session_analytics')
    op.drop_table('session_analytics')
    
    # Drop user_behavior_aggregations table
    op.drop_index('idx_user_behavior_last_activity', table_name='user_behavior_aggregations')
    op.drop_index('idx_user_behavior_merchant_session', table_name='user_behavior_aggregations')
    op.drop_index('idx_user_behavior_merchant_user', table_name='user_behavior_aggregations')
    op.drop_table('user_behavior_aggregations')
    
    # Drop analytics_aggregations table
    op.drop_index('idx_analytics_agg_type_window', table_name='analytics_aggregations')
    op.drop_index('idx_analytics_agg_merchant_window', table_name='analytics_aggregations')
    op.drop_index('idx_analytics_agg_merchant_type_window', table_name='analytics_aggregations')
    op.drop_table('analytics_aggregations')
    
    # Drop analytics_events table indexes
    op.drop_index('idx_analytics_events_merchant_session_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_merchant_user_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_merchant_type_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_merchant_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_product_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_session_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_user_id_int', table_name='analytics_events')
    op.drop_index('idx_analytics_events_user_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_type', table_name='analytics_events')
    op.drop_index('idx_analytics_events_timestamp', table_name='analytics_events')
    op.drop_index('idx_analytics_events_merchant_id', table_name='analytics_events')
    op.drop_index('idx_analytics_events_event_id', table_name='analytics_events')
    
    # Drop analytics_events table
    op.drop_table('analytics_events')

