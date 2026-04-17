"""
AI Product Discovery Suite - Seed Test Data

Creates test merchants, API keys, and sample data for development using SQLAlchemy ORM.

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

# Color codes (defined early for path setup)
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_success(message):
    print(f"{GREEN}+ {message}{RESET}")


def print_error(message):
    print(f"{RED}X {message}{RESET}")


def print_info(message):
    print(f"{BLUE}i {message}{RESET}")


def print_warning(message):
    print(f"{YELLOW}! {message}{RESET}")


# Setup paths - dual environment support
def setup_paths():
    """Set up Python paths for both local dev and production Docker"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    backend_path = project_root / "backend"

    # Always add backend path first (where shared modules are)
    sys.path.insert(0, str(backend_path))
    sys.path.insert(0, str(project_root))

    # Verify we can find the shared modules
    if (backend_path / "shared").exists():
        print_info("Using local development environment (backend/shared found)")
    elif (Path("/app/shared")).exists():
        # Production Docker - modules are in /app
        sys.path.insert(0, "/app")
        print_info("Using production Docker environment (/app/shared found)")
    else:
        print_error("Could not find shared modules")
        print_error(f"Backend path: {backend_path}")
        print_error(f"Backend/shared exists: {(backend_path / 'shared').exists()}")
        print_error(f"Current working directory: {Path.cwd()}")
        sys.exit(1)

# Setup paths before other imports
setup_paths()

# Import after path setup
try:
    from shared.config.settings import get_settings
    from shared.auth.api_key_manager import APIKeyManager
    from shared.models import Merchant, APIKey
    from shared.database.base import get_database_session
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    print_success("Successfully imported shared modules and models")
except ImportError as e:
    print_error(f"Failed to import modules: {e}")
    print_error("This script requires access to the shared backend modules.")
    print_error("Make sure you're running from the project root with venv activated.")
    print_error("Try installing dependencies: pip install -r backend/requirements.txt")
    sys.exit(1)

settings = get_settings()


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
    from shared.models import Merchant, APIKey
    from sqlalchemy import select, func
    
    print_info("Listing merchants and API key prefixes...")
    result = await session.execute(
        select(
            Merchant.id,
            Merchant.name,
            Merchant.email,
            Merchant.tier,
            func.coalesce(
                select(APIKey.key_prefix)
                .where(APIKey.merchant_id == Merchant.id)
                .where(APIKey.status == 'active')
                .limit(1)
                .scalar_subquery(),
                '-'
            ).label('key_prefix')
        ).order_by(Merchant.id)
    )
    rows = result.fetchall()
    for r in rows:
        print(f"ID={r.id} | {r.name} | {r.email} | tier={r.tier} | key_prefix={r.key_prefix}")


async def drop_seed_data(session: AsyncSession) -> None:
    from shared.models import Merchant, APIKey
    from sqlalchemy import select, delete
    
    print_warning("Dropping seeded merchants and related API keys...")
    emails = [m["email"] for m in SEED_MERCHANTS]
    
    # Find merchant IDs
    result = await session.execute(
        select(Merchant.id).where(Merchant.email.in_(emails))
    )
    merchant_ids = [row[0] for row in result.fetchall()]
    
    if merchant_ids:
        # Delete API keys
        await session.execute(
            delete(APIKey).where(APIKey.merchant_id.in_(merchant_ids))
        )
        # Delete merchants
        await session.execute(
            delete(Merchant).where(Merchant.id.in_(merchant_ids))
        )
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
                from shared.models import Merchant
                from sqlalchemy import select
                
                # Check if merchant already exists
                result = await session.execute(
                    select(Merchant.id).where(Merchant.email == merchant_data["email"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print_warning(f"Merchant {merchant_data['name']} already exists (ID: {existing})")
                    merchant_id = existing
                else:
                    # Create merchant
                    merchant = Merchant(
                        name=merchant_data["name"],
                        email=merchant_data["email"],
                        company_name=merchant_data["company"],
                        tier=merchant_data["tier"],
                        status="active"
                    )
                    
                    session.add(merchant)
                    await session.flush()
                    await session.refresh(merchant)
                    await session.commit()
                    merchant_id = merchant.id
                    
                    print_success(f"Created merchant: {merchant.name} (ID: {merchant.id}, Tier: {merchant.tier})")
                
                # Create API key for merchant
                manager = APIKeyManager(session)
                
                # Check if API key already exists
                from shared.models import APIKey
                from sqlalchemy import select
                
                result = await session.execute(
                    select(APIKey.id, APIKey.key_prefix)
                    .where(APIKey.merchant_id == merchant_id)
                    .where(APIKey.status == 'active')
                    .limit(1)
                )
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


# Template for other scripts to support dual environments
"""
DUAL ENVIRONMENT SUPPORT TEMPLATE:

For scripts that need to work in both local dev and production Docker:

1. Replace the path setup section with:

def setup_paths():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check environment type
    if (script_dir / "shared").exists():
        # Local development
        sys.path.insert(0, str(project_root))
    else:
        # Production Docker - try common mount points
        possible_paths = [project_root, Path("/app"), Path("/opt/app")]
        for path in possible_paths:
            if (path / "shared").exists():
                sys.path.insert(0, str(path))
                break
        else:
            # Fallback search
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / "shared").exists():
                    sys.path.insert(0, str(parent))
                    break
            else:
                raise RuntimeError("Could not find shared modules")

# Call setup_paths() before other imports
setup_paths()

2. For database connections, use environment variables with fallbacks:
   host = os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', 'localhost'))
   port = os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', '7010'))
   etc.

3. Handle import errors gracefully with informative messages.
"""
