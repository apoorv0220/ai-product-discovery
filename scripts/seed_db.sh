#!/bin/bash
# AI Product Discovery Suite - Database Seeding Script
# Seeds test data into the PostgreSQL database

set -e

echo "AI Product Discovery Suite - Database Seeding"
echo "============================================"

# Check if we're in the right directory
if [ ! -f "scripts/seed_sql.sql" ]; then
    echo "❌ Error: seed_sql.sql not found. Run this script from the project root."
    exit 1
fi

# Check if Docker container is running
if ! docker ps | grep -q ai_discovery_postgres; then
    echo "❌ Error: PostgreSQL container 'ai_discovery_postgres' is not running."
    echo "   Start it with: docker-compose up -d postgres"
    exit 1
fi

echo "✓ PostgreSQL container is running"

# Run the SQL seed script
echo "📝 Seeding test data..."
if docker exec -i ai_discovery_postgres psql -U ai_user -d ai_discovery < scripts/seed_sql.sql; then
    echo ""
    echo "✅ Test data seeded successfully!"
    echo ""
    echo "Test API Keys:"
    echo "=============="
    echo "Free Tier:     sk_free_test_key_12345678901234567890123456789012"
    echo "Pro Tier:      sk_pro_test_key_123456789012345678901234567890123"
    echo "Enterprise:    sk_enterprise_test_key_123456789012345678901234567890"
    echo ""
    echo "Usage example:"
    echo "curl -H \"Authorization: Bearer sk_free_test_key_12345678901234567890123456789012\" \\"
    echo "     http://localhost:7001/api/v1/search/"
else
    echo "❌ Failed to seed test data"
    exit 1
fi