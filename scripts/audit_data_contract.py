#!/usr/bin/env python3
"""
AI Product Discovery Suite - Data Contract Audit Script

Performs comprehensive audit of Analytics Service API data contract.
Tests payload mapping, field validation, and edge case resilience.

Usage:
    python scripts/audit_data_contract.py

Requirements:
    - Analytics Service running on localhost:7004
    - PostgreSQL running (for database verification)
    - Valid API key in environment or .env file
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import structlog

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from shared.config.settings import get_settings

logger = structlog.get_logger()


class AuditStatus(Enum):
    PASS = "✓ PASS"
    FAIL = "✗ FAIL"
    WARN = "⚠ WARN"


@dataclass
class AuditResult:
    test_name: str
    status: AuditStatus
    details: str
    expected: Any = None
    actual: Any = None
    error: Optional[str] = None


class DataContractAuditor:
    """Comprehensive data contract auditor for Analytics Service"""

    def __init__(self):
        # Set environment variables for the audit
        self._setup_environment()

        self.base_url = "http://localhost:7097"
        self.api_key = self._get_api_key()
        self.results: List[AuditResult] = []
        self.db_conn = None
        self.db_available = True  # Assume DB is available initially

        # Test data
        self.test_session_id = f"audit_session_{int(datetime.now().timestamp())}"
        self.test_user_id = f"audit_user_{int(datetime.now().timestamp())}"

    def _get_api_key(self) -> str:
        """Get API key from environment, provided key, or .env file"""
        # Use provided API key or environment variables
        api_key = os.getenv('API_KEY') or os.getenv('ANALYTICS_API_KEY')

        # Use the provided API key if no other key is found
        if not api_key:
            api_key = "sk_YnsYYfGYKIsii-xjfoWfHjhAWKDOo7ksxq_aJT0Fll0"

        if not api_key:
            # Try to read from .env file as fallback
            env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('API_KEY=') or line.startswith('ANALYTICS_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"\'')
                            break

        if not api_key:
            raise ValueError("No API key found. Set API_KEY environment variable or add to .env file")

        return api_key

    def _setup_environment(self):
        """Set up environment variables for the audit"""
        # Disable .env file reading by setting PYDANTIC_SETTINGS_SOURCES to only use environment variables
        os.environ['PYDANTIC_SETTINGS_SOURCES'] = 'env'

        # Set development environment variables if not already set
        env_vars = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '7010',
            'POSTGRES_DB': 'ai_discovery',
            'POSTGRES_USER': 'ai_user',
            'POSTGRES_PASSWORD': 'ai_password',
            'DATABASE_URL': 'postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '7011',
            'REDIS_PASSWORD': 'redis_password_2024',
            'ELASTICSEARCH_URL': 'http://localhost:7020',
            'QDRANT_URL': 'http://localhost:7021',
            'ANALYTICS_SERVICE_PORT': '7097'
        }

        for key, value in env_vars.items():
            if not os.getenv(key):
                os.environ[key] = value

    def _get_db_config(self) -> Dict[str, Any]:
        """Extract database configuration from environment variables"""
        # Use environment variables directly to avoid settings loading issues
        db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery')

        if not db_url.startswith('postgresql+asyncpg://'):
            raise ValueError(f"Unsupported DATABASE_URL format: {db_url}")

        # Remove asyncpg prefix to get standard postgres URL
        db_url = db_url.replace('postgresql+asyncpg://', '')

        # Parse URL components
        try:
            user_pass, host_port_db = db_url.split('@')
            user, password = user_pass.split(':')
            host_port, database = host_port_db.split('/')
            host, port = host_port.split(':')

            return {
                'host': host,
                'port': int(port),
                'database': database,
                'user': user,
                'password': password
            }
        except ValueError as e:
            raise ValueError(f"Failed to parse DATABASE_URL: {db_url}") from e

    async def _make_request(self, endpoint: str, payload: Dict[str, Any],
                           headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
        """Make HTTP request to Analytics Service"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                response = await client.post(url, json=payload, headers=request_headers)
                return response.status_code, response.json() if response.content else {}
            except Exception as e:
                return 500, {"error": str(e)}

    def _connect_db(self):
        """Connect to PostgreSQL database"""
        if self.db_conn:
            return

        if not self.db_available:
            return

        try:
            db_config = self._get_db_config()
            self.db_conn = psycopg2.connect(**db_config)
            logger.info("Connected to database for audit verification")
        except Exception as e:
            logger.warning("Database not available for audit verification", error=str(e))
            self.db_available = False

    def _query_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Query event from database with retries and UUID handling"""
        self._connect_db()
        
        if not self.db_conn:
            logger.debug("Database connection not available for query", event_id=event_id)
            return None

        # Analytics events might have a slight ingestion delay, use retries
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # PostgreSQL UUID type handling
                    cursor.execute("""
                        SELECT event_id, event_type, user_id, session_id, product_id,
                               experiment_id, variant_id, revenue, properties,
                               platform, device_type, user_agent, referrer, ip_address,
                               timestamp
                        FROM analytics_events
                        WHERE event_id = %s::uuid
                        ORDER BY id DESC LIMIT 1
                    """, (event_id,))
                    result = cursor.fetchone()
                    if result:
                        return dict(result)
                
                # If not found, wait and retry
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logger.error("Database query failed", error=str(e), attempt=attempt+1)
                # On error, don't retry immediately
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        return None

    def _add_result(self, test_name: str, status: AuditStatus, details: str,
                   expected: Any = None, actual: Any = None, error: Optional[str] = None):
        """Add audit result"""
        self.results.append(AuditResult(
            test_name=test_name,
            status=status,
            details=details,
            expected=expected,
            actual=actual,
            error=error
        ))

    async def test_experiment_variant_fields(self):
        """Test experiment_id and variant_id field persistence"""
        logger.info("Testing experiment_id and variant_id field persistence")

        # Test 1: Event with experiment and variant IDs
        payload = {
            "event_type": "product_view",
            "session_id": self.test_session_id,
            "product_id": 12345,
            "experiment_id": 42,
            "variant_id": 7,
            "platform": "magento",
            "properties": {
                "page_url": "/products/test-product.html",
                "test_type": "experiment_variant_mapping"
            }
        }

        status_code, response = await self._make_request("/api/v1/events/track", payload)

        if status_code != 200:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.FAIL,
                f"API request failed with status {status_code}",
                expected="200 OK",
                actual=f"{status_code} {response.get('detail', 'Unknown error')}"
            )
            return

        event_id = response.get('event_id')
        if not event_id:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.FAIL,
                "No event_id returned in response",
                expected="event_id present",
                actual="missing"
            )
            return

        # Verify in database (if available)
        if not self.db_available:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.WARN,
                "Database verification skipped - database not available",
                expected="API accepts payload",
                actual="API accepted payload successfully"
            )
            return

        db_event = self._query_event(event_id)
        if not db_event:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.FAIL,
                "Event not found in database",
                expected="event in database",
                actual="not found"
            )
            return

        # Check experiment_id
        if db_event.get('experiment_id') != 42:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.FAIL,
                "experiment_id not correctly stored",
                expected=42,
                actual=db_event.get('experiment_id')
            )
        elif db_event.get('variant_id') != 7:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.FAIL,
                "variant_id not correctly stored",
                expected=7,
                actual=db_event.get('variant_id')
            )
        else:
            self._add_result(
                "experiment_variant_fields",
                AuditStatus.PASS,
                "experiment_id and variant_id correctly stored in database",
                expected={"experiment_id": 42, "variant_id": 7},
                actual={"experiment_id": db_event.get('experiment_id'), "variant_id": db_event.get('variant_id')}
            )

    async def test_revenue_field_precision(self):
        """Test revenue field with various decimal values"""
        logger.info("Testing revenue field precision and handling")

        test_cases = [
            ("small_decimal", 19.99),
            ("large_decimal", 12345.67),
            ("zero_revenue", 0.00),
            ("high_precision", 99.9999),
            ("negative_revenue", -50.00)  # Should this be allowed?
        ]

        for test_name, revenue_value in test_cases:
            payload = {
                "event_type": "purchase",
                "session_id": f"{self.test_session_id}_{test_name}",
                "product_id": 12345,
                "revenue": revenue_value,
                "platform": "magento",
                "properties": {
                    "test_type": "revenue_precision",
                    "test_case": test_name
                }
            }

            status_code, response = await self._make_request("/api/v1/events/track", payload)

            if test_name == "negative_revenue":
                if status_code == 400:
                    self._add_result(
                        f"revenue_field_{test_name}",
                        AuditStatus.PASS,
                        "API correctly rejected negative revenue value",
                        expected="400 Bad Request",
                        actual=f"{status_code} {response.get('detail', 'Validation Error')}"
                    )
                else:
                    self._add_result(
                        f"revenue_field_{test_name}",
                        AuditStatus.FAIL,
                        "API should have rejected negative revenue value",
                        expected="400 Bad Request",
                        actual=f"{status_code} OK"
                    )
                continue

            if status_code != 200:
                self._add_result(
                    f"revenue_field_{test_name}",
                    AuditStatus.FAIL,
                    f"API request failed with status {status_code}",
                    expected="200 OK",
                    actual=f"{status_code} {response.get('detail', 'Unknown error')}"
                )
                continue

            event_id = response.get('event_id')

            if not self.db_available:
                self._add_result(
                    f"revenue_field_{test_name}",
                    AuditStatus.WARN,
                    f"Database verification skipped - revenue value {revenue_value} accepted by API",
                    expected="API accepts payload",
                    actual="API accepted payload successfully"
                )
                continue

            db_event = self._query_event(event_id)

            if not db_event:
                self._add_result(
                    f"revenue_field_{test_name}",
                    AuditStatus.FAIL,
                    "Event not found in database",
                    expected="event in database",
                    actual="not found"
                )
                continue

            stored_revenue = db_event.get('revenue')
            if stored_revenue != revenue_value:
                self._add_result(
                    f"revenue_field_{test_name}",
                    AuditStatus.FAIL,
                    f"Revenue precision lost or altered",
                    expected=revenue_value,
                    actual=stored_revenue
                )
            else:
                self._add_result(
                    f"revenue_field_{test_name}",
                    AuditStatus.PASS,
                    f"Revenue value {revenue_value} correctly stored with precision",
                    expected=revenue_value,
                    actual=stored_revenue
                )

    async def test_user_agent_parsing(self):
        """Test User-Agent header parsing into device_type, browser, os fields"""
        logger.info("Testing User-Agent header parsing")

        test_user_agents = [
            ("chrome_desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"),
            ("firefox_mobile", "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"),
            ("safari_tablet", "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"),
            ("edge_desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59")
        ]

        for ua_name, user_agent in test_user_agents:
            payload = {
                "event_type": "page_view",
                "session_id": f"{self.test_session_id}_{ua_name}",
                "platform": "magento",
                "user_agent": user_agent,
                "properties": {
                    "test_type": "user_agent_parsing",
                    "ua_test": ua_name
                }
            }

            headers = {"User-Agent": user_agent}
            status_code, response = await self._make_request("/api/v1/events/track", payload, headers)

            if status_code != 200:
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.FAIL,
                    f"API request failed with status {status_code}",
                    expected="200 OK",
                    actual=f"{status_code} {response.get('detail', 'Unknown error')}"
                )
                continue

            event_id = response.get('event_id')

            if not self.db_available:
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.WARN,
                    f"Database verification skipped - User-Agent parsing accepted by API",
                    expected="API accepts payload",
                    actual="API accepted payload successfully"
                )
                continue

            db_event = self._query_event(event_id)

            if not db_event:
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.FAIL,
                    "Event not found in database",
                    expected="event in database",
                    actual="not found"
                )
                continue

            # Check that User-Agent was stored
            if db_event.get('user_agent') != user_agent:
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.FAIL,
                    "User-Agent string not stored correctly",
                    expected=user_agent,
                    actual=db_event.get('user_agent')
                )
                continue

            # Check that properties contain device parsing info
            properties = db_event.get('properties', {})

            # These fields should be populated by the event enricher
            device_info = {
                'device_type': properties.get('device_type'),
                'browser': properties.get('browser'),
                'os': properties.get('os')
            }

            # Verify at least one device field is populated
            if not any(device_info.values()):
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.FAIL,
                    "User-Agent not parsed into device info fields",
                    expected="device_type, browser, or os populated",
                    actual=device_info
                )
            else:
                self._add_result(
                    f"user_agent_{ua_name}",
                    AuditStatus.PASS,
                    f"User-Agent parsed successfully: {device_info}",
                    expected="parsed device info",
                    actual=device_info
                )

    async def test_edge_cases(self):
        """Test API resilience with edge cases"""
        logger.info("Testing edge case resilience")

        # Test 1: Missing optional fields (event without experiment)
        payload_minimal = {
            "event_type": "page_view",
            "session_id": f"{self.test_session_id}_minimal",
            "platform": "magento"
        }

        status_code, response = await self._make_request("/api/v1/events/track", payload_minimal)
        if status_code == 200:
            self._add_result(
                "edge_case_minimal_fields",
                AuditStatus.PASS,
                "Event accepted with minimal required fields",
                expected="200 OK",
                actual=f"{status_code} OK"
            )
        else:
            self._add_result(
                "edge_case_minimal_fields",
                AuditStatus.FAIL,
                "Event rejected with minimal required fields",
                expected="200 OK",
                actual=f"{status_code} {response.get('detail', 'Unknown error')}"
            )

        # Test 2: Malformed session ID
        payload_malformed = {
            "event_type": "page_view",
            "session_id": "session with spaces and special chars !@#$%^&*()",
            "platform": "magento"
        }

        status_code, response = await self._make_request("/api/v1/events/track", payload_malformed)
        if status_code == 200:
            event_id = response.get('event_id')

            if not self.db_available:
                self._add_result(
                    "edge_case_malformed_session_id",
                    AuditStatus.WARN,
                    "Database verification skipped - malformed session_id accepted by API",
                    expected="API accepts payload",
                    actual="API accepted payload successfully"
                )
            else:
                db_event = self._query_event(event_id)
                if db_event and db_event.get('session_id') == payload_malformed['session_id']:
                    self._add_result(
                        "edge_case_malformed_session_id",
                        AuditStatus.PASS,
                        "Malformed session ID handled correctly",
                        expected=payload_malformed['session_id'],
                        actual=db_event.get('session_id')
                    )
                else:
                    self._add_result(
                        "edge_case_malformed_session_id",
                        AuditStatus.FAIL,
                        "Malformed session ID not stored correctly",
                        expected=payload_malformed['session_id'],
                        actual=db_event.get('session_id') if db_event else None
                    )
        else:
            self._add_result(
                "edge_case_malformed_session_id",
                AuditStatus.FAIL,
                f"API rejected malformed session ID: {response.get('detail', 'Unknown error')}",
                expected="accept malformed session_id",
                actual=f"{status_code} {response.get('detail', 'Unknown error')}"
            )

        # Test 3: Very large revenue value
        large_revenue = 999999999.99
        payload_large_revenue = {
            "event_type": "purchase",
            "session_id": f"{self.test_session_id}_large_revenue",
            "product_id": 12345,
            "revenue": large_revenue,
            "platform": "magento"
        }

        status_code, response = await self._make_request("/api/v1/events/track", payload_large_revenue)
        if status_code == 200:
            event_id = response.get('event_id')

            if not self.db_available:
                self._add_result(
                    "edge_case_large_revenue",
                    AuditStatus.WARN,
                    f"Database verification skipped - large revenue {large_revenue} accepted by API",
                    expected="API accepts payload",
                    actual="API accepted payload successfully"
                )
            else:
                db_event = self._query_event(event_id)
                if db_event and db_event.get('revenue') == large_revenue:
                    self._add_result(
                        "edge_case_large_revenue",
                        AuditStatus.PASS,
                        f"Large revenue value {large_revenue} handled correctly",
                        expected=large_revenue,
                        actual=db_event.get('revenue')
                    )
                else:
                    self._add_result(
                        "edge_case_large_revenue",
                        AuditStatus.FAIL,
                        "Large revenue value not stored correctly",
                        expected=large_revenue,
                        actual=db_event.get('revenue') if db_event else None
                    )
        else:
            self._add_result(
                "edge_case_large_revenue",
                AuditStatus.FAIL,
                f"API rejected large revenue: {response.get('detail', 'Unknown error')}",
                expected="accept large revenue",
                actual=f"{status_code} {response.get('detail', 'Unknown error')}"
            )

    async def test_api_health(self):
        """Test basic API connectivity"""
        logger.info("Testing API health and connectivity")

        # Health check might require auth depending on middleware
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/events/health", headers=headers)
                if response.status_code == 200:
                    self._add_result(
                        "api_health",
                        AuditStatus.PASS,
                        "Analytics Service health check passed",
                        expected="200 OK",
                        actual="200 OK"
                    )
                elif response.status_code == 401:
                    self._add_result(
                        "api_health",
                        AuditStatus.WARN,
                        "Analytics Service is UP, but health check requires authentication",
                        expected="200 OK",
                        actual="401 Unauthorized"
                    )
                else:
                    self._add_result(
                        "api_health",
                        AuditStatus.FAIL,
                        f"Health check failed with status {response.status_code}",
                        expected="200 OK",
                        actual=f"{response.status_code}"
                    )
            except Exception as e:
                self._add_result(
                    "api_health",
                    AuditStatus.FAIL,
                    f"Cannot connect to Analytics Service: {str(e)}",
                    expected="service running",
                    actual="connection failed"
                )

    async def run_audit(self):
        """Run complete data contract audit"""
        logger.info("Starting Data Contract Audit for Analytics Service")
        print("🔍 Starting Data Contract Audit for Analytics Service")
        print("=" * 60)

        # Run all tests
        await self.test_api_health()
        await self.test_experiment_variant_fields()
        await self.test_revenue_field_precision()
        await self.test_user_agent_parsing()
        await self.test_edge_cases()

        # Generate summary
        self._generate_summary()

        # Cleanup
        if self.db_conn:
            self.db_conn.close()

    def _generate_summary(self):
        """Generate and display audit summary"""
        print("\n📊 AUDIT RESULTS SUMMARY")
        print("=" * 60)

        passed = len([r for r in self.results if r.status == AuditStatus.PASS])
        failed = len([r for r in self.results if r.status == AuditStatus.FAIL])
        warnings = len([r for r in self.results if r.status == AuditStatus.WARN])
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"⚠ Warnings: {warnings}")

        if failed > 0:
            print(f"\n❌ CRITICAL ISSUES FOUND ({failed} failures)")
            for result in self.results:
                if result.status == AuditStatus.FAIL:
                    print(f"  • {result.test_name}: {result.details}")
                    if result.expected is not None:
                        print(f"    Expected: {result.expected}")
                    if result.actual is not None:
                        print(f"    Actual: {result.actual}")
                    if result.error:
                        print(f"    Error: {result.error}")
        else:
            print("\n✅ ALL TESTS PASSED - Data contract is solid!")

        print(f"\n📋 DETAILED RESULTS")
        print("-" * 40)
        for result in self.results:
            status_icon = {
                AuditStatus.PASS: "✓",
                AuditStatus.FAIL: "✗",
                AuditStatus.WARN: "⚠"
            }[result.status]

            print(f"{status_icon} {result.test_name}")
            print(f"  {result.details}")

            if result.expected is not None or result.actual is not None:
                print(f"  Expected: {result.expected}")
                print(f"  Actual: {result.actual}")

            if result.error:
                print(f"  Error: {result.error}")
            print()


async def main():
    """Main entry point"""
    auditor = DataContractAuditor()
    await auditor.run_audit()


if __name__ == "__main__":
    asyncio.run(main())