"""Baseline schema migration using SQLAlchemy metadata.

This migration creates all tables registered on shared.database Base.metadata.
"""

from alembic import op
import sqlalchemy as sa

from shared.models import Base  # type: ignore

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables defined on Base.metadata."""
    bind = op.get_bind()
    # Use checkfirst=True to skip creation if objects already exist
    # Note: checkfirst works for tables but indexes may still cause issues
    # If you get duplicate index errors, ensure database is properly cleaned via Docker
    try:
        Base.metadata.create_all(bind=bind, checkfirst=True)
    except Exception as e:
        # If we get duplicate errors, it means objects exist from a previous partial migration
        # In this case, we need to ensure proper cleanup via Docker commands
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise Exception(
                f"Migration failed: {error_msg}\n\n"
                "This usually means the database has leftover objects from a previous migration.\n"
                "Please ensure proper cleanup:\n"
                "  1. docker exec ai_discovery_postgres psql -U ai_user -d postgres -c 'DROP DATABASE IF EXISTS ai_discovery;'\n"
                "  2. docker exec ai_discovery_postgres psql -U ai_user -d postgres -c 'CREATE DATABASE ai_discovery;'\n"
                "  3. Then run: alembic upgrade head"
            ) from e
        raise


def downgrade() -> None:
    """Drop all tables defined on Base.metadata."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)




