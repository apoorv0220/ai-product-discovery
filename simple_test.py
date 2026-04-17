import requests
import json

# Simple test to check if search works
url = "http://localhost:7099/api/v1/search"
headers = {
    "Authorization": "Bearer ak_live_djl6lrgmy25xzffkawal55j9utbpfkbw",
    "Content-Type": "application/json"
}

data = {
    "query": "shirt",
    "search_type": "keyword",
    "merchant_id": 1
}

print("Testing basic search...")
try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("SUCCESS: Basic search works")
        print(f"Results count: {len(result.get('results', []))}")
        print(f"Merchandising applied: {result.get('metadata', {}).get('merchandising_applied')}")
    else:
        print("FAILED:")
        print(response.text)
except Exception as e:
    print(f"Exception: {e}")
