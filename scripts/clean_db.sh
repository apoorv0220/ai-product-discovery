#!/bin/bash

# Define colors for output
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Database Cleanup Script${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${YELLOW}This script will:${NC}"
echo -e "  1. Drop the 'ai_discovery' database (if it exists)"
echo -e "  2. Create a fresh 'ai_discovery' database"
echo -e "  3. Verify the database is empty"
echo ""

read -p "Continue? (Y/N) " confirm
if [[ "$confirm" != "Y" && "$confirm" != "y" ]]; then
    echo -e "${YELLOW}Cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Dropping database...${NC}"

# Capture output and exit code
drop_result=$(docker exec ai_discovery_postgres psql -U ai_user -d postgres -c "DROP DATABASE IF EXISTS ai_discovery;" 2>&1)
drop_status=$?

if [ $drop_status -eq 0 ]; then
    echo -e "${GREEN}  [OK] Database dropped${NC}"
else
    echo -e "${YELLOW}  [WARNING] Drop command returned non-zero exit code${NC}"
    echo -e "${GRAY}  Output: $drop_result${NC}"
fi

echo ""
echo -e "${YELLOW}Creating fresh database...${NC}"

create_result=$(docker exec ai_discovery_postgres psql -U ai_user -d postgres -c "CREATE DATABASE ai_discovery;" 2>&1)
create_status=$?

if [ $create_status -eq 0 ]; then
    echo -e "${GREEN}  [OK] Database created${NC}"
else
    echo -e "${RED}  [ERROR] Failed to create database${NC}"
    echo -e "${RED}  Output: $create_result${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Verifying database is empty...${NC}"

# Get counts and trim whitespace using xargs
table_check=$(docker exec ai_discovery_postgres psql -U ai_user -d ai_discovery -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>&1)
index_check=$(docker exec ai_discovery_postgres psql -U ai_user -d ai_discovery -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';" 2>&1)

table_count=$(echo "$table_check" | xargs)
index_count=$(echo "$index_check" | xargs)

if [[ ("$table_count" == "0" || -z "$table_count") && ("$index_count" == "0" || -z "$index_count") ]]; then
    echo -e "${GREEN}  [OK] Database is empty (no tables or indexes)${NC}"
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}Database cleanup complete!${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${GREEN}You can now run migrations:${NC}"
    echo -e "  cd backend"
    echo -e "  alembic upgrade head"
    echo ""
else
    echo -e "${YELLOW}  [WARNING] Database may not be completely empty:${NC}"
    echo -e "${GRAY}    Tables: $table_count${NC}"
    echo -e "${GRAY}    Indexes: $index_count${NC}"
fi