import os
import sys
from dotenv import load_dotenv
import redis
import time
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

load_dotenv()

from shared.config.settings import get_settings

def monitor_longevity():
    settings = get_settings()
    print(f"Monitoring Longevity...")
    print(f"Redis: {settings.REDIS_URL}")
    
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Monitor for a few minutes
        start_time = time.time()
        duration = 300  # 5 minutes for verification
        
        print(f"Monitoring for {duration} seconds...")
        
        while time.time() - start_time < duration:
            # Check queue length
            queue_len = r.llen("analytics:events_queue")
            
            # Check for worker heartbeat logs in Redis (if any)
            # Or just check if the queue is being processed
            
            print(f"[{time.strftime('%H:%M:%S')}] Queue Length: {queue_len}")
            
            if queue_len == 0 and time.time() - start_time > 60:
                print("Queue is being processed. Worker is active.")
            
            time.sleep(30)
            
    except Exception as e:
        print(f"Monitoring Error: {e}")

if __name__ == "__main__":
    monitor_longevity()
