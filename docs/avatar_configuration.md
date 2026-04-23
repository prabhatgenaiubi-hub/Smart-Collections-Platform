# Avatar Configuration Guide

This guide explains how to configure different avatars for the Video AI Agent.

## Current Configuration

**Backend**: `backend/routers/video_agent.py` (line ~420)  
**Frontend Fallback**: `frontend/src/components/VideoCallAgent.jsx` (line ~430)

---

## D-ID Avatar Options

### Option 1: Professional Female Presenter (Default)
**Best for**: Indian banking context, friendly and trustworthy

```python
avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_kYZmXDNL4MaWQWe5fuqKt/image.png"
```

**Features**:
- Professional business attire
- Neutral, friendly expression
- Suitable for diverse customer base

---

### Option 2: Professional Male Presenter
**Best for**: Corporate banking, formal interactions

```python
avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_NMqLWiQVB4iHYjCCWFwYx/image.png"
```

**Features**:
- Business suit
- Professional demeanor
- Trustworthy appearance

---

### Option 3: D-ID Preset Presenters (Most Reliable)
**Best for**: Production deployment, guaranteed availability

```python
# Female presenter
avatar_url = "amy-jcwCkr1grs"

# Male presenter  
avatar_url = "noah-jVnRDjO_Tw"

# Other options
avatar_url = "rian-00vJaMc3R1"  # Young professional male
avatar_url = "kira-Y7YWkZiKNv"  # Young professional female
```

**Features**:
- Hosted by D-ID (always available)
- Optimized for lip-sync quality
- Multiple presenter IDs available
- No external URL dependencies

---

### Option 4: Custom Avatar (Your Own Image)
**Best for**: Brand consistency, specific requirements

**Requirements**:
- Image format: JPG, PNG
- Recommended size: 512x512 or higher
- Face clearly visible, frontal view
- Good lighting, neutral background

**Steps**:
1. Upload your image to a public URL (AWS S3, Cloudinary, etc.)
2. Use the public URL:
   ```python
   avatar_url = "https://your-cdn.com/path/to/avatar.jpg"
   ```

**Example with company logo background**:
```python
avatar_url = "https://your-company.com/avatars/ai-assistant.png"
```

---

## How to Change Avatar

### Backend (D-ID Video Generation)

Edit `backend/routers/video_agent.py`:

```python
def generate_video_with_did(text: str, language: str) -> str:
    # ... existing code ...
    
    # CHANGE THIS LINE:
    avatar_url = "amy-jcwCkr1grs"  # ← Your chosen avatar
    
    payload = {
        "source_url": avatar_url,
        # ... rest of payload ...
    }
```

### Frontend Fallback Icon

Edit `frontend/src/components/VideoCallAgent.jsx`:

The fallback avatar (shown when D-ID is not configured) uses a professional user icon. You can customize it by:

1. **Change Icon**: Replace the SVG path with a different icon
2. **Use Image**: Replace the SVG with an `<img>` tag
3. **Change Colors**: Modify the gradient colors in `from-blue-500 to-purple-600`

**Example with image**:
```jsx
<div className="w-48 h-48 mx-auto rounded-full overflow-hidden shadow-2xl border-4 border-white">
  <img 
    src="https://your-cdn.com/avatar.jpg" 
    alt="AI Assistant"
    className="w-full h-full object-cover"
  />
</div>
```

---

## Advanced Configuration

### Multiple Avatars (Language-Based)

You can show different avatars based on customer language:

```python
def get_avatar_for_language(language: str) -> str:
    """Return appropriate avatar based on language/region"""
    
    avatars = {
        "hi": "indian-female-avatar-url",  # Hindi
        "ta": "south-indian-avatar-url",   # Tamil
        "te": "south-indian-avatar-url",   # Telugu
        "en": "professional-neutral-url",  # English
        # ... more mappings
    }
    
    return avatars.get(language, "amy-jcwCkr1grs")  # Default
```

Then use it:
```python
avatar_url = get_avatar_for_language(language)
```

---

### Gender-Based Avatars

Allow customers to choose their preferred presenter:

```python
# Store preference in customer profile
customer_preferences = {
    "avatar_preference": "female"  # or "male"
}

# Use in video generation
avatar_url = "amy-jcwCkr1grs" if preference == "female" else "noah-jVnRDjO_Tw"
```

---

### Avatar with Expressions

Control facial expressions for different scenarios:

```python
payload = {
    "source_url": avatar_url,
    "config": {
        "fluent": True,
        "driver_expressions": {
            "expressions": [
                {"start_frame": 0, "expression": "happy", "intensity": 0.8},      # Greeting
                {"start_frame": 50, "expression": "neutral", "intensity": 0.5},   # Explanation
                {"start_frame": 100, "expression": "serious", "intensity": 0.7}   # Important info
            ]
        }
    }
}
```

**Available expressions**:
- `neutral` - Default, professional
- `happy` - Friendly greeting
- `serious` - Important information
- `surprise` - Unexpected news

---

## Testing Avatars

### Test in Development

1. Update avatar URL in `video_agent.py`
2. Restart backend: `uvicorn backend.main:app --reload`
3. Open Video AI Agent in browser
4. Ask a question and check the video

### Preview Without Backend

Use D-ID Studio to preview avatars:
1. Go to https://studio.d-id.com/
2. Click "Create Video"
3. Select different presenters
4. Test with sample text

---

## Best Practices

### ✅ Do's
- Use D-ID preset presenters for production (more reliable)
- Test avatar with different languages/accents
- Choose avatars matching your brand identity
- Use high-quality images (512x512+)
- Ensure consistent avatar across all videos

### ❌ Don'ts
- Don't use low-resolution images (< 256x256)
- Don't use copyrighted images without permission
- Don't use avatars with extreme expressions
- Don't change avatars too frequently (confuses users)
- Don't use celebrity faces (legal issues)

---

## Recommended Setup

**For Banking/Financial Services**:
```python
# Professional, trustworthy, neutral
avatar_url = "amy-jcwCkr1grs"  # Female
# OR
avatar_url = "noah-jVnRDjO_Tw"  # Male
```

**For E-commerce/Retail**:
```python
# Friendly, approachable, younger
avatar_url = "kira-Y7YWkZiKNv"  # Young female
# OR
avatar_url = "rian-00vJaMc3R1"  # Young male
```

**For Healthcare**:
```python
# Calm, professional, reassuring
avatar_url = "amy-jcwCkr1grs"  # Recommended
```

---

## Troubleshooting

### Avatar not loading
- Check if URL is publicly accessible
- Verify D-ID API key is valid
- Check D-ID API response for errors
- Try using a preset presenter ID

### Poor lip-sync quality
- Use D-ID preset presenters (optimized)
- Ensure image has clear face visibility
- Use frontal face photos, not profiles
- Avoid images with shadows on face

### Video generation fails
- Check D-ID API credits/quota
- Verify avatar URL returns 200 status
- Test with preset presenter first
- Check backend logs for error messages

---

## Cost Considerations

**D-ID Pricing** (as of 2026):
- Each video generation costs credits
- Preset presenters use fewer credits
- Custom images may cost more
- Check D-ID dashboard for current pricing

**Optimization**:
- Cache frequently asked questions
- Use shorter responses (less generation time)
- Consider text fallback for simple queries

---

## Support

For more information:
- **D-ID Documentation**: https://docs.d-id.com/
- **D-ID Studio**: https://studio.d-id.com/
- **Avatar Gallery**: https://studio.d-id.com/agents

---

**Last Updated**: April 2026  
**Current Avatar**: Professional female presenter (Indian banking context)
