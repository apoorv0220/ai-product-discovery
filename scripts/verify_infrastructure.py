"""
AI Product Discovery Suite - Infrastructure Verification Script

Validates all infrastructure components are operational before starting services.

@category    Scripts
@package     Infrastructure
@author      AI Product Discovery Team
@license     MIT License
"""

import sys
import os
import time
import psycopg2
import redis
from elasticsearch import Elasticsearch
from typing import Dict, Any, Tuple
import requests

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(message: str):
    """Print section header"""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{message:^80}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{RED}✗ {message}{RESET}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{YELLOW}⚠ {message}{RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"{BLUE}ℹ {message}{RESET}")


def verify_environment_variables() -> Tuple[bool, Dict[str, str]]:
    """Verify required environment variables are set"""
    print_header("Environment Variables Verification")
    
    required_vars = {
        'POSTGRES_DB': 'ai_discovery',
        'POSTGRES_USER': 'ai_user',
        'POSTGRES_PASSWORD': 'ai_password',
        'REDIS_PASSWORD': 'redis_password',
        'SECRET_KEY': 'secret-key-change-in-production',
        'JWT_SECRET_KEY': 'jwt-secret-key-change-in-production',
    }
    
    optional_vars = [
        'OPENAI_API_KEY',
        'ELASTICSEARCH_URL',
        'QDRANT_URL',
        'ENVIRONMENT',
    ]
    
    env_vars = {}
    all_valid = True
    
    # Check required variables
    for var, default in required_vars.items():
        value = os.getenv(var, default)
        env_vars[var] = value
        if value == default and var.endswith('KEY'):
            print_warning(f"{var}: Using default value (change in production!)")
        else:
            print_success(f"{var}: Set")
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            env_vars[var] = value
            print_success(f"{var}: Set")
        else:
            print_info(f"{var}: Not set (optional)")
    
    return all_valid, env_vars


