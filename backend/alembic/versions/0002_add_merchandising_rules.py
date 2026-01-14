"""add_merchandising_rules

Revision ID: 0002_add_merchandising_rules
Revises: 0001_baseline
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_merchandising_rules'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create merchandising_rules table"""
    op.create_table(
        'merchandising_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_merchandising_rules_merchant_active', 'merchandising_rules', ['merchant_id', 'is_active'])
    op.create_index('idx_merchandising_rules_priority', 'merchandising_rules', ['priority'])
    op.create_index('idx_merchandising_rules_type', 'merchandising_rules', ['rule_type'])
    op.create_index(op.f('ix_merchandising_rules_merchant_id'), 'merchandising_rules', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_merchandising_rules_is_active'), 'merchandising_rules', ['is_active'], unique=False)


def downgrade() -> None:
    """Drop merchandising_rules table"""
    op.drop_index(op.f('ix_merchandising_rules_is_active'), table_name='merchandising_rules')
    op.drop_index(op.f('ix_merchandising_rules_merchant_id'), table_name='merchandising_rules')
    op.drop_index('idx_merchandising_rules_type', table_name='merchandising_rules')
    op.drop_index('idx_merchandising_rules_priority', table_name='merchandising_rules')
    op.drop_index('idx_merchandising_rules_merchant_active', table_name='merchandising_rules')
    op.drop_table('merchandising_rules')


