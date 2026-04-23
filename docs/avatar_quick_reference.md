# Quick Avatar Reference

## Top 5 Professional Avatars for Banking

### 🥇 Recommended: Amy (D-ID Preset)
```python
avatar_url = "amy-jcwCkr1grs"
```
- **Type**: D-ID Preset Presenter
- **Gender**: Female
- **Style**: Professional, trustworthy
- **Best for**: General banking, customer service
- **Reliability**: ⭐⭐⭐⭐⭐ (D-ID hosted)
- **Lip-sync Quality**: Excellent
- **Availability**: Always available

---

### 🥈 Noah (D-ID Preset)
```python
avatar_url = "noah-jVnRDjO_Tw"
```
- **Type**: D-ID Preset Presenter
- **Gender**: Male
- **Style**: Corporate, authoritative
- **Best for**: Formal banking, loan advisory
- **Reliability**: ⭐⭐⭐⭐⭐ (D-ID hosted)
- **Lip-sync Quality**: Excellent
- **Availability**: Always available

---

### 🥉 Professional Indian Female (Current)
```python
avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_kYZmXDNL4MaWQWe5fuqKt/image.png"
```
- **Type**: Custom Image
- **Gender**: Female
- **Style**: Professional, Indian context
- **Best for**: Indian banking, diverse customers
- **Reliability**: ⭐⭐⭐⭐ (External URL)
- **Lip-sync Quality**: Very Good
- **Availability**: Dependent on URL availability

---

### 4️⃣ Kira (Young Professional Female)
```python
avatar_url = "kira-Y7YWkZiKNv"
```
- **Type**: D-ID Preset Presenter
- **Gender**: Female
- **Style**: Friendly, approachable
- **Best for**: Younger customer base, fintech
- **Reliability**: ⭐⭐⭐⭐⭐ (D-ID hosted)
- **Lip-sync Quality**: Excellent
- **Availability**: Always available

---

### 5️⃣ Rian (Young Professional Male)
```python
avatar_url = "rian-00vJaMc3R1"
```
- **Type**: D-ID Preset Presenter
- **Gender**: Male
- **Style**: Modern, tech-savvy
- **Best for**: Tech-forward banking, younger audience
- **Reliability**: ⭐⭐⭐⭐⭐ (D-ID hosted)
- **Lip-sync Quality**: Excellent
- **Availability**: Always available

---

## Quick Comparison Table

| Avatar | Gender | Style | Best For | Reliability |
|--------|--------|-------|----------|-------------|
| Amy | Female | Professional | General banking | ⭐⭐⭐⭐⭐ |
| Noah | Male | Corporate | Formal banking | ⭐⭐⭐⭐⭐ |
| Custom Indian | Female | Professional | Indian context | ⭐⭐⭐⭐ |
| Kira | Female | Friendly | Younger audience | ⭐⭐⭐⭐⭐ |
| Rian | Male | Modern | Tech-forward | ⭐⭐⭐⭐⭐ |

---

## How to Switch

### Method 1: Edit Backend File

1. Open `backend/routers/video_agent.py`
2. Find line ~423: `avatar_url = "..."`
3. Replace with your chosen avatar from above
4. Save file
5. Backend will auto-reload (if using `--reload` flag)

### Method 2: Environment Variable (Advanced)

1. Add to `.env` file:
   ```bash
   DID_AVATAR_URL=amy-jcwCkr1grs
   ```

2. Update `video_agent.py`:
   ```python
   avatar_url = os.getenv("DID_AVATAR_URL", "amy-jcwCkr1grs")
   ```

3. Restart backend

---

## Testing Commands

```bash
# 1. Restart backend
cd D:\Prabhat\GenAI Prabhat\Smart-Collections-Platform
uvicorn backend.main:app --reload

# 2. Test in browser
# - Go to http://localhost:5173
# - Login as customer
# - Click "📹 Ask Video AI Agent"
# - Ask: "What is my loan balance?"
# - Observe the avatar in the video response
```

---

## Recommendation for Your Use Case

**For Collections Intelligence Platform (Indian Banking)**:

### Option A: Reliable & Professional
```python
avatar_url = "amy-jcwCkr1grs"  # D-ID preset
```
- ✅ Always available
- ✅ Excellent lip-sync
- ✅ Professional appearance
- ✅ No external dependencies

### Option B: Context-Specific
```python
avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_kYZmXDNL4MaWQWe5fuqKt/image.png"
```
- ✅ Indian context
- ✅ Professional appearance
- ⚠️ External URL dependency

### Option C: Gender Choice
```python
# Female for approachable, trustworthy feel
avatar_url = "amy-jcwCkr1grs"

# Male for authoritative, formal feel
avatar_url = "noah-jVnRDjO_Tw"
```

---

## Current Configuration

**As of April 2026, your system uses**:

**Backend**: Professional Indian Female (Custom URL)  
**Frontend Fallback**: Professional user icon (SVG)

**Recommendation**: Consider switching to `amy-jcwCkr1grs` for production due to higher reliability (D-ID hosted).

---

## Need More Options?

### Explore D-ID Studio
1. Visit https://studio.d-id.com/
2. Click "Agents" or "Presenters"
3. Browse available avatars
4. Note the presenter ID (e.g., `amy-jcwCkr1grs`)
5. Use in your code

### Upload Custom Avatar
1. Go to D-ID Studio
2. Upload your image (512x512+)
3. Get the URL from your created video
4. Use in your code

---

**Quick Copy-Paste for Most Common Change**:

```python
# In backend/routers/video_agent.py, line ~423
# Replace existing avatar_url with:

avatar_url = "amy-jcwCkr1grs"  # Most reliable option
```

**That's it!** Restart backend and test.
