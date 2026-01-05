"""Remove product foreign key constraint from analytics_events.

Since products are not stored in PostgreSQL and the products table is empty,
the foreign key constraint on analytics_events.product_id causes unnecessary
validation failures. This migration removes the constraint while keeping
the product_id column for reference purposes.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_remove_product_foreign_key'
down_revision = '0004_add_analytics_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove product foreign key constraint from analytics_events table."""
    # Drop the foreign key constraint on product_id
    op.drop_constraint('fk_analytics_events_product_id_products', 'analytics_events', type_='foreignkey')

    # Note: We keep the product_id column and its index, just remove the FK constraint
    # This allows analytics events to reference products by ID without database validation


def downgrade() -> None:
    """Restore product foreign key constraint to analytics_events table."""
    # Recreate the foreign key constraint
    op.create_foreign_key(
        'fk_analytics_events_product_id_products',
        'analytics_events', 'products',
        ['product_id'], ['id'],
        ondelete='SET NULL'
    )
