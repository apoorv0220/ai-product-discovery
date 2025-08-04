#!/usr/bin/env python3
"""
Comprehensive localhost verification script for AI Product Discovery Suite
"""

import asyncio
import json
import time
import aiohttp
import subprocess
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class TestResult:
    name: str
    success: bool
    response_time: float
    message: str
    data: Optional[Dict] = None

class LocalhostVerifier:
    def __init__(self):
        self.services = {
            "PostgreSQL": {"port": 5432, "check_cmd": "pg_isready -h localhost -p 5432"},
            "Redis": {"port": 6379, "url": "http://localhost:6379"},
            "Elasticsearch": {"port": 9200, "url": "http://localhost:9200"},
            "Weaviate": {"port": 8080, "url": "http://localhost:8080/v1/meta"},
            "RabbitMQ": {"port": 15672, "url": "http://localhost:15672"},
            "Search Service": {"port": 8001, "url": "http://localhost:8001/health/"},
            "Recommendation Service": {"port": 8002, "url": "http://localhost:8002/health/"},
            "Analytics Service": {"port": 8004, "url": "http://localhost:8004/health/"},
            "Shopping Assistant": {"port": 8005, "url": "http://localhost:8005/health/"}
        }
        
        self.api_tests = [
            {
                "name": "Search API - Basic Query",
                "method": "POST",
                "url": "http://localhost:8001/api/v1/search/",
                "data": {
                    "query": "MacBook laptop",
                    "limit": 5,
                    "filters": {}
                },
                "expected_fields": ["results", "total", "query"]
            },
            {
                "name": "Search API - Autocomplete",
                "method": "GET",
                "url": "http://localhost:8001/api/v1/autocomplete/?q=iPhone&limit=5",
                "data": None,
                "expected_fields": ["suggestions"]
            },
            {
                "name": "Recommendations API - User Recommendations",
                "method": "POST",
                "url": "http://localhost:8002/api/v1/recommendations/",
                "data": {
                    "user_id": "1",
                    "context": "home",
                    "limit": 8
                },
                "expected_fields": ["recommendations"]
            },
            {
                "name": "Analytics API - Track Event",
                "method": "POST",
                "url": "http://localhost:8004/api/v1/events/track",
                "data": {
                    "event_type": "product_view",
                    "user_id": "1",
                    "properties": {
                        "product_id": "1",
                        "page": "product_detail"
                    }
                },
                "expected_fields": ["success"]
            },
            {
                "name": "Shopping Assistant API - Chat",
                "method": "POST",
                "url": "http://localhost:8005/api/v1/chat/message",
                "data": {
                    "session_id": "test_session_123",
                    "message": "I need a laptop for programming"
                },
                "expected_fields": ["response", "session_id"]
            }
        ]
        
        self.results: List[TestResult] = []

    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)

    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")

    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")

    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")

    async def check_service_health(self, name: str, config: Dict) -> TestResult:
        """Check if a service is healthy"""
        start_time = time.time()
        
        try:
            if "check_cmd" in config:
                # Use command line check for PostgreSQL
                result = subprocess.run(
                    config["check_cmd"].split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                success = result.returncode == 0
                message = "Connected" if success else f"Failed: {result.stderr}"
            else:
                # Use HTTP check for other services
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(config["url"]) as response:
                        success = response.status < 400
                        message = f"HTTP {response.status}" if success else f"HTTP {response.status}: {await response.text()}"
        
        except Exception as e:
            success = False
            message = f"Connection failed: {str(e)}"
        
        response_time = time.time() - start_time
        return TestResult(name, success, response_time, message)

    async def test_api_endpoint(self, test_config: Dict) -> TestResult:
        """Test an API endpoint"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                if test_config["method"] == "POST":
                    async with session.post(
                        test_config["url"],
                        json=test_config["data"],
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        response_data = await response.json()
                        success = response.status == 200
                elif test_config["method"] == "GET":
                    async with session.get(test_config["url"]) as response:
                        response_data = await response.json()
                        success = response.status == 200
                else:
                    raise ValueError(f"Unsupported method: {test_config['method']}")
                
                # Check expected fields
                if success and test_config["expected_fields"]:
                    missing_fields = [
                        field for field in test_config["expected_fields"]
                        if field not in response_data
                    ]
                    if missing_fields:
                        success = False
                        message = f"Missing fields: {missing_fields}"
                    else:
                        message = "All expected fields present"
                else:
                    message = f"HTTP {response.status}"
                    
        except Exception as e:
            success = False
            message = f"Request failed: {str(e)}"
            response_data = None
        
        response_time = time.time() - start_time
        return TestResult(test_config["name"], success, response_time, message, response_data)

    async def run_infrastructure_checks(self):
        """Check all infrastructure services"""
        self.print_header("INFRASTRUCTURE HEALTH CHECKS")
        
        for service_name, config in self.services.items():
            result = await self.check_service_health(service_name, config)
            self.results.append(result)
            
            if result.success:
                self.print_success(f"{service_name}: {result.message} ({result.response_time:.2f}s)")
            else:
                self.print_error(f"{service_name}: {result.message}")

    async def run_api_tests(self):
        """Run all API endpoint tests"""
        self.print_header("API ENDPOINT TESTS")
        
        for test_config in self.api_tests:
            result = await self.test_api_endpoint(test_config)
            self.results.append(result)
            
            if result.success:
                self.print_success(f"{result.name}: {result.message} ({result.response_time:.2f}s)")
                if result.data and "results" in result.data:
                    self.print_info(f"   → Found {len(result.data['results'])} results")
                elif result.data and "recommendations" in result.data:
                    self.print_info(f"   → Generated {len(result.data['recommendations'])} recommendations")
            else:
                self.print_error(f"{result.name}: {result.message}")

    async def demonstrate_features(self):
        """Demonstrate key features with dummy data"""
        self.print_header("FEATURE DEMONSTRATIONS")
        
        # Demonstrate search functionality
        print("\n🔍 SEARCH FUNCTIONALITY:")
        search_tests = [
            {"query": "MacBook", "description": "Brand search"},
            {"query": "laptop", "description": "Category search"},
            {"query": "gaming console", "description": "Product type search"},
            {"query": "wireless headphones", "description": "Feature search"}
        ]
        
        for test in search_tests:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8001/api/v1/search/",
                        json={"query": test["query"], "limit": 3}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results_count = len(data.get("results", []))
                            self.print_success(f"{test['description']}: '{test['query']}' → {results_count} results")
                        else:
                            self.print_error(f"{test['description']}: Failed to search for '{test['query']}'")
            except Exception as e:
                self.print_error(f"{test['description']}: {str(e)}")
        
        # Demonstrate recommendations
        print("\n🤖 RECOMMENDATION FUNCTIONALITY:")
        rec_tests = [
            {"context": "home", "description": "Homepage recommendations"},
            {"context": "product_detail", "description": "Product page recommendations"},
            {"context": "cart", "description": "Cart recommendations"}
        ]
        
        for test in rec_tests:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8002/api/v1/recommendations/",
                        json={"user_id": "1", "context": test["context"], "limit": 5}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            rec_count = len(data.get("recommendations", []))
                            self.print_success(f"{test['description']}: Generated {rec_count} recommendations")
                        else:
                            self.print_error(f"{test['description']}: Failed to get recommendations")
            except Exception as e:
                self.print_error(f"{test['description']}: {str(e)}")

    def print_summary(self):
        """Print verification summary"""
        self.print_header("VERIFICATION SUMMARY")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n💡 FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"   • {result.name}: {result.message}")
        
        print(f"\n🌐 ACCESS URLS:")
        print(f"   • Search API: http://localhost:8001/api/v1/search/")
        print(f"   • Recommendations API: http://localhost:8002/api/v1/recommendations/")
        print(f"   • Analytics API: http://localhost:8004/api/v1/events/")
        print(f"   • Shopping Assistant API: http://localhost:8005/api/v1/chat/")
        print(f"   • RabbitMQ Management: http://localhost:15672/")
        print(f"   • Elasticsearch: http://localhost:9200/")
        print(f"   • Weaviate: http://localhost:8080/v1/meta")

async def main():
    """Main verification function"""
    print("🚀 AI Product Discovery Suite - Localhost Verification")
    print("="*60)
    print("This script will verify that all services are running correctly")
    print("and demonstrate the key features with dummy data.")
    
    verifier = LocalhostVerifier()
    
    try:
        # Run all checks
        await verifier.run_infrastructure_checks()
        await verifier.run_api_tests()
        await verifier.demonstrate_features()
        
        # Print summary
        verifier.print_summary()
        
        # Final status
        failed_count = sum(1 for r in verifier.results if not r.success)
        if failed_count == 0:
            print(f"\n🎉 ALL TESTS PASSED! The AI Product Discovery Suite is ready to use.")
        else:
            print(f"\n⚠️  {failed_count} tests failed. Please check the services and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())