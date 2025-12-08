#!/usr/bin/env python3
"""
Simple database initialization script
Creates all necessary tables for AI Product Discovery
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from shared.config.settings import get_settings

settings = get_settings()

async def create_tables():
    """Create all database tables"""

    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        print("Creating database tables...")

        # Create extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\""))
        print("✓ Extensions created")

        # Create merchants table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS merchants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                company_name VARCHAR(255),
                tier VARCHAR(50) DEFAULT 'free',
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create api_keys table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                merchant_id INTEGER REFERENCES merchants(id) ON DELETE CASCADE,
                key_hash VARCHAR(255) NOT NULL,
                key_prefix VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255),
                description TEXT,
                status VARCHAR(50) DEFAULT 'active',
                rate_limit_per_minute INTEGER DEFAULT 100,
                scopes JSONB DEFAULT '["read", "write"]'::jsonb,
                expires_at TIMESTAMP WITH TIME ZONE,
                created_by INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create users table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create customer_profiles table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                preferences JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create categories table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create products table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                sku VARCHAR(100) UNIQUE NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                stock_quantity INTEGER DEFAULT 0,
                attributes JSONB DEFAULT '{}'::jsonb,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create search_queries table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                filters JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create search_logs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id SERIAL PRIMARY KEY,
                query_id INTEGER REFERENCES search_queries(id) ON DELETE SET NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                results_count INTEGER,
                response_time_ms INTEGER,
                clicked_products INTEGER[] DEFAULT ARRAY[]::INTEGER[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create user_sessions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                session_id VARCHAR(255) UNIQUE NOT NULL,
                started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create analytics_events table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                session_id VARCHAR(255) REFERENCES user_sessions(session_id) ON DELETE SET NULL,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                properties JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create recommendation_logs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recommendation_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                context VARCHAR(50),
                recommended_products INTEGER[] DEFAULT ARRAY[]::INTEGER[],
                algorithm VARCHAR(50),
                confidence_score DECIMAL(5,4),
                clicked_products INTEGER[] DEFAULT ARRAY[]::INTEGER[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_name ON products USING GIN (to_tsvector('english', name))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_description ON products USING GIN (to_tsvector('english', description))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_queries_user_id ON search_queries(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries(created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_product_id ON analytics_events(product_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recommendation_logs_user_id ON recommendation_logs(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recommendation_logs_created_at ON recommendation_logs(created_at)"))

        # Grant permissions
        await conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_user"))
        await conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_user"))

        print("✓ All tables created successfully")

async def main():
    try:
        await create_tables()
        print("🎉 Database initialization completed successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
