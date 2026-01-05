"""Fix UserBehaviorAggregation schema for plugin compatibility.

Change user_id column from INTEGER FK to VARCHAR(255) to support plugin architecture
without requiring users table.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_fix_user_behavior_schema'
down_revision = '0006_drop_empty_legacy_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change UserBehaviorAggregation.user_id from INTEGER FK to VARCHAR(255)."""
    # Drop the foreign key constraint and index on user_id
    op.drop_constraint('fk_user_behavior_aggregations_user_id_users', 'user_behavior_aggregations', type_='foreignkey')

    # Change the column type from INTEGER to VARCHAR(255)
    op.alter_column('user_behavior_aggregations',
                    'user_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.String(length=255),
                    existing_nullable=True,
                    postgresql_using='user_id::varchar')  # Handle conversion from int to string


def downgrade() -> None:
    """Revert UserBehaviorAggregation.user_id back to INTEGER FK."""
    # Change the column type back from VARCHAR(255) to INTEGER
    op.alter_column('user_behavior_aggregations',
                    'user_id',
                    existing_type=sa.String(length=255),
                    type_=sa.INTEGER(),
                    existing_nullable=True,
                    postgresql_using='user_id::integer')  # Handle conversion from string to int

    # Recreate the foreign key constraint
    op.create_foreign_key('fk_user_behavior_aggregations_user_id_users',
                          'user_behavior_aggregations', 'users',
                          ['user_id'], ['id'],
                          ondelete='CASCADE')
