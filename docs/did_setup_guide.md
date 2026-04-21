# D-ID Lip-Sync Video Integration Guide

## 🎯 Overview

D-ID integration provides realistic lip-synced video avatars that speak loan information to customers in their preferred language with perfect lip synchronization.

## 📋 Prerequisites

1. D-ID Account (Free tier available)
2. D-ID API Key
3. Backend server with internet access

## 🔧 Setup Instructions

### Step 1: Create D-ID Account

1. Go to https://studio.d-id.com/
2. Click **"Sign Up"** (top right)
3. Create account with email or Google
4. Verify your email

### Step 2: Get API Key

1. Login to D-ID Studio
2. Click your profile icon (top right)
3. Select **"API Keys"**
4. Click **"Create API Key"**
5. Name it: `Smart-Collections-Platform`
6. Copy the API key (starts with `Basic ...`)

### Step 3: Configure Backend

#### Option A: Environment Variable (Recommended)

**Windows PowerShell:**
```powershell
# Set environment variable for current session
$env:DID_API_KEY="your-d-id-api-key-here"

# Or permanently (system-wide)
[System.Environment]::SetEnvironmentVariable('DID_API_KEY', 'your-d-id-api-key-here', 'User')
```

**Linux/Mac:**
```bash
export DID_API_KEY="your-d-id-api-key-here"

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export DID_API_KEY="your-d-id-api-key-here"' >> ~/.bashrc
```

#### Option B: .env File

Create `.env` file in project root:
```env
DID_API_KEY=your-d-id-api-key-here
```

Install python-dotenv:
```bash
pip install python-dotenv
```

Update `backend/main.py`:
```python
from dotenv import load_dotenv
load_dotenv()  # Add at the top
```

### Step 4: Restart Backend

```powershell
# Stop current server (Ctrl+C)
# Start with environment variable loaded
uvicorn backend.main:app --reload
```

### Step 5: Test Integration

1. Login as customer (CUST001)
2. Click **"📹 Ask AI Agent"** on any loan card
3. Ask: "What is my next EMI?"
4. Wait 10-20 seconds for video generation
5. Watch the realistic avatar speak with lip-sync! 🎉

## 🎬 How It Works

```
User Question
    ↓
Backend generates text answer (LLM/Templates)
    ↓
D-ID API receives:
  - Text to speak
  - Language (Hindi, Tamil, etc.)
  - Avatar image URL
    ↓
D-ID generates video (10-20 seconds)
    ↓
Frontend receives video URL
    ↓
Video plays with perfect lip-sync!
```

## 🎭 Avatar Customization

### Using Default Avatar

The default avatar is a professional female banker. No changes needed!

### Using Custom Avatar

1. **Prepare your image:**
   - Clear face photo
   - Front-facing, well-lit
   - Neutral expression
   - JPG/PNG format
   - Recommended: 512x512px or higher

2. **Upload to public hosting:**
   - Upload to your cloud storage (AWS S3, Azure Blob, Google Cloud Storage)
   - Make it publicly accessible (read-only)
   - Copy the URL

3. **Update backend code:**
   
   Edit `backend/routers/video_agent.py`:
   ```python
   # Line ~215
   avatar_url = "https://your-domain.com/path/to/avatar.jpg"
   ```

4. **Or make it dynamic per customer:**
   ```python
   # Use customer profile photo
   avatar_url = customer.profile_photo_url or "https://default-avatar.jpg"
   ```

### Using Multiple Avatars

Create avatar mapping based on language:
```python
def get_avatar_for_language(language: str) -> str:
    avatar_map = {
        "en": "https://avatars.com/indian-female-en.jpg",
        "hi": "https://avatars.com/indian-female-hi.jpg",
        "ta": "https://avatars.com/indian-female-ta.jpg",
        # ... more languages
    }
    return avatar_map.get(language, avatar_map["en"])

# In generate_video_with_did():
avatar_url = get_avatar_for_language(language)
```

## 💰 Pricing & Limits

### Free Tier
- **10 credits/month** (≈ 10 videos)
- Great for testing!
- No credit card required

### Pay-as-you-go
- **$0.05 per video** (~10-20 seconds)
- **$0.08 per minute** for longer videos
- No monthly commitment

### Production Recommendations

For production with ~1000 customers/month asking 2-3 questions each:
- Expected: **2000-3000 videos/month**
- Cost: **$100-150/month**

**Cost Optimization Strategies:**
1. **Cache common questions** - Store pre-generated videos for FAQs
2. **Hybrid approach** - Use browser TTS for first response, D-ID for important questions
3. **Batch processing** - Generate videos during off-peak hours
4. **Length limits** - Keep answers concise (10-20 seconds)

## 🐛 Troubleshooting

### Issue 1: "D-ID API key not found"

**Solution:**
```powershell
# Check if env var is set
echo $env:DID_API_KEY

# If empty, set it:
$env:DID_API_KEY="your-key-here"

# Restart backend
```

### Issue 2: Video generation fails (status=error)

**Possible causes:**
- Invalid API key
- Avatar image URL inaccessible
- Text too long (>500 chars)
- Unsupported language

**Solution:**
```python
# Check backend logs for specific error
# Look for: "D-ID generation error: ..."

# Test API key manually:
curl -X POST https://api.d-id.com/talks \
  -H "Authorization: Basic YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "script": {
      "type": "text",
      "input": "Hello",
      "provider": {
        "type": "microsoft",
        "voice_id": "en-IN-NeerjaNeural"
      }
    },
    "source_url": "https://d-id-public-bucket.s3.amazonaws.com/alice.jpg"
  }'
```

