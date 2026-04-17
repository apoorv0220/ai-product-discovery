import asyncio
import httpx
import random
import time
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:7097"
API_KEY = "sk_YnsYYfGYKIsii-xjfoWfHjhAWKDOo7ksxq_aJT0Fll0"
TOTAL_EVENTS = 500
DURATION_SECONDS = 600  # 10 minutes
MERCHANT_ID = 1

# Headers
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Sample data
SEARCH_QUERIES = ["hoodie", "running shoes", "t-shirt", "backpack", "yoga mat", "water bottle", "jacket", "shorts"]
PRODUCT_NAMES = {
    101: "Hero Hoodie",
    102: "Swift Running Shoes",
    103: "Classic T-Shirt",
    104: "Adventure Backpack",
    105: "Zen Yoga Mat",
    106: "Hydro Water Bottle",
    107: "Peak Performance Jacket",
    108: "Active Shorts"
}
PRODUCT_IDS = list(PRODUCT_NAMES.keys())

async def track_search_query(client, session_id, user_id):
    query = random.choice(SEARCH_QUERIES)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "query": query,
        "results_count": random.randint(5, 50),
        "platform": "magento",
        "device_type": random.choice(["desktop", "mobile", "tablet"]),
        "ip_address": "127.0.0.1"
    }
    try:
        response = await client.post(f"{BASE_URL}/api/v1/tracking/search-query", json=payload)
        return response.status_code
    except Exception as e:
        return str(e)

async def track_search_click(client, session_id, user_id):
    query = random.choice(SEARCH_QUERIES)
    product_id = random.choice(PRODUCT_IDS)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "search_query": query,
        "clicked_product_id": product_id,
        "clicked_product_name": PRODUCT_NAMES[product_id],
        "position_in_results": random.randint(1, 10),
        "platform": "magento",
        "device_type": random.choice(["desktop", "mobile", "tablet"]),
        "ip_address": "127.0.0.1"
    }
    try:
        response = await client.post(f"{BASE_URL}/api/v1/tracking/search-click", json=payload)
        return response.status_code
    except Exception as e:
        return str(e)

async def track_product_view(client, session_id, user_id):
    product_id = random.choice(PRODUCT_IDS)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "product_id": product_id,
        "product_name": PRODUCT_NAMES[product_id],
        "product_sku": f"SKU-{product_id}",
        "categories": ["Category A", "Category B"],
        "platform": "magento",
        "device_type": random.choice(["desktop", "mobile", "tablet"]),
        "ip_address": "127.0.0.1",
        "view_duration": random.randint(5, 120)
    }
    try:
        response = await client.post(f"{BASE_URL}/api/v1/tracking/product-view", json=payload)
        return response.status_code
    except Exception as e:
        return str(e)

async def simulate_load():
    print(f"Starting load simulation: {TOTAL_EVENTS} events over {DURATION_SECONDS}s")
    print(f"Targeting: {BASE_URL}")
    
    interval = DURATION_SECONDS / TOTAL_EVENTS
    stats = {"success": 0, "error": 0, "status_codes": {}}
    
    # Active sessions to simulate realistic behavior
    sessions = [(f"sess_{uuid.uuid4().hex[:8]}", f"user_{random.randint(1000, 9999)}") for _ in range(20)]

    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        for i in range(TOTAL_EVENTS):
            session_id, user_id = random.choice(sessions)
            
            # Choose event type based on mix: 20% search, 30% click, 50% view
            rand = random.random()
            if rand < 0.2:
                status = await track_search_query(client, session_id, user_id)
            elif rand < 0.5:
                status = await track_search_click(client, session_id, user_id)
            else:
                status = await track_product_view(client, session_id, user_id)
            
            if status == 200 or status == 201:
                stats["success"] += 1
            else:
                stats["error"] += 1
            
            stats["status_codes"][status] = stats["status_codes"].get(status, 0) + 1
            
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{TOTAL_EVENTS} events fired...")
            
            # Sleep to maintain the rate
            await asyncio.sleep(interval)

    print("\nSimulation Complete!")
    print(f"Total Events: {TOTAL_EVENTS}")
    print(f"Successes: {stats['success']}")
    print(f"Errors: {stats['error']}")
    print(f"Status Codes: {stats['status_codes']}")

if __name__ == "__main__":
    asyncio.run(simulate_load())
