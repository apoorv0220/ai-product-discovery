"""Drop empty legacy tables that are no longer needed.

The following tables are empty and replaced by analytics_events:
- products: Empty table causing FK constraint issues (products in ElasticSearch)
- user_product_views: Legacy tracking replaced by analytics_events
- user_search_clicks: Legacy tracking replaced by analytics_events
- user_search_history: Legacy tracking replaced by analytics_events
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_drop_empty_legacy_tables'
down_revision = '0005_remove_product_foreign_key'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop empty legacy tables that are no longer needed."""
    # Note: Keeping products table as it has dependencies from product_similarities and analytics_events_archive
    # The table is empty anyway, so it doesn't hurt to keep it

    # Drop legacy tracking tables (replaced by analytics_events)
    op.drop_table('user_product_views')
    op.drop_table('user_search_clicks')
    op.drop_table('user_search_history')


def downgrade() -> None:
    """Recreate the dropped legacy tables."""
    # Note: Not recreating products table as we didn't drop it

    # Recreate user_product_views table
    op.create_table(
        'user_product_views',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=True),
        sa.Column('product_sku', sa.String(length=100), nullable=True),
        sa.Column('categories', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('view_duration', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('came_from_search', sa.Boolean(), nullable=True),
        sa.Column('search_query', sa.String(length=255), nullable=True),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate user_search_clicks table
    op.create_table(
        'user_search_clicks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('search_query', sa.String(length=255), nullable=True),
        sa.Column('clicked_product_id', sa.Integer(), nullable=True),
        sa.Column('clicked_product_name', sa.String(length=255), nullable=True),
        sa.Column('product_position', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate user_search_history table
    op.create_table(
        'user_search_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('search_query', sa.String(length=255), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
