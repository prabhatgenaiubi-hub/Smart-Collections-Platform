# Tests

This folder contains test scripts for the Smart Collections Platform.

## Test Files

- **test_sarvam_api.py** - Tests Sarvam AI Speech-to-Text API directly
- **test_sarvam_sdk.py** - Tests Sarvam AI SDK integration
- **test_transcribe_endpoint.py** - Tests the /transcribe-audio endpoint
- **test_dashboard.py** - Tests dashboard functionality
- **test_coaching.py** - Tests coaching features

## Running Tests

```bash
# Run a specific test
python tests/test_sarvam_api.py

# Run from root directory
cd "d:\Prabhat\GenAI Prabhat\Smart-Collections-Platform"
python tests/test_sarvam_api.py
```

## Notes

- These are development/debugging test scripts, not unit tests
- Make sure backend server is running before testing API endpoints
- Ensure SARVAM_API_KEY is configured in .env file
