"""
AI Product Discovery Suite - Seed Test Data

Creates test merchants, API keys, and sample data for development.

@category    Scripts
@package     Development
@license     MIT License

Usage:
    python scripts/seed_test_data.py
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from shared.config.settings import get_settings
from shared.auth.api_key_manager import APIKeyManager

settings = get_settings()

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    print(f"{BLUE}ℹ {message}{RESET}")


def print_warning(message):
    print(f"{YELLOW}⚠ {message}{RESET}")


SEED_MERCHANTS = [
    {
        "name": "Test Merchant Free",
        "email": "free@test.example.com",
        "company": "Free Test Company",
        "tier": "free"
    },
    {
        "name": "Test Merchant Pro",
        "email": "pro@test.example.com",
        "company": "Pro Test Company",
        "tier": "pro"
    },
    {
        "name": "Test Merchant Enterprise",
        "email": "enterprise@test.example.com",
        "company": "Enterprise Test Company",
        "tier": "enterprise"
    }
]


async def list_data(session: AsyncSession) -> None:
    print_info("Listing merchants and API key prefixes...")
    q = text("""
        SELECT m.id, m.name, m.email, m.tier,
               COALESCE((SELECT key_prefix FROM api_keys ak WHERE ak.merchant_id = m.id AND ak.status='active' LIMIT 1), '-') AS key_prefix
        FROM merchants m
        ORDER BY m.id
    """)
    result = await session.execute(q)
    rows = result.fetchall()
    for r in rows:
        print(f"ID={r[0]} | {r[1]} | {r[2]} | tier={r[3]} | key_prefix={r[4]}")


async def drop_seed_data(session: AsyncSession) -> None:
    print_warning("Dropping seeded merchants and related API keys...")
    emails = [m["email"] for m in SEED_MERCHANTS]
    await session.execute(text("DELETE FROM api_keys WHERE merchant_id IN (SELECT id FROM merchants WHERE email = ANY(:emails))"), {"emails": emails})
    await session.execute(text("DELETE FROM merchants WHERE email = ANY(:emails)"), {"emails": emails})
    await session.commit()
    print_success("Dropped seed merchants and keys")


async def create_key(session: AsyncSession, merchant_id: int) -> None:
    manager = APIKeyManager(session)
    api_key, key_record = await manager.create_api_key(
        merchant_id=merchant_id,
        name=f"CLI generated key for {merchant_id}",
        description="Generated via seed CLI"
    )
    print_success(f"Created API key for merchant {merchant_id}")
    print(f"API Key: {api_key}")
    print(f"Rate Limit: {key_record['rate_limit_per_minute']} / min")


async def seed_data():
    """Seed test data"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Seeding Test Data{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    test_api_keys = []
    
    try:
        async with session_factory() as session:
            # Create test merchants
            print_info("Creating test merchants...")
            
            for merchant_data in SEED_MERCHANTS:
                # Check if merchant already exists
                check_query = text("SELECT id FROM merchants WHERE email = :email")
                result = await session.execute(check_query, {"email": merchant_data["email"]})
                existing = result.fetchone()
                
                if existing:
                    print_warning(f"Merchant {merchant_data['name']} already exists (ID: {existing[0]})")
                    merchant_id = existing[0]
                else:
                    # Create merchant
                    query = text("""
                        INSERT INTO merchants (name, email, company_name, tier, status)
                        VALUES (:name, :email, :company, :tier, 'active')
                        RETURNING id, name, email, tier
                    """)
                    
                    result = await session.execute(query, {
                        "name": merchant_data["name"],
                        "email": merchant_data["email"],
                        "company": merchant_data["company"],
                        "tier": merchant_data["tier"]
                    })
                    
                    row = result.fetchone()
                    await session.commit()
                    merchant_id = row[0]
                    
                    print_success(f"Created merchant: {row[1]} (ID: {row[0]}, Tier: {row[3]})")
                
                # Create API key for merchant
                manager = APIKeyManager(session)
                
                # Check if API key already exists
                check_key_query = text("""
                    SELECT id, key_prefix FROM api_keys 
                    WHERE merchant_id = :merchant_id AND status = 'active'
                    LIMIT 1
                """)
                result = await session.execute(check_key_query, {"merchant_id": merchant_id})
                existing_key = result.fetchone()
                
                if existing_key:
                    print_warning(f"API key already exists for merchant {merchant_id} (Prefix: {existing_key[1]})")
                else:
                    api_key, key_record = await manager.create_api_key(
                        merchant_id=merchant_id,
                        name=f"{merchant_data['name']} - Default Key",
                        description="Auto-generated test API key"
                    )
                    
                    test_api_keys.append({
                        "merchant": merchant_data["name"],
                        "tier": merchant_data["tier"],
                        "api_key": api_key,
                        "rate_limit": key_record["rate_limit_per_minute"]
                    })
                    
                    print_success(f"Created API key for {merchant_data['name']} (Rate limit: {key_record['rate_limit_per_minute']}/min)")
        
        await engine.dispose()
        
        # Print summary
        print(f"\n{GREEN}{'=' * 60}{RESET}")
        print(f"{GREEN}Test Data Seeded Successfully!{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}\n")
        
        if test_api_keys:
            print(f"{YELLOW}{'=' * 60}{RESET}")
            print(f"{YELLOW}TEST API KEYS (Save these for testing){RESET}")
            print(f"{YELLOW}{'=' * 60}{RESET}\n")
            
            for key_info in test_api_keys:
                print(f"{BLUE}Merchant:{RESET} {key_info['merchant']}")
                print(f"{BLUE}Tier:{RESET} {key_info['tier']}")
                print(f"{BLUE}Rate Limit:{RESET} {key_info['rate_limit']} requests/minute")
                print(f"{BLUE}API Key:{RESET} {key_info['api_key']}")
                print()
            
            print(f"{YELLOW}Example usage:{RESET}")
            print(f'  curl -H "Authorization: Bearer {test_api_keys[0]["api_key"]}" \\')
            print(f'       http://localhost:7001/api/v1/search/')
            print()
        
        return True
        
    except Exception as e:
        print_error(f"Failed to seed test data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed or manage test data")
    parser.add_argument("action", nargs="?", default="seed", choices=["seed", "list", "drop", "reseed", "create-key"], help="Action to perform")
    parser.add_argument("--merchant-id", dest="merchant_id", type=int, help="Merchant ID for create-key")
    args = parser.parse_args()

    async def main():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        ok = True
        try:
            async with session_factory() as session:
                if args.action == "list":
                    await list_data(session)
                elif args.action == "drop":
                    await drop_seed_data(session)
                elif args.action == "reseed":
                    await drop_seed_data(session)
                    ok = await seed_data()
                elif args.action == "create-key":
                    if not args.merchant_id:
                        print_error("--merchant-id is required for create-key")
                        ok = False
                    else:
                        await create_key(session, args.merchant_id)
                else:
                    ok = await seed_data()
        finally:
            await engine.dispose()
        return ok

    success = asyncio.run(main())
    sys.exit(0 if success else 1)