### Issue 3: Video takes too long (>60 seconds)

**Cause:** D-ID timeout (max 30 attempts × 2 seconds = 60s)

**Solution:**
- Text might be too long (D-ID struggles with >200 words)
- Try shorter answers
- Check D-ID service status

### Issue 4: Video doesn't play in frontend

**Solution:**
```javascript
// Check browser console for errors
// Verify video URL is accessible
// Try opening video URL directly in browser

// Add autoplay policy handling:
videoRef.current.play()
  .then(() => console.log('Video playing'))
  .catch(err => {
    console.error('Autoplay blocked:', err);
    // Show play button to user
  });
```

### Issue 5: Browser TTS plays instead of video

**Cause:** D-ID API key not configured or video generation failed

**Check:**
1. Environment variable set correctly
2. Backend logs show "Generating D-ID video..."
3. No "D-ID API key not configured" message

**Fallback behavior:** System automatically uses browser TTS if video unavailable - this is intentional!

## 🔒 Security Best Practices

1. **Never commit API keys to Git**
   ```bash
   # Add to .gitignore
   .env
   ```

2. **Use environment variables**
   - Never hardcode keys in code
   - Use different keys for dev/staging/prod

3. **Restrict API key permissions**
   - Use separate keys for each environment
   - Revoke unused keys

4. **Monitor usage**
   - Check D-ID dashboard regularly
   - Set up billing alerts

## 📊 Monitoring & Analytics

### Track Video Generation

Add logging to backend:
```python
# In generate_video_with_did()
logger.info(f"Video generated for {language}: {talk_id}")
logger.info(f"Generation time: {generation_time}s")

# Store in database
VideoGeneration(
    customer_id=customer_id,
    language=language,
    text_length=len(text),
    generation_time=generation_time,
    status="success",
    video_url=video_url
)
```

### Dashboard Queries

```sql
-- Daily video generation count
SELECT DATE(interaction_time), COUNT(*)
FROM interaction_history
WHERE interaction_type = 'video_agent_chat'
GROUP BY DATE(interaction_time);

-- Popular languages
SELECT language, COUNT(*)
FROM video_generations
GROUP BY language
ORDER BY COUNT(*) DESC;

-- Average generation time
SELECT AVG(generation_time)
FROM video_generations
WHERE status = 'success';
```

## 🚀 Advanced Features

### 1. Custom Voices

D-ID supports 119 languages with multiple voice options:
```python
# Professional male voice for Hindi
"voice_id": "hi-IN-MadhurNeural"  # Male

# Friendly female voice for Tamil
"voice_id": "ta-IN-PallaviNeural"  # Female
```

### 2. Emotion Control

Add emotions to make avatar more expressive:
```python
payload = {
    "script": {
        "type": "text",
        "input": text,
        "provider": voice_config,
        "ssml": True  # Enable SSML for emotions
    },
    # ...
}

# In answer text:
answer_text = "<prosody rate='slow' pitch='+2st'>Your EMI is due soon!</prosody>"
```

### 3. Background Customization

Change avatar background:
```python
payload = {
    # ...
    "config": {
        "background": {
            "color": "#1E40AF",  # Blue background
            # Or use image:
            # "url": "https://your-background.jpg"
        }
    }
}
```

### 4. Video Caching

Cache videos for common questions:
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_video(question_hash: str, language: str) -> str:
    # Check database for cached video
    cached = db.query(CachedVideo).filter(
        CachedVideo.question_hash == question_hash,
        CachedVideo.language == language
    ).first()
    
    if cached and cached.created_at > datetime.now() - timedelta(days=30):
        return cached.video_url
    
    return None

# Usage
question_hash = hashlib.md5(question.encode()).hexdigest()
video_url = get_cached_video(question_hash, language)

if not video_url:
    video_url = generate_video_with_did(answer_text, language)
    # Cache it
    cache_video(question_hash, language, video_url)
```

## 📝 API Reference

### D-ID API Endpoints

**Create Talk (POST /talks)**
```json
{
  "script": {
    "type": "text",
    "input": "Text to speak",
    "provider": {
      "type": "microsoft",
      "voice_id": "en-IN-NeerjaNeural"
    }
  },
  "source_url": "https://avatar-image.jpg",
  "config": {
    "fluent": true,
    "pad_audio": 0.0,
    "stitch": true
  }
}
```

**Get Status (GET /talks/:id)**
```json
{
  "id": "talk-id",
  "status": "done",  // created / started / done / error
  "result_url": "https://video.mp4",
  "duration": 15.5
}
```

## 🎓 Learning Resources

- [D-ID Documentation](https://docs.d-id.com/)
- [D-ID API Reference](https://docs.d-id.com/reference/talks-api)
- [Voice Gallery](https://docs.d-id.com/docs/microsoft-azure-voices)
- [Best Practices](https://docs.d-id.com/docs/best-practices)

## ✅ Next Steps

1. ✅ **Test with real D-ID API key**
2. ⏳ **Customize avatar image**
3. ⏳ **Add video caching for popular questions**
4. ⏳ **Monitor usage and optimize costs**
5. ⏳ **Collect user feedback on video quality**

---

**Need Help?**
- Check D-ID support: support@d-id.com
- Review backend logs: `backend/routers/video_agent.py`
- Test API: https://studio.d-id.com/
