#!/bin/bash
# AI Product Discovery Suite - Environment Validation Script
# Ensures .env configuration matches the intended environment (dev/prod)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo -e "${RED}Error: .env file not found in $PROJECT_DIR${NC}"
    exit 1
fi

# Function to check if string contains substring
contains() {
    [[ "$1" == *"$2"* ]]
}

# Validate database URL matches environment
validate_database_url() {
    local db_url="$DATABASE_URL"
    local env="$ENVIRONMENT"

    echo "🔍 Validating database configuration..."
    echo "  Environment: $env"
    echo "  Database URL: $db_url"

    case "$env" in
        "development")
            if contains "$db_url" "localhost"; then
                echo -e "${GREEN}✅ Database URL correctly configured for development (localhost)${NC}"
                return 0
            else
                echo -e "${RED}❌ Database URL mismatch: Development environment should use localhost${NC}"
                return 1
            fi
            ;;
        "production")
            if contains "$db_url" "postgres:"; then
                echo -e "${GREEN}✅ Database URL correctly configured for production (service names)${NC}"
                return 0
            else
                echo -e "${RED}❌ Database URL mismatch: Production environment should use service names${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown environment: $env${NC}"
            return 1
            ;;
    esac
}

# Validate Redis URL matches environment
validate_redis_url() {
    local redis_url="$REDIS_URL"
    local env="$ENVIRONMENT"

    echo "🔍 Validating Redis configuration..."
    echo "  Redis URL: $redis_url"

    case "$env" in
        "development")
            if contains "$redis_url" "localhost"; then
                echo -e "${GREEN}✅ Redis URL correctly configured for development (localhost)${NC}"
                return 0
            else
                echo -e "${RED}❌ Redis URL mismatch: Development environment should use localhost${NC}"
                return 1
            fi
            ;;
        "production")
            if contains "$redis_url" "redis:"; then
                echo -e "${GREEN}✅ Redis URL correctly configured for production (service names)${NC}"
                return 0
            else
                echo -e "${RED}❌ Redis URL mismatch: Production environment should use service names${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown environment: $env${NC}"
            return 1
            ;;
    esac
}

# Validate Elasticsearch URL matches environment
validate_elasticsearch_url() {
    local es_url="$ELASTICSEARCH_URL"
    local env="$ENVIRONMENT"

    echo "🔍 Validating Elasticsearch configuration..."
    echo "  Elasticsearch URL: $es_url"

    case "$env" in
        "development")
            if contains "$es_url" "localhost"; then
                echo -e "${GREEN}✅ Elasticsearch URL correctly configured for development (localhost)${NC}"
                return 0
            else
                echo -e "${RED}❌ Elasticsearch URL mismatch: Development environment should use localhost${NC}"
                return 1
            fi
            ;;
        "production")
            if contains "$es_url" "elasticsearch:"; then
                echo -e "${GREEN}✅ Elasticsearch URL correctly configured for production (service names)${NC}"
                return 0
            else
                echo -e "${RED}❌ Elasticsearch URL mismatch: Production environment should use service names${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown environment: $env${NC}"
            return 1
            ;;
    esac
}

# Validate Qdrant URL matches environment
validate_qdrant_url() {
    local qdrant_url="$QDRANT_URL"
    local env="$ENVIRONMENT"

    echo "🔍 Validating Qdrant configuration..."
    echo "  Qdrant URL: $qdrant_url"

    case "$env" in
        "development")
            if contains "$qdrant_url" "localhost"; then
                echo -e "${GREEN}✅ Qdrant URL correctly configured for development (localhost)${NC}"
                return 0
            else
                echo -e "${RED}❌ Qdrant URL mismatch: Development environment should use localhost${NC}"
                return 1
            fi
            ;;
        "production")
            if contains "$qdrant_url" "qdrant:"; then
                echo -e "${GREEN}✅ Qdrant URL correctly configured for production (service names)${NC}"
                return 0
            else
                echo -e "${RED}❌ Qdrant URL mismatch: Production environment should use service names${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown environment: $env${NC}"
            return 1
            ;;
    esac
}

# Check if containers are running and match environment
check_containers() {
    local env="$ENVIRONMENT"

    echo "🔍 Checking running containers..."

    # Check if any containers are running
    local running_containers=$(docker-compose ps -q 2>/dev/null | wc -l)
    local prod_containers=$(docker-compose -f docker-compose.prod.yml ps -q 2>/dev/null | wc -l)

    case "$env" in
        "development")
            if [ "$running_containers" -gt 0 ]; then
                echo -e "${GREEN}✅ Development containers are running${NC}"
            else
                echo -e "${YELLOW}⚠️  No development containers running${NC}"
            fi
            if [ "$prod_containers" -gt 0 ]; then
                echo -e "${RED}❌ Production containers are running in development mode!${NC}"
                return 1
            fi
            ;;
        "production")
            if [ "$running_containers" -gt 0 ] && [ "$prod_containers" -gt 0 ]; then
                echo -e "${GREEN}✅ Production containers are running${NC}"
            else
                echo -e "${YELLOW}⚠️  Production containers not fully running${NC}"
            fi
            ;;
    esac

    return 0
}

# Main validation function
main() {
    echo "🚀 AI Product Discovery Suite - Environment Validator"
    echo "=================================================="

    local errors=0

    # Run all validations
    validate_database_url || ((errors++))
    validate_redis_url || ((errors++))
    validate_elasticsearch_url || ((errors++))
    validate_qdrant_url || ((errors++))
    check_containers || ((errors++))

    echo ""
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}🎉 All validations passed! Environment is correctly configured.${NC}"
        exit 0
    else
        echo -e "${RED}💥 $errors validation(s) failed! Please check your configuration.${NC}"
        echo ""
        echo "💡 Quick fixes:"
        echo "  - Run 'make dev-infra' for development"
        echo "  - Run 'make prod-up' for production"
        echo "  - Check .env file matches your intended environment"
        exit 1
    fi
}

# Run main function
main "$@"