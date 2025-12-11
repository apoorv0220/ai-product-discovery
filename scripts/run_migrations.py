"""
AI Product Discovery Suite - Database Migration Runner

Runs SQL migration files in order.

@category    Scripts
@package     Database
@license     MIT License

Usage:
    python scripts/run_migrations.py
"""

import os
import sys
import psycopg2
from pathlib import Path

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


def run_migrations():
    """Run all migration files"""
    # Detect if running inside Docker container
    # Check for common container indicators
    in_container = (
        os.path.exists('/.dockerenv') or  # Docker container marker
        os.getenv('DOCKER_CONTAINER') == 'true' or  # Explicit env var
        os.getenv('HOSTNAME') and os.getenv('HOSTNAME').startswith('ai_discovery_')  # Container naming pattern
    )

    if in_container:
        # Running inside Docker container - use container network
        host = os.getenv('POSTGRES_HOST', 'postgres')  # Container name
        port = os.getenv('POSTGRES_PORT', '5432')      # Internal port
        print_info("Detected: Running inside Docker container")
    else:
        # Running on host machine
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '7010')      # External port
        print_info("Detected: Running on host machine")

    database = os.getenv('POSTGRES_DB', 'ai_discovery')
    user = os.getenv('POSTGRES_USER', 'ai_user')
    password = os.getenv('POSTGRES_PASSWORD', 'ai_password')
    
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Running Database Migrations{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    print_info(f"Connecting to database: {database} at {host}:{port}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        print_success("Database connection established")
        
        # Get migration directory
        migrations_dir = Path(__file__).parent.parent / 'backend' / 'shared' / 'database' / 'migrations'
        
        if not migrations_dir.exists():
            print_error(f"Migrations directory not found: {migrations_dir}")
            return False
        
        # Get all SQL files
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        if not migration_files:
            print_info("No migration files found")
            return True
        
        print_info(f"Found {len(migration_files)} migration file(s)\n")
        
        # Run each migration
        for migration_file in migration_files:
            print(f"{BLUE}Running migration: {migration_file.name}{RESET}")
            
            try:
                # Read migration file
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                
                # Execute migration
                cursor.execute(sql)
                conn.commit()
                
                print_success(f"Migration {migration_file.name} completed successfully")
                print()
                
            except Exception as e:
                print_error(f"Migration {migration_file.name} failed: {str(e)}")
                conn.rollback()
                return False
        
        cursor.close()
        conn.close()
        
        print(f"\n{GREEN}{'=' * 60}{RESET}")
        print(f"{GREEN}All migrations completed successfully!{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}\n")
        
        return True
        
    except psycopg2.OperationalError as e:
        print_error(f"Database connection failed: {str(e)}")
        print_info("Make sure PostgreSQL is running: docker-compose up -d postgres")
        return False
    except Exception as e:
        print_error(f"Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)

