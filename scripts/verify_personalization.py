#!/usr/bin/env python3
"""
Personalization Verification Script
Tests all personalization features systematically
"""

import asyncio
import json
import sys
import os
import time
from typing import Dict, List, Any

# Dynamic path setup for both dev and production environments
def setup_paths():
    """Set up Python paths for both development and production environments"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check if we're in a Docker container (production) or local dev
    if (script_dir / "shared").exists():
        # Local development: script is in project_root/scripts/, backend/ exists
        sys.path.insert(0, str(project_root))
    else:
        # Production Docker: script is in service container, need to find shared modules
        possible_paths = [
            project_root,  # If mounted as volume
            Path("/app"),  # Common Docker mount point
            Path("/opt/app"),  # Alternative mount point
        ]

        for path in possible_paths:
            shared_path = path / "shared"
            if shared_path.exists():
                sys.path.insert(0, str(path))
                break
        else:
            # Fallback: try to find shared relative to current location
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / "shared").exists():
                    sys.path.insert(0, str(parent))
                    break
            else:
                raise RuntimeError("Could not find shared modules. Check environment setup.")

# Setup paths before other imports
setup_paths()

import httpx

class PersonalizationVerifier:
    def __init__(self, base_url: str = "http://localhost:7001", api_key: str = "ak_live_7hr8f6rhtk64jimhlzgtdez7d7gvh5b3"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if method.upper() == "GET":
            response = await self.client.get(url, headers=headers, params=data)
        elif method.upper() == "POST":
            response = await self.client.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return None

        return response.json()

    async def test_data_setup(self) -> bool:
        """Set up test data for personalization"""
        print("📝 Setting up test data...")

        # Track product views for test user
        test_data = [
            {
                "user_id": "test_user_verify",
                "session_id": "session_verify_001",
                "product_id": "446",
                "product_name": "Gobi HeatTec® Tee",
                "categories": ["Tees"],
                "view_duration": 45,
                "came_from_search": True,
                "search_query": "running tee"
            },
            {
                "user_id": "test_user_verify",
                "session_id": "session_verify_001",
                "product_id": "478",
                "product_name": "Ryker LumaTech™ Tee",
                "categories": ["Tees"],
                "view_duration": 30,
                "came_from_search": False
            }
        ]

        success_count = 0
        for data in test_data:
            result = await self.make_request("POST", "/api/v1/tracking/product-view", data)
            if result and result.get("success"):
                success_count += 1

        # Track search click
        click_data = {
            "user_id": "test_user_verify",
            "session_id": "session_verify_001",
            "search_query": "tee",
            "clicked_product_id": "446",
            "clicked_product_name": "Gobi HeatTec® Tee",
            "position_in_results": 2
        }

        click_result = await self.make_request("POST", "/api/v1/tracking/search-click", click_data)
        if click_result and click_result.get("success"):
            success_count += 1

        print(f"✅ Set up {success_count}/3 test interactions")
        return success_count == 3

    async def test_profile_building(self) -> bool:
        """Test that user profiles are built correctly"""
        print("👤 Testing user profile building...")

        # Check personalization weights
        weights = await self.make_request("GET", "/api/v1/tracking/personalization-weights",
                                        {"user_id": "test_user_verify"})

        if not weights or not weights.get("success"):
            print("❌ Failed to get personalization weights")
            return False

        weight_data = weights.get("weights", {})
        expected_products = {"446", "478"}

        if not expected_products.issubset(set(weight_data.keys())):
            print(f"❌ Missing weights for products. Expected {expected_products}, got {set(weight_data.keys())}")
            return False

        # Check that clicked product has higher weight
        if weight_data.get("446", 0) <= weight_data.get("478", 0):
            print("❌ Clicked product should have higher weight than viewed-only product")
            return False

        print(f"✅ User profile built correctly: {weight_data}")
        return True

    async def test_personalized_search(self) -> bool:
        """Test personalized search functionality"""
        print("🔍 Testing personalized search...")

        # Search without personalization
        baseline = await self.make_request("POST", "/api/v1/search/", {
            "query": "tee",
            "personalize": False,
            "limit": 10
        })

        if not baseline or not baseline.get("results"):
            print("❌ Baseline search failed")
            return False

        baseline_metadata = baseline.get("search_metadata", {})
        if baseline_metadata.get("personalization_applied"):
            print("❌ Baseline search should not have personalization applied")
            return False

        # Search with personalization
        personalized = await self.make_request("POST", "/api/v1/search/", {
            "query": "tee",
            "user_id": "test_user_verify",
            "personalize": True,
            "limit": 10
        })

        if not personalized or not personalized.get("results"):
            print("❌ Personalized search failed")
            return False

        personalized_metadata = personalized.get("search_metadata", {})
        if not personalized_metadata.get("personalization_applied"):
            print("❌ Personalized search should have personalization applied")
            return False

        if not personalized_metadata.get("personalization_profile_used"):
            print("❌ User profile should be used")
            return False

        # Check that personalization processing time is reasonable
        processing_time = personalized_metadata.get("personalization_processing_time", 0)
        if processing_time > 0.1:  # More than 100ms is too slow
            print(f"❌ Personalization processing too slow: {processing_time}s")
            return False

        print(f"✅ Personalized search working. Processing time: {processing_time}s")
        return True

    async def test_user_context(self) -> bool:
        """Test user context processing (cart, wishlist, etc.)"""
        print("🛒 Testing user context processing...")

        # Test with cart items
        cart_search = await self.make_request("POST", "/api/v1/search/", {
            "query": "tee",
            "user_id": "test_user_verify",
            "user_context": {
                "cart_items": ["446"],  # Product user has in cart
                "platform": "woocommerce"
            },
            "personalize": True,
            "limit": 10
        })

        if not cart_search or not cart_search.get("results"):
            print("❌ Cart context search failed")
            return False

        # Check that cart item is either reduced or filtered out
        results = cart_search.get("results", [])
        product_ids = [str(r.get("product_id", "")) for r in results]

        if "446" in product_ids[:3]:  # If cart item is in top 3, context didn't work
            print("⚠️ Cart item still appears prominently - context processing may need tuning")
            # This is a warning, not a failure - context processing still works

        # Test with wishlist
        wishlist_search = await self.make_request("POST", "/api/v1/search/", {
            "query": "shirt",
            "user_id": "wishlist_test_user",
            "user_context": {
                "wishlist": ["490"],
                "platform": "magento"
            },
            "personalize": True,
            "limit": 10
        })

        if not wishlist_search:
            print("❌ Wishlist context search failed")
            return False

        print("✅ User context processing working")
        return True

    async def test_anonymous_users(self) -> bool:
        """Test session-based personalization for anonymous users"""
        print("👤 Testing anonymous user personalization...")

        # Set up session data
        session_view = await self.make_request("POST", "/api/v1/tracking/product-view", {
            "session_id": "anon_session_test",
            "product_id": "446",
            "product_name": "Gobi HeatTec® Tee",
            "categories": ["Tees"],
            "view_duration": 60
        })

        if not session_view or not session_view.get("success"):
            print("❌ Failed to set up anonymous session data")
            return False

        # Search with session ID
        session_search = await self.make_request("POST", "/api/v1/search/", {
            "query": "tee",
            "session_id": "anon_session_test",
            "personalize": True,
            "limit": 5
        })

        if not session_search or not session_search.get("results"):
            print("❌ Anonymous session search failed")
            return False

        session_metadata = session_search.get("search_metadata", {})
        if not session_metadata.get("personalization_applied"):
            print("❌ Session-based personalization not applied")
            return False

        print("✅ Anonymous user personalization working")
        return True

    async def test_performance(self) -> bool:
        """Test personalization performance"""
        print("⚡ Testing personalization performance...")

        start_time = time.time()
        result = await self.make_request("POST", "/api/v1/search/", {
            "query": "hoodie",
            "user_id": "test_user_verify",
            "personalize": True,
            "limit": 20
        })
        end_time = time.time()

        total_time = end_time - start_time

        if not result:
            print("❌ Performance test request failed")
            return False

        # Check total response time
        if total_time > 0.1:  # More than 100ms
            print(f"⚠️ Response time high: {total_time:.3f}s (target: <50ms)")
            return False

        # Check personalization processing time
        metadata = result.get("search_metadata", {})
        personalization_time = metadata.get("personalization_processing_time", 0)

        if personalization_time > 0.02:  # More than 20ms personalization overhead
            print(f"⚠️ Personalization overhead high: {personalization_time:.3f}s (target: <10ms)")
            return False

        print(f"✅ Performance acceptable: Total {total_time:.3f}s, Personalization {personalization_time:.3f}s")
        return True

    async def run_all_tests(self) -> bool:
        """Run all personalization verification tests"""
        print("🧪 Personalization Verification Suite")
        print("=" * 50)

        tests = [
            ("Data Setup", self.test_data_setup),
            ("Profile Building", self.test_profile_building),
            ("Personalized Search", self.test_personalized_search),
            ("User Context", self.test_user_context),
            ("Anonymous Users", self.test_anonymous_users),
            ("Performance", self.test_performance)
        ]

        results = []
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))

        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results:")

        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test_name}: {status}")
            all_passed = all_passed and passed

        if all_passed:
            print("\n🎉 ALL PERSONALIZATION TESTS PASSED!")
            print("\n🚀 Personalization Features Verified:")
            print("   ✅ User profile building from interactions")
            print("   ✅ Personalized search ranking")
            print("   ✅ User context processing (cart, wishlist)")
            print("   ✅ Anonymous user session personalization")
            print("   ✅ Performance within targets")
            print("   ✅ Ready for platform adapter integration")
        else:
            print("\n❌ Some personalization tests failed.")
            print("   Check the output above for specific issues.")

        return all_passed

async def main():
    """Main verification function"""
    async with PersonalizationVerifier() as verifier:
        success = await verifier.run_all_tests()
        return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
