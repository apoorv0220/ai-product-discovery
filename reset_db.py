#!/usr/bin/env python3
"""Reset database transaction state for safe rollback."""

import os
from sqlalchemy import create_engine, text

# Database connection
DB_URL = f"postgresql://{os.environ.get('POSTGRES_USER')}:{os.environ.get('POSTGRES_PASSWORD')}@{os.environ.get('POSTGRES_HOST')}:{os.environ.get('POSTGRES_PORT')}/{os.environ.get('POSTGRES_DB')}"

def reset_transaction():
    """Reset aborted transaction state."""
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # Reset transaction state
            conn.execute(text("ROLLBACK;"))
            print("SUCCESS: Transaction state reset successfully")
    except Exception as e:
        print(f"ERROR: Failed to reset transaction: {e}")

if __name__ == "__main__":
    reset_transaction()
