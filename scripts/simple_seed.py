#!/usr/bin/env python3
"""
Simple Seed Script for AI Product Discovery Suite

Creates basic test data without complex dependencies.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(project_root))

# Import minimal requirements
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, insert, text
from sqlalchemy.orm import sessionmaker
import uuid
import bcrypt
import secrets

# Database connection settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery')

async def create_merchant_and_key(engine, name, email, company, tier):
    """Create a merchant and API key directly in the database"""

    async with AsyncSession(engine) as session:
        try:
            # Check if merchant exists
            result = await session.execute(
                select(text("*")).select_from(text("merchants")).where(text("email = :email")),
                {"email": email}
            )
            existing = result.fetchone()

            if existing:
                print(f"Merchant {name} already exists (ID: {existing[0]})")
                merchant_id = existing[0]
            else:
                # Create merchant
                await session.execute(
                    text("""
                        INSERT INTO merchants (name, email, company_name, tier, status, created_at, updated_at)
                        VALUES (:name, :email, :company, :tier, 'active', :now, :now)
                        RETURNING id
                    """),
                    {
                        "name": name,
                        "email": email,
                        "company": company,
                        "tier": tier,
                        "now": datetime.utcnow()
                    }
                )
                result = await session.execute(
                    select(text("id")).select_from(text("merchants")).where(text("email = :email")),
                    {"email": email}
                )
                merchant_id = result.scalar()
                print(f"Created merchant: {name} (ID: {merchant_id})")

            # Check if API key exists
            result = await session.execute(
                text("SELECT id FROM api_keys WHERE merchant_id = :merchant_id AND status = 'active' LIMIT 1"),
                {"merchant_id": merchant_id}
            )
            existing_key = result.fetchone()

            if existing_key:
                print(f"API key already exists for merchant {merchant_id}")
            else:
                # Generate API key
                api_key = f"sk_{secrets.token_urlsafe(32)}"
                key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                key_prefix = api_key[:8]

                # Rate limits based on tier
                rate_limits = {
                    'free': 100,
                    'pro': 1000,
                    'enterprise': 10000
                }
                rate_limit = rate_limits.get(tier, 100)

                await session.execute(
                    text("""
                        INSERT INTO api_keys (
                            merchant_id, key_hash, key_prefix, name, description,
                            rate_limit_per_minute, status, created_at
                        ) VALUES (
                            :merchant_id, :key_hash, :key_prefix, :name, :description,
                            :rate_limit, 'active', :now
                        )
                    """),
                    {
                        "merchant_id": merchant_id,
                        "key_hash": key_hash,
                        "key_prefix": key_prefix,
                        "name": f"{name} - Default Key",
                        "description": "Auto-generated test API key",
                        "rate_limit": rate_limit,
                        "now": datetime.utcnow()
                    }
                )

                print(f"Created API key for {name}")
                print(f"API Key: {api_key}")
                print(f"Rate Limit: {rate_limit}/min")

            await session.commit()

        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")
            raise

async def main():
    print("AI Product Discovery Suite - Simple Seed Script")
    print("=" * 50)

    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")

        # Create test merchants
        merchants = [
            ("Test Merchant Free", "free@test.example.com", "Free Test Company", "free"),
            ("Test Merchant Pro", "pro@test.example.com", "Pro Test Company", "pro"),
            ("Test Merchant Enterprise", "enterprise@test.example.com", "Enterprise Test Company", "enterprise")
        ]

        for name, email, company, tier in merchants:
            await create_merchant_and_key(engine, name, email, company, tier)

        print("\n" + "=" * 50)
        print("✓ Test data seeded successfully!")
        print("You can now use the API keys above to test the services.")

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1
    finally:
        await engine.dispose()

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)