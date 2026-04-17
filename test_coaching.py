"""
Test coaching session scheduling
"""
import requests
import json

# Test schedule coaching
url = "http://localhost:8000/performance/schedule-coaching"
data = {
    "officer_id": "820654",
    "session_type": "1-on-1",
    "topic": "Customer Empathy Training",
    "scheduled_date": "2026-04-20T10:00:00",
    "notes": "Focus on active listening techniques"
}

print("Testing coaching session scheduling...")
print(f"Request: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response text: {e.response.text}")
