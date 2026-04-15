# Architecture Upgrade: English-First Voice Transcription

## Overview
Upgraded the STT → LLM → Translation pipeline to match the production app architecture, where:
- **Saaras returns English transcripts directly** (not native Devanagari/Tamil script)
- **UI displays English transcript** with language label
- **AI response translated to user's language** via Mayura
- **Analysis section** shows Intent, Sentiment, Escalation flag

## Changes Summary

### 1. Backend - Transcribe Endpoint (`customer.py`)

**File**: `backend/routers/customer.py`

**Key Changes**:
```python
# OLD: Saaras returned native script, then translated via Mayura
saaras_data = {
    "language_code": "hi-IN",  # Hindi
    # ... Saaras returns Devanagari
}
# Then translate to English via Mayura...

# NEW: Saaras returns English directly
saaras_data = {
    "model": "saaras:v2",
    "target_language_code": "en-IN",  # ← Force English output
    "with_timestamps": "false",
    "with_disfluencies": "false",
}
```

**Response Format**:
```json
{
  "transcript": "What is my pending EMI amount?",  // English
  "detected_language": "Hindi",                     // Display name
  "language_code": "hi-IN"                          // BCP-47
}
```

**What was removed**:
- Entire Mayura translation section (50+ lines)
- Native script handling

---

### 2. Backend - Chat Endpoint (`chat.py`)

**File**: `backend/routers/chat.py`

**Key Changes**:

#### SendMessageRequest Model
```python
# OLD
class SendMessageRequest(BaseModel):
    message: str              # native script
    english_text: str         # pre-translated
    original_language: str    # BCP-47

# NEW
class SendMessageRequest(BaseModel):
    message: str              # English (from Saaras or typed)
    language: Optional[str]   # language name for response translation
```

#### New Helper Functions
```python
def _classify_intent(message: str) -> str:
    """Returns: LOAN_EMI_QUERY, LOAN_BALANCE_QUERY, etc."""

def _analyze_sentiment(message: str) -> str:
    """Returns: calm, frustrated, angry, distressed"""

def _check_escalation(sentiment: str, message: str) -> bool:
    """Returns: True if needs human support"""
```

#### Pipeline Flow
```python
# 1. Extract English message (already English from Saaras)
message_english = body.message.strip()

# 2. Classify intent
intent = _classify_intent(message_english)

# 3. Analyze sentiment
sentiment = _analyze_sentiment(message_english)

# 4. Check escalation
escalation_required = _check_escalation(sentiment, message_english)

# 5. Save user message (English)
user_msg = ChatMessage(
    message_text = message_english,
    english_text = message_english,
    original_language = user_language,
)

# 6. Run LLM (English → English)
result = run_chat_response(user_query=message_english, ...)

# 7. Translate response to user's language
if needs_translation:
    ai_response = await _translate_mayura(ai_response, "en-IN", user_lang_code)

# 8. Return with analysis
return {
    "ai_response": {...},
    "detected_language": user_language,
    "analysis": {
        "intent": intent,
        "sentiment": sentiment,
        "escalation_required": escalation_required,
    }
}
```

---

### 3. Frontend - Voice Chat UI (`LoanChat.jsx`)

**File**: `frontend/src/components/LoanChat.jsx`

**Key Changes**:

#### Voice Transcription Handler
```javascript
// OLD: Destructured native + English text
const { transcript, english_text } = resp.data;
await sendMessage(transcript, english_text, detected_language);

// NEW: Transcript IS English
const { transcript, detected_language } = resp.data;
await sendMessage(transcript, '', detected_language);
```

#### sendMessage Function
```javascript
const sendMessage = useCallback(async (textArg, _unused, langArg) => {
  const text = (textArg ?? input).trim();  // English text
  const lang = langArg ?? language;
  
  // Add metadata to user message
  const userMsg = {
    role: 'user',
    message_text: text,                      // English
    isEnglishTranscript: lang !== 'auto',    // Flag for voice
    originalLanguage: lang,                  // "Hindi", "Tamil", etc.
  };
  setMessages(m => [...m, userMsg]);
  
  // Send to backend
  const r = await api.post(`/chat/sessions/${sessionId}/message`, {
    message: text,          // English
    language: lang,         // For response translation
  });
  
  // Attach analysis to AI message
  const aiMsg = { ...r.data.ai_response };
  if (r.data.analysis) aiMsg.analysis = r.data.analysis;
  setMessages(m => [...m, aiMsg]);
});
```

#### Message Rendering
```jsx
{messages.map((msg, idx) => (
  <div key={idx} className="space-y-1.5">
    {/* Transcription label */}
    {msg.isEnglishTranscript && (
      <span>📝 Transcribed Text ({msg.originalLanguage})</span>
    )}
    
    {/* Message bubble */}
    <div>{msg.message_text}</div>
    
    {/* Analysis section */}
    {msg.analysis && (
      <div className="analysis-box">
        <p>🧠 Analysis</p>
        <p>Intent: {msg.analysis.intent}</p>
        <p>Sentiment: {msg.analysis.sentiment}</p>
        <p>Escalation: {msg.analysis.escalation_required}</p>
      </div>
    )}
  </div>
))}
```

---

## Intent Categories

