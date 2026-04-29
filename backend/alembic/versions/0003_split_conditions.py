"""split_conditions

Revision ID: 0003_split_conditions
Revises: 0002_add_merchandising_rules
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_split_conditions'
down_revision = '0002_add_merchandising_rules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Split conditions into trigger_conditions and target_conditions"""

    # Add new columns
    op.add_column('merchandising_rules', sa.Column('trigger_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('merchandising_rules', sa.Column('target_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Make existing conditions column nullable for backwards compatibility
    op.alter_column('merchandising_rules', 'conditions', nullable=True)

    # Create indexes for new columns
    op.create_index('idx_merchandising_rules_trigger_conditions', 'merchandising_rules', ['trigger_conditions'], postgresql_using='gin')
    op.create_index('idx_merchandising_rules_target_conditions', 'merchandising_rules', ['target_conditions'], postgresql_using='gin')


def downgrade() -> None:
    """Revert split conditions"""

    # Drop indexes
    op.drop_index('idx_merchandising_rules_target_conditions', table_name='merchandising_rules')
    op.drop_index('idx_merchandising_rules_trigger_conditions', table_name='merchandising_rules')

    # Make conditions column NOT NULL again
    op.alter_column('merchandising_rules', 'conditions', nullable=False)

    # Drop new columns
    op.drop_column('merchandising_rules', 'target_conditions')
    op.drop_column('merchandising_rules', 'trigger_conditions')
