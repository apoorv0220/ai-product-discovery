"""
AI Product Discovery Suite - API Key Management CLI

Command-line tool for managing API keys and merchants.

@category    Backend
@package     Shared/CLI
@license     MIT License

Usage:
    python -m shared.cli.api_keys create-merchant --name "Test Merchant" --email "test@example.com" --tier pro
    python -m shared.cli.api_keys create-key --merchant-id 1 --name "Production Key"
    python -m shared.cli.api_keys list-keys --merchant-id 1
    python -m shared.cli.api_keys revoke-key --key-id 1 --reason "Compromised"
    python -m shared.cli.api_keys stats --merchant-id 1
"""

import asyncio
import sys
import os
from typing import Optional
import argparse
from datetime import datetime
from tabulate import tabulate

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from shared.config.settings import get_settings
from shared.auth.api_key_manager import APIKeyManager

settings = get_settings()


class APIKeyCLI:
    """CLI tool for API key management"""
    
    def __init__(self):
        """Initialize CLI"""
        # Create async engine
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def create_merchant(
        self,
        name: str,
        email: str,
        company_name: Optional[str] = None,
        tier: str = "free"
    ) -> int:
        """
        Create a new merchant
        
        Args:
            name: Merchant name
            email: Merchant email
            company_name: Company name
            tier: Subscription tier
            
        Returns:
            Merchant ID
        """
        async with self.session_factory() as session:
            query = text("""
                INSERT INTO merchants (name, email, company_name, tier, status)
                VALUES (:name, :email, :company_name, :tier, 'active')
                RETURNING id, name, email, tier, created_at
            """)
            
            result = await session.execute(query, {
                "name": name,
                "email": email,
                "company_name": company_name or name,
                "tier": tier
            })
            
            row = result.fetchone()
            await session.commit()
            
            print(f"\n✓ Merchant created successfully!")
            print(f"  ID: {row[0]}")
            print(f"  Name: {row[1]}")
            print(f"  Email: {row[2]}")
            print(f"  Tier: {row[3]}")
            print(f"  Created: {row[4]}")
            
            return row[0]
    
    async def create_api_key(
        self,
        merchant_id: int,
        name: str,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        Create a new API key for a merchant
        
        Args:
            merchant_id: Merchant ID
            name: Key name
            description: Key description
            expires_in_days: Optional expiration in days
            
        Returns:
            API key (plain text)
        """
        async with self.session_factory() as session:
            manager = APIKeyManager(session)
            
            api_key, key_record = await manager.create_api_key(
                merchant_id=merchant_id,
                name=name,
                description=description,
                expires_in_days=expires_in_days
            )
            
            print(f"\n✓ API Key created successfully!")
            print(f"  Key ID: {key_record['id']}")
            print(f"  Name: {key_record['name']}")
            print(f"  Rate Limit: {key_record['rate_limit_per_minute']} req/min")
            print(f"  Scopes: {key_record['scopes']}")
            print(f"\n  ⚠️  IMPORTANT: Save this API key securely. It won't be shown again!")
            print(f"\n  API Key: {api_key}")
            print()
            
            return api_key
    
    async def list_keys(self, merchant_id: int, include_revoked: bool = False):
        """
        List all API keys for a merchant
        
        Args:
            merchant_id: Merchant ID
            include_revoked: Include revoked keys
        """
        async with self.session_factory() as session:
            manager = APIKeyManager(session)
            keys = await manager.list_merchant_keys(merchant_id, include_revoked)
            
            if not keys:
                print(f"\nNo API keys found for merchant {merchant_id}")
                return
            
            # Format for display
            table_data = []
            for key in keys:
                table_data.append([
                    key['id'],
                    key['key_prefix'],
                    key['name'],
                    key['rate_limit_per_minute'],
                    key['status'],
                    key['usage_count'],
                    key['last_used_at'].strftime('%Y-%m-%d %H:%M') if key['last_used_at'] else 'Never',
                    key['created_at'].strftime('%Y-%m-%d')
                ])
            
            print(f"\nAPI Keys for Merchant {merchant_id}:")
            print(tabulate(
                table_data,
                headers=['ID', 'Prefix', 'Name', 'Rate Limit', 'Status', 'Usage', 'Last Used', 'Created'],
                tablefmt='grid'
            ))
            print()
    
    async def revoke_key(self, key_id: int, reason: Optional[str] = None):
        """
        Revoke an API key
        
        Args:
            key_id: API key ID
            reason: Revocation reason
        """
        async with self.session_factory() as session:
            manager = APIKeyManager(session)
            success = await manager.revoke_api_key(key_id, reason=reason)
            
            if success:
                print(f"\n✓ API key {key_id} revoked successfully")
                if reason:
                    print(f"  Reason: {reason}")
            else:
                print(f"\n✗ Failed to revoke API key {key_id}")
    
    async def get_stats(self, merchant_id: int):
        """
        Get usage statistics for merchant
        
        Args:
            merchant_id: Merchant ID
        """
        async with self.session_factory() as session:
            # Get merchant info
            query = text("""
                SELECT name, email, tier, status, created_at
                FROM merchants
                WHERE id = :merchant_id
            """)
            result = await session.execute(query, {"merchant_id": merchant_id})
            merchant = result.fetchone()
            
            if not merchant:
                print(f"\n✗ Merchant {merchant_id} not found")
                return
            
            # Get key stats
            query = text("""
                SELECT 
                    COUNT(*) as total_keys,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_keys,
                    COUNT(CASE WHEN status = 'revoked' THEN 1 END) as revoked_keys,
                    SUM(usage_count) as total_requests
                FROM api_keys
                WHERE merchant_id = :merchant_id
            """)
            result = await session.execute(query, {"merchant_id": merchant_id})
            stats = result.fetchone()
            
            # Get recent usage
            query = text("""
                SELECT 
                    COUNT(*) as requests_24h,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors_24h
                FROM api_key_usage
                WHERE merchant_id = :merchant_id
                  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)
            result = await session.execute(query, {"merchant_id": merchant_id})
            usage = result.fetchone()
            
            print(f"\n{'='*60}")
            print(f"Merchant Statistics: {merchant[0]}")
            print(f"{'='*60}")
            print(f"\nMerchant Info:")
            print(f"  Email: {merchant[1]}")
            print(f"  Tier: {merchant[2]}")
            print(f"  Status: {merchant[3]}")
            print(f"  Created: {merchant[4].strftime('%Y-%m-%d')}")
            
            print(f"\nAPI Keys:")
            print(f"  Total Keys: {stats[0] or 0}")
            print(f"  Active Keys: {stats[1] or 0}")
            print(f"  Revoked Keys: {stats[2] or 0}")
            
            print(f"\nUsage:")
            print(f"  Total Requests (All Time): {stats[3] or 0}")
            print(f"  Requests (Last 24h): {usage[0] or 0}")
            print(f"  Avg Response Time: {int(usage[1] or 0)} ms")
            print(f"  Errors (Last 24h): {usage[2] or 0}")
            print(f"\n{'='*60}\n")
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="AI Product Discovery Suite - API Key Management CLI"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create merchant command
    merchant_parser = subparsers.add_parser('create-merchant', help='Create a new merchant')
    merchant_parser.add_argument('--name', required=True, help='Merchant name')
    merchant_parser.add_argument('--email', required=True, help='Merchant email')
    merchant_parser.add_argument('--company', help='Company name')
    merchant_parser.add_argument('--tier', choices=['free', 'basic', 'pro', 'enterprise'],
                                default='free', help='Subscription tier')
    
    # Create API key command
    key_parser = subparsers.add_parser('create-key', help='Create a new API key')
    key_parser.add_argument('--merchant-id', type=int, required=True, help='Merchant ID')
    key_parser.add_argument('--name', required=True, help='Key name')
    key_parser.add_argument('--description', help='Key description')
    key_parser.add_argument('--expires-in-days', type=int, help='Expiration in days')
    
    # List keys command
    list_parser = subparsers.add_parser('list-keys', help='List API keys for merchant')
    list_parser.add_argument('--merchant-id', type=int, required=True, help='Merchant ID')
    list_parser.add_argument('--include-revoked', action='store_true',
                            help='Include revoked keys')
    
    # Revoke key command
    revoke_parser = subparsers.add_parser('revoke-key', help='Revoke an API key')
    revoke_parser.add_argument('--key-id', type=int, required=True, help='API key ID')
    revoke_parser.add_argument('--reason', help='Revocation reason')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Get merchant statistics')
    stats_parser.add_argument('--merchant-id', type=int, required=True, help='Merchant ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = APIKeyCLI()
    
    try:
        if args.command == 'create-merchant':
            await cli.create_merchant(
                name=args.name,
                email=args.email,
                company_name=args.company,
                tier=args.tier
            )
        
        elif args.command == 'create-key':
            await cli.create_api_key(
                merchant_id=args.merchant_id,
                name=args.name,
                description=args.description,
                expires_in_days=args.expires_in_days
            )
        
        elif args.command == 'list-keys':
            await cli.list_keys(
                merchant_id=args.merchant_id,
                include_revoked=args.include_revoked
            )
        
        elif args.command == 'revoke-key':
            await cli.revoke_key(
                key_id=args.key_id,
                reason=args.reason
            )
        
        elif args.command == 'stats':
            await cli.get_stats(
                merchant_id=args.merchant_id
            )
    
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())

