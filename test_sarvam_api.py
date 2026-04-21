"""
Test script to verify Sarvam AI STT API
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

print(f"API Key loaded: {SARVAM_API_KEY[:20]}..." if SARVAM_API_KEY else "No API key found")

# Create a small test audio (just empty bytes for testing API format)
test_audio = b"test audio data"

print(f"Test audio size: {len(test_audio)} bytes")

try:
    print("Calling Sarvam API with multipart/form-data...")
    
    files = {
        'file': ('test.webm', test_audio, 'audio/webm')
    }
    
    data = {
        'language_code': 'auto',
        'model': 'saaras:v1'
    }
    
    response = requests.post(
        "https://api.sarvam.ai/speech-to-text",
        headers={
            "Authorization": f"Bearer {SARVAM_API_KEY}"
        },
        files=files,
        data=data,
        timeout=30
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
