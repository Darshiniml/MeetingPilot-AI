import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
from urllib.request import Request, urlopen
from app.core.security import create_access_token

def get_meetings_for_user(user_id):
    token = create_access_token(subject=user_id)
    req = Request(
        "http://127.0.0.1:8000/meetings?limit=100",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"\n=== Meetings for User ID {user_id} ===")
            print(f"Total: {data.get('total')}")
            for item in data.get("items", []):
                print(f"ID: {item['id']}, Title: {item['title']}, Count: {item['transcript_count']}, Status: {item['meeting_status']}, Summary Available: {item['summary_available']}")
    except Exception as e:
        print(f"Error fetching for User ID {user_id}: {e}")

print("Fetching /meetings for User 1 and User 2:")
get_meetings_for_user(1)
get_meetings_for_user(2)