The system classifies user queries into these categories:
- `LOAN_EMI_QUERY` - EMI amount, due date, next payment
- `LOAN_BALANCE_QUERY` - Outstanding balance, total due
- `GRACE_PERIOD_QUERY` - Extension, postpone, delay payment
- `RESTRUCTURE_QUERY` - Modify loan, change EMI, reduce EMI
- `PAYMENT_ASSISTANCE` - How to pay, payment methods
- `COMPLAINT` - Issues, problems, errors
- `GENERAL_QUERY` - Everything else

## Sentiment Levels

The system detects four sentiment levels:
- `calm` (default) - Neutral, informational queries
- `frustrated` - Annoyed, confused, repeated issues
- `angry` - Strong negative emotions, threats
- `distressed` - Desperate, urgent, financial hardship

## Escalation Triggers

Human escalation is flagged when:
1. Sentiment is `angry` or `distressed`
2. Keywords detected: "speak to manager", "talk to someone", "human", "cancel", "complaint", "lawyer", "legal"

---

## Testing Checklist

### Voice Recording (Hindi)
1. ✅ Click mic button
2. ✅ Say: "मेरा लोन बैलेंस क्या है?" (What is my loan balance?)
3. ✅ Verify transcription: "What is my loan balance?" (English)
4. ✅ Verify label: "📝 Transcribed Text (Hindi)"
5. ✅ Verify AI response in Hindi
6. ✅ Verify analysis section shows:
   - Intent: LOAN_BALANCE_QUERY
   - Sentiment: calm
   - Escalation: ✅ No

### Voice Recording (Angry tone)
1. ✅ Say: "I am very frustrated with this service! I want to speak to a manager!"
2. ✅ Verify sentiment: 😡 Angry
3. ✅ Verify escalation: 🚨 Yes

### Typed English Message
1. ✅ Type: "What is my EMI amount?"
2. ✅ Verify NO transcription label (not voice)
3. ✅ Verify analysis section shows:
   - Intent: LOAN_EMI_QUERY
   - Sentiment: 😌 Calm
   - Escalation: ✅ No

---

## Database Schema Updates

**Table**: `chat_messages`

**New Columns** (already migrated):
```sql
ALTER TABLE chat_messages ADD COLUMN english_text TEXT;
ALTER TABLE chat_messages ADD COLUMN original_language VARCHAR;
```

**Usage**:
- `message_text`: English text (from Saaras or typed)
- `english_text`: Same as message_text (for consistency)
- `original_language`: Language name ("Hindi", "Tamil", "English", etc.)

---

## API Endpoints Modified

### `POST /customer/self-cure/transcribe`
**OLD Response**:
```json
{
  "transcript": "मेरा लोन क्या है?",
  "english_text": "What is my loan?",
  "language": "Hindi"
}
```

**NEW Response**:
```json
{
  "transcript": "What is my loan?",
  "detected_language": "Hindi",
  "language_code": "hi-IN"
}
```

### `POST /chat/sessions/{session_id}/message`
**OLD Request**:
```json
{
  "message": "मेरा लोन क्या है?",
  "english_text": "What is my loan?",
  "original_language": "hi-IN"
}
```

**NEW Request**:
```json
{
  "message": "What is my loan?",
  "language": "Hindi"
}
```

**NEW Response** (added `analysis`):
```json
{
  "success": true,
  "ai_response": {
    "message_id": 123,
    "role": "assistant",
    "message_text": "आपका लोन बैलेंस...",
    "timestamp": "2024-01-15 10:30:00"
  },
  "detected_language": "Hindi",
  "analysis": {
    "intent": "LOAN_BALANCE_QUERY",
    "sentiment": "calm",
    "escalation_required": false
  }
}
```

---

## Benefits of New Architecture

1. **Consistency**: English is the "source of truth" for all processing
2. **Better Analysis**: Intent/sentiment classification works better in English
3. **Simpler Pipeline**: One translation step instead of two
4. **Audit Trail**: English transcripts are easier to review for compliance
5. **Debugging**: Easier to debug LLM reasoning (all in English)
6. **UI Transparency**: Users see what the system "understood" in English
7. **Escalation Visibility**: Officers can see why a case was escalated

---

## Rollback Plan (if needed)

If issues arise, revert these commits:
1. `customer.py` - restore Mayura translation in transcribe endpoint
2. `chat.py` - restore `english_text` field handling
3. `LoanChat.jsx` - restore native text display

**Note**: Database migration is backward-compatible (new columns are nullable).

---

## Future Enhancements

1. **Advanced Intent Classification**: Use LLM-based classification instead of keywords
2. **Sentiment Score**: Return numerical score (0-100) instead of discrete levels
3. **Multi-turn Context**: Consider conversation history for sentiment analysis
4. **Auto-escalation**: Automatically assign to human agent when escalation flag is True
5. **Analytics Dashboard**: Show distribution of intents, sentiments, escalations

---

## References

- **Sarvam AI Docs**: https://docs.sarvam.ai/
- **Saaras Model**: `saaras:v2` (STT with translation capability)
- **Mayura Model**: `mayura:v1` (Translation Hindi↔English, Tamil↔English)
- **API Key**: `SARVAM_API_KEY` (environment variable)
