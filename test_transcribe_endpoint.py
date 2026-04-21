"""
Test the /transcribe-audio endpoint directly
"""
import requests

# Login first to get token
login_response = requests.post(
    "http://localhost:8000/auth/login",
    data={"username": "ramesh@gmail.com", "password": "password123"}
)

print(f"Login status: {login_response.status_code}")
print(f"Login response: {login_response.text}")
token = login_response.json()["access_token"]
print(f"Got token: {token[:50]}...")

# Create a fake audio file for testing
fake_audio = b"RIFF" + b"\x00" * 100  # Minimal RIFF header

# Test the transcription endpoint
print("\nTesting /customer/video-agent/transcribe-audio...")

files = {
    'audio_file': ('recording.webm', fake_audio, 'audio/webm')
}

headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.post(
    "http://localhost:8000/customer/video-agent/transcribe-audio",
    files=files,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
