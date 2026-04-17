#!/usr/bin/env python3
"""
API Key Generation Script

Generates new API keys for merchants in the AI Product Discovery Suite.

Usage:
    python scripts/generate_api_key.py --merchant-id 1 --name "My API Key" --environment live --tier pro

Arguments:
    --merchant-id: Merchant ID to create key for (required)
    --name: Human-readable name for the key (required)
    --environment: Environment type - 'live' or 'test' (default: live)
    --tier: Rate limit tier - 'free', 'basic', 'pro', 'enterprise' (default: auto-detect from merchant)
    --help: Show this help message
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from shared.config.settings import get_settings
from shared.auth.api_key_manager import APIKeyManager
from shared.database.base import AsyncSessionLocal


async def generate_api_key(merchant_id: int, name: str, environment: str = 'live', tier: str = None):
    """Generate a new API key for the specified merchant"""

    # Get database session
    db = AsyncSessionLocal()

    try:
        # Initialize API key manager
        api_key_manager = APIKeyManager(db)

        # Generate the key
        api_key, key_record = await api_key_manager.create_api_key(
            merchant_id=merchant_id,
            name=name,
            environment=environment,
            tier=tier
        )

        # Get rate limit info
        rate_limits = {
            'free': 100,
            'basic': 1000,
            'pro': 5000,
            'enterprise': 10000
        }
        actual_tier = key_record.get('tier', 'free')
        rate_limit = rate_limits.get(actual_tier, 100)

        print("API Key Generated Successfully!")
        print(f"API Key: {api_key}")
        print(f"Merchant ID: {key_record['merchant_id']}")
        print(f"Name: {key_record['name']}")
        print(f"Environment: {environment}")
        print(f"Tier: {actual_tier}")
        print(f"Rate Limit: {rate_limit} requests/minute")
        print(f"Created: {key_record['created_at']}")
        print(f"Status: {key_record['status']}")

        return api_key

    except Exception as e:
        print(f"Error generating API key: {e}")
        return None
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate API keys for AI Product Discovery Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--merchant-id',
        type=int,
        required=True,
        help='Merchant ID to create key for'
    )

    parser.add_argument(
        '--name',
        type=str,
        required=True,
        help='Human-readable name for the API key'
    )

    parser.add_argument(
        '--environment',
        type=str,
        choices=['live', 'test'],
        default='live',
        help='Environment type (default: live)'
    )

    parser.add_argument(
        '--tier',
        type=str,
        choices=['free', 'basic', 'pro', 'enterprise'],
        default=None,
        help='Rate limit tier (default: auto-detect from merchant tier)'
    )

    args = parser.parse_args()

    # Validate merchant ID
    if args.merchant_id <= 0:
        print("❌ Merchant ID must be a positive integer")
        sys.exit(1)

    # Validate name
    if not args.name.strip():
        print("❌ API key name cannot be empty")
        sys.exit(1)

    # Run the async function
    api_key = asyncio.run(generate_api_key(
        merchant_id=args.merchant_id,
        name=args.name.strip(),
        environment=args.environment,
        tier=args.tier
    ))

    if api_key:
        print("\nKeep this API key secure and don't share it publicly!")
        print("   You can use it in the Authorization header: 'Bearer <api_key>'")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
