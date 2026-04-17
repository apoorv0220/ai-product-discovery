import json
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from shared.config.redis import json_serial

def verify_fix():
    event_data = {
        "event_id": "test-id",
        "timestamp": datetime.utcnow(),
        "properties": {"foo": "bar"}
    }
    
    try:
        json_str = json.dumps(event_data, default=json_serial)
        print("SUCCESS: Serialized event_data with datetime.")
        print("JSON:", json_str)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    verify_fix()
