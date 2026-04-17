#!/usr/bin/env python3
"""
Personalized Search Engine Debug Script
"""

import requests
import json
import time

def test_personalization():
    print("🔍 Personalized Search Engine Debug")
    print("=" * 50)
    
    base_url = "http://localhost:7001"
    session_id = f"debug_{int(time.time())}"
    
    print(f"Test Session: {session_id}")
    print()
    
    # Step 1: Initial search
    print("1️⃣  Initial Search (No Personalization)")
    response = requests.post(f"{base_url}/api/v1/autocomplete/", 
                           json={"q": "Hoodie", "limit": 5, "session_id": session_id})
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Success")
        for i, item in enumerate(data.get('suggestions', [])[:3]):
            print(f"   {i+1}. {item.get('suggestion', 'N/A')} (ID: {item.get('id', 'N/A')})")
        original_first = data.get('suggestions', [{}])[0].get('suggestion', 'N/A')
        original_first_id = data.get('suggestions', [{}])[0].get('id', 'N/A')
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return
    
    print()
    
    # Step 2: Check initial weights
    print("2️⃣  Check Initial Weights")
    response = requests.get(f"{base_url}/api/v1/tracking/personalization-weights", 
                           params={"session_id": session_id})
    
    if response.status_code == 200:
        weights = response.json()
        print(f"   Weights found: {weights.get('total', 0)}")
        if weights.get('weights'):
            print(f"   Weights: {weights['weights']}")
        else:
            print("   No weights (as expected)")
    
    print()
    
    # Step 3: Track a product view
    print("3️⃣  Track Product View (Eos V-Neck Hoodie)")
    track_data = {
        "session_id": session_id,
        "product_id": "1194",
        "product_name": "Eos V-Neck Hoodie"
    }
    
    response = requests.post(f"{base_url}/api/v1/tracking/product-view", json=track_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ {result.get('message', 'Success')}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return
    
    print()
    
    # Step 4: Check weights after tracking
    print("4️⃣  Check Weights After Tracking")
    response = requests.get(f"{base_url}/api/v1/tracking/personalization-weights", 
                           params={"session_id": session_id})
    
    if response.status_code == 200:
        weights = response.json()
        print(f"   Weights found: {weights.get('total', 0)}")
        if weights.get('weights'):
            print(f"   Weights: {weights['weights']}")
            eos_weight = weights['weights'].get('1194', 'N/A')
            print(f"   Eos V-Neck Hoodie weight: {eos_weight}")
    
    print()
    
    # Step 5: Personalized search
    print("5️⃣  Personalized Search")
    response = requests.post(f"{base_url}/api/v1/autocomplete/", 
                           json={"q": "Hoodie", "limit": 5, "session_id": session_id})
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Success")
        for i, item in enumerate(data.get('suggestions', [])[:3]):
            weight = item.get('personalization_weight', 'N/A')
            score = item.get('final_score', 'N/A')
            print(f"   {i+1}. {item.get('suggestion', 'N/A')} (ID: {item.get('id', 'N/A')}) - Weight: {weight}, Score: {score}")
        
        new_first = data.get('suggestions', [{}])[0].get('suggestion', 'N/A')
        new_first_id = data.get('suggestions', [{}])[0].get('id', 'N/A')
        
        print()
        print("📊 RESULTS:")
        print(f"   Original first: {original_first} (ID: {original_first_id})")
        print(f"   New first:      {new_first} (ID: {new_first_id})")
        
        if new_first_id == "1194":
            print("   🎉 PERSONALIZATION WORKING! Eos V-Neck Hoodie moved to #1!")
        elif new_first != original_first:
            print("   🔄 Order changed - personalization may be working")
        else:
            print("   ⚠️  No personalization detected")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    print()
    print("🔍 To check logs:")
    print("   docker logs ai_discovery_search --tail 50")
    print()
    print("🔍 To monitor logs in real-time:")
    print("   docker logs ai_discovery_search -f")

if __name__ == "__main__":
    test_personalization()
