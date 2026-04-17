#!/usr/bin/env python3
"""Clean analytics schema while preserving other data."""

import os
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.engine.reflection import Inspector

# Database connection
DB_URL = f"postgresql://{os.environ.get('POSTGRES_USER')}:{os.environ.get('POSTGRES_PASSWORD')}@{os.environ.get('POSTGRES_HOST')}:{os.environ.get('POSTGRES_PORT')}/{os.environ.get('POSTGRES_DB')}"

def clean_analytics_schema():
    """Clean all analytics-related tables and columns while preserving other data."""
    try:
        engine = create_engine(DB_URL)

        with engine.connect() as conn:
            # Start a fresh transaction
            trans = conn.begin()

            try:
                # Check if analytics tables exist and drop them
                inspector = Inspector.from_engine(engine)

                analytics_tables = [
                    'analytics_events_archive',
                    'session_analytics',
                    'user_behavior_aggregations',
                    'analytics_aggregations',
                    'analytics_events'
                ]

                for table in analytics_tables:
                    if table in inspector.get_table_names():
                        print(f"Dropping table: {table}")
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

                # Reset any sequences if they exist
                sequences = [
                    'analytics_events_id_seq',
                    'analytics_aggregations_id_seq',
                    'user_behavior_aggregations_id_seq',
                    'session_analytics_id_seq',
                    'analytics_events_archive_id_seq'
                ]

                for seq in sequences:
                    try:
                        conn.execute(text(f"DROP SEQUENCE IF EXISTS {seq}"))
                    except:
                        pass  # Sequence may not exist

                trans.commit()
                print("SUCCESS: Analytics schema cleaned successfully")

            except Exception as e:
                trans.rollback()
                print(f"ERROR: Failed to clean analytics schema: {e}")
                raise

    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")

if __name__ == "__main__":
    clean_analytics_schema()