def verify_postgresql(env_vars: Dict[str, str]) -> bool:
    """Verify PostgreSQL connectivity and schema"""
    print_header("PostgreSQL Verification")
    
    try:
        # Connection parameters
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '7010')
        database = env_vars.get('POSTGRES_DB', 'ai_discovery')
        user = env_vars.get('POSTGRES_USER', 'ai_user')
        password = env_vars.get('POSTGRES_PASSWORD', 'ai_password')
        
        print_info(f"Connecting to PostgreSQL at {host}:{port}...")
        
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )
        
        print_success("PostgreSQL connection established")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_success(f"PostgreSQL version: {version.split(',')[0]}")
        
        # Check database exists
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print_success(f"Current database: {db_name}")
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        if tables:
            print_success(f"Found {len(tables)} tables in database")
            for table in tables:
                print_info(f"  - {table[0]}")
        else:
            print_warning("No tables found (expected for fresh installation)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print_error(f"PostgreSQL connection failed: {str(e)}")
        print_info("Make sure PostgreSQL is running: docker-compose up -d postgres")
        return False
    except Exception as e:
        print_error(f"PostgreSQL verification failed: {str(e)}")
        return False


def verify_redis(env_vars: Dict[str, str]) -> bool:
    """Verify Redis connectivity and persistence"""
    print_header("Redis Verification")
    
    try:
        # Connection parameters
        host = os.getenv('REDIS_HOST', 'localhost')
        port = os.getenv('REDIS_PORT', '7011')
        password = env_vars.get('REDIS_PASSWORD', 'redis_password_2024')
        
        print_info(f"Connecting to Redis at {host}:{port}...")
        
        # Test connection
        r = redis.Redis(
            host=host,
            port=int(port),
            password=password,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # Test ping
        if r.ping():
            print_success("Redis connection established")
        
        # Get server info
        info = r.info()
        print_success(f"Redis version: {info['redis_version']}")
        print_success(f"Redis mode: {info['redis_mode']}")
        print_success(f"Connected clients: {info['connected_clients']}")
        
        # Check persistence configuration
        if info.get('aof_enabled') == 1:
            print_success("AOF persistence: Enabled")
        else:
            print_warning("AOF persistence: Disabled")
        
        if info.get('rdb_last_save_time'):
            print_success("RDB snapshots: Configured")
        
        # Test write/read
        test_key = "infrastructure_test"
        test_value = "verified"
        r.setex(test_key, 10, test_value)
        retrieved_value = r.get(test_key)
        
        if retrieved_value == test_value:
            print_success("Redis write/read test: Passed")
            r.delete(test_key)
        
        # Check memory usage
        used_memory_human = info.get('used_memory_human', 'Unknown')
        print_info(f"Memory usage: {used_memory_human}")
        
        r.close()
        return True
        
    except redis.ConnectionError as e:
        print_error(f"Redis connection failed: {str(e)}")
        print_info("Make sure Redis is running: docker-compose up -d redis")
        return False
    except Exception as e:
        print_error(f"Redis verification failed: {str(e)}")
        return False


def verify_elasticsearch() -> bool:
    """Verify Elasticsearch cluster health"""
    print_header("Elasticsearch Verification")
    
    try:
        # Connection parameters
        url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        
        print_info(f"Connecting to Elasticsearch at {url}...")
        
        # Test connection
        es = Elasticsearch([url], request_timeout=10)
        
        if not es.ping():
            raise Exception("Elasticsearch ping failed")
        
        print_success("Elasticsearch connection established")
        
        # Get cluster health
        health = es.cluster.health()
        cluster_name = health['cluster_name']
        status = health['status']
        
        print_success(f"Cluster name: {cluster_name}")
        
        if status == 'green':
            print_success(f"Cluster status: {status}")
        elif status == 'yellow':
            print_warning(f"Cluster status: {status} (acceptable for single-node)")
        else:
            print_error(f"Cluster status: {status}")
        
        print_success(f"Number of nodes: {health['number_of_nodes']}")
        print_success(f"Active shards: {health['active_shards']}")
        
        # Get version
        info = es.info()
        version = info['version']['number']
        print_success(f"Elasticsearch version: {version}")
        
        # List indices
        indices = es.cat.indices(format='json')
        if indices:
            print_success(f"Found {len(indices)} indices")
            for idx in indices:
                print_info(f"  - {idx['index']} ({idx['docs.count']} docs, {idx['store.size']})")
        else:
            print_warning("No indices found (expected for fresh installation)")
        
        es.close()
        return True
        
    except requests.exceptions.ConnectionError as e:
        print_error(f"Elasticsearch connection failed: {str(e)}")
        print_info("Make sure Elasticsearch is running: docker-compose up -d elasticsearch")
        return False
    except Exception as e:
        print_error(f"Elasticsearch verification failed: {str(e)}")
        return False


def verify_qdrant() -> bool:
    """Verify Qdrant connectivity"""
    print_header("Qdrant Verification")
    
    try:
        # Connection parameters
        url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        
        print_info(f"Connecting to Qdrant at {url}...")
        
        # Test connection
        response = requests.get(f"{url}/", timeout=5)
        
        if response.status_code == 200:
            print_success("Qdrant connection established")
            
            info = response.json()
            if 'title' in info:
                print_success(f"Qdrant: {info['title']}")
            if 'version' in info:
                print_success(f"Version: {info['version']}")
        else:
            raise Exception(f"Unexpected status code: {response.status_code}")
        
        # List collections
        collections_response = requests.get(f"{url}/collections", timeout=5)
        if collections_response.status_code == 200:
            collections = collections_response.json()
            if collections.get('result', {}).get('collections'):
                collection_list = collections['result']['collections']
                print_success(f"Found {len(collection_list)} collections")
                for coll in collection_list:
                    print_info(f"  - {coll['name']}")
            else:
                print_warning("No collections found (expected for fresh installation)")
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print_error(f"Qdrant connection failed: {str(e)}")
        print_info("Make sure Qdrant is running: docker-compose up -d qdrant")
        print_warning("Note: If you haven't replaced Weaviate with Qdrant yet, this is expected")
        return False
    except Exception as e:
        print_error(f"Qdrant verification failed: {str(e)}")
        return False


def verify_docker_network() -> bool:
    """Verify Docker network connectivity"""
    print_header("Docker Network Verification")
    
    try:
        # Check if Docker is running
        result = os.system('docker info > nul 2>&1' if os.name == 'nt' else 'docker info > /dev/null 2>&1')
        
        if result == 0:
            print_success("Docker is running")
        else:
            print_error("Docker is not running")
            return False
        
        # Check if docker-compose is available
        result = os.system('docker-compose --version > nul 2>&1' if os.name == 'nt' else 'docker-compose --version > /dev/null 2>&1')
        
        if result == 0:
            print_success("Docker Compose is available")
        else:
            print_warning("Docker Compose is not available (checking docker compose plugin...)")
            result = os.system('docker compose version > nul 2>&1' if os.name == 'nt' else 'docker compose version > /dev/null 2>&1')
            if result == 0:
                print_success("Docker Compose plugin is available")
            else:
                print_error("Docker Compose is not available")
                return False
        
        # Check if ai_discovery_network exists
        if os.name == 'nt':
            result = os.system('docker network inspect ai_discovery_network > nul 2>&1')
        else:
            result = os.system('docker network inspect ai_discovery_network > /dev/null 2>&1')
        
        if result == 0:
            print_success("Docker network 'ai_discovery_network' exists")
        else:
            print_warning("Docker network 'ai_discovery_network' not found")
            print_info("Network will be created when starting services")
        
        return True
        
    except Exception as e:
        print_error(f"Docker verification failed: {str(e)}")
        return False


def main():
    """Main verification routine"""
    print(f"\n{BLUE}{'*' * 80}{RESET}")
    print(f"{BLUE}{'AI Product Discovery Suite - Infrastructure Verification':^80}{RESET}")
    print(f"{BLUE}{'*' * 80}{RESET}\n")
    
    start_time = time.time()
    results = {}
    
    # Run all verifications
    env_valid, env_vars = verify_environment_variables()
    results['environment'] = env_valid
    
    results['postgresql'] = verify_postgresql(env_vars)
    results['redis'] = verify_redis(env_vars)
    results['elasticsearch'] = verify_elasticsearch()
    results['qdrant'] = verify_qdrant()
    results['docker'] = verify_docker_network()
    
    # Summary
    print_header("Verification Summary")
    
    for component, status in results.items():
        if status:
            print_success(f"{component.capitalize()}: OK")
        else:
            print_error(f"{component.capitalize()}: FAILED")
    
    total_checks = len(results)
    passed_checks = sum(1 for v in results.values() if v)
    
    print(f"\n{BLUE}Results: {passed_checks}/{total_checks} checks passed{RESET}")
    
    elapsed_time = time.time() - start_time
    print(f"{BLUE}Time elapsed: {elapsed_time:.2f} seconds{RESET}\n")
    
    # Overall status
    # Note: Qdrant might fail if not yet migrated from Weaviate, so we'll be lenient
    critical_components = ['environment', 'postgresql', 'redis', 'elasticsearch', 'docker']
    critical_passed = all(results.get(comp, False) for comp in critical_components)
    
    if critical_passed:
        print_success("All critical infrastructure components are operational!")
        print_info("Note: Qdrant verification may fail until migration from Weaviate is complete")
        return 0
    else:
        print_error("Some critical infrastructure components failed verification")
        print_info("Please fix the issues above before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())

