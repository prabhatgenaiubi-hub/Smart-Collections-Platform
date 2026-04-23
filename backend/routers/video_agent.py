"""
Video Call Agent Router
Handles AI-powered video assistant for loan-specific Q&A
Supports multilingual responses using Sarvam AI TTS
Supports voice input with Sarvam STT and automatic language detection
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import requests
import os
import base64
import tempfile
import subprocess

from backend.db.database import get_db
from backend.db.models import Loan, Customer, PaymentHistory, InteractionHistory
from backend.routers.auth import get_current_customer

# Import Sarvam AI SDK (same as working customer.py)
from sarvamai import SarvamAI

router = APIRouter(prefix="/customer/video-agent", tags=["Video Agent"])


# ─────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────

class VideoChatRequest(BaseModel):
    loan_id: str
    question: str
    language: str = "en"  # en, hi, ta, te, kn, ml, bn, gu, mr


class VideoChatResponse(BaseModel):
    answer_text: str
    answer_audio_url: Optional[str] = None
    answer_video_url: Optional[str] = None  # ← D-ID video URL
    video_status: str = "processing"  # processing / ready / failed / disabled
    language: str
    timestamp: str
    loan_context: dict


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def get_loan_context(loan: Loan, customer: Customer, db: Session) -> dict:
    """Get comprehensive loan context for AI agent"""
    
    # Payment history
    payments = db.query(PaymentHistory).filter(
        PaymentHistory.loan_id == loan.loan_id
    ).order_by(PaymentHistory.payment_date.desc()).limit(5).all()
    
    last_payment = payments[0] if payments else None
    
    # Convert dates to strings for JSON serialization
    emi_due_date_str = loan.emi_due_date.strftime("%Y-%m-%d") if hasattr(loan.emi_due_date, 'strftime') else str(loan.emi_due_date)
    last_payment_date_str = last_payment.payment_date.strftime("%Y-%m-%d") if last_payment and hasattr(last_payment.payment_date, 'strftime') else (str(last_payment.payment_date) if last_payment else None)
    
    return {
        "customer_name": customer.customer_name,
        "loan_id": loan.loan_id,
        "loan_type": loan.loan_type,
        "loan_amount": float(loan.loan_amount) if loan.loan_amount else 0,
        "outstanding_balance": float(loan.outstanding_balance) if loan.outstanding_balance else 0,
        "emi_amount": float(loan.emi_amount) if loan.emi_amount else 0,
        "emi_due_date": emi_due_date_str,
        "days_past_due": int(loan.days_past_due) if loan.days_past_due else 0,
        "risk_segment": loan.risk_segment,
        "last_payment_date": last_payment_date_str,
        "last_payment_amount": float(last_payment.payment_amount) if last_payment and last_payment.payment_amount else None,
        "total_payments_made": len(payments),
    }


def generate_loan_answer(question: str, loan_context: dict, language: str) -> str:
    """Generate AI answer based on loan context and question"""
    
    # Build context for LLM
    context = f"""
You are a helpful AI loan assistant. Answer the customer's question based on their loan details.

Loan Details:
- Customer: {loan_context['customer_name']}
- Loan Type: {loan_context['loan_type']}
- Loan Amount: ₹{loan_context['loan_amount']:,}
- Outstanding Balance: ₹{loan_context['outstanding_balance']:,}
- EMI Amount: ₹{loan_context['emi_amount']:,}
- Next EMI Due: {loan_context['emi_due_date']}
- Days Past Due: {loan_context['days_past_due']}
- Last Payment: ₹{loan_context['last_payment_amount']} on {loan_context['last_payment_date']}

Language: {language}
Customer Question: {question}

Provide a helpful, friendly answer in {language} language. Keep it concise (2-3 sentences).
If in Hindi, use Devanagari script. Be supportive and professional.
"""
    
    # Use OpenAI API or fallback to template-based responses
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful loan assistant."},
                {"role": "user", "content": context}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"LLM Error: {e}")
        # Fallback to template-based responses
        return generate_template_answer(question, loan_context, language)


def generate_template_answer(question: str, loan_context: dict, language: str) -> str:
    """Fallback template-based answers for common questions"""
    
    q_lower = question.lower()
    
    # English responses
    if language == "en":
        if any(word in q_lower for word in ["emi", "payment", "due", "next"]):
            return f"Your next EMI of ₹{loan_context['emi_amount']:,} is due on {loan_context['emi_due_date']}. You can pay online or enable Auto-Pay to never miss a payment."
        
        elif any(word in q_lower for word in ["outstanding", "balance", "owe"]):
            return f"Your current outstanding balance is ₹{loan_context['outstanding_balance']:,}. This includes your principal and any pending interest."
        
        elif any(word in q_lower for word in ["grace", "extension", "delay"]):
            return f"If you need more time to pay, you can request a grace period. This will give you extra days without penalty. Would you like to apply?"
        
        elif any(word in q_lower for word in ["auto", "autopay", "automatic"]):
            return f"Auto-Pay ensures your EMI of ₹{loan_context['emi_amount']:,} is automatically deducted on {loan_context['emi_due_date']} each month. No more missed payments!"
        
        else:
            return f"I'm here to help with your {loan_context['loan_type']}. Your next EMI of ₹{loan_context['emi_amount']:,} is due on {loan_context['emi_due_date']}. What would you like to know?"
    
    # Hindi responses
    elif language == "hi":
        if any(word in q_lower for word in ["emi", "payment", "due", "next", "भुगतान"]):
            return f"आपकी अगली EMI ₹{loan_context['emi_amount']:,} है जो {loan_context['emi_due_date']} को देय है। आप ऑनलाइन भुगतान कर सकते हैं या Auto-Pay सक्षम कर सकते हैं।"
        
        elif any(word in q_lower for word in ["outstanding", "balance", "बकाया"]):
            return f"आपका वर्तमान बकाया ₹{loan_context['outstanding_balance']:,} है। इसमें मूलधन और ब्याज शामिल है।"
        
        elif any(word in q_lower for word in ["grace", "समय", "विस्तार"]):
            return f"यदि आपको भुगतान के लिए अधिक समय चाहिए, तो आप ग्रेस पीरियड का अनुरोध कर सकते हैं। क्या आप आवेदन करना चाहेंगे?"
        
        else:
            return f"मैं आपके {loan_context['loan_type']} में मदद के लिए यहाँ हूँ। आपकी अगली EMI ₹{loan_context['emi_amount']:,} है जो {loan_context['emi_due_date']} को देय है।"
    
    # Default
    return f"Your next EMI of ₹{loan_context['emi_amount']:,} is due on {loan_context['emi_due_date']}. How can I help you today?"


def generate_audio_url(text: str, language: str) -> Optional[str]:
    """Generate audio using Sarvam AI TTS (mock for now)"""
    
    # TODO: Integrate with actual Sarvam TTS API
    # For now, return None (frontend can use browser TTS as fallback)
    
    """
    # Real Sarvam TTS integration would look like:
    try:
        response = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "Authorization": f"Bearer {os.getenv('SARVAM_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "language": language,
                "voice": "female",
                "speed": 1.0
            }
        )
        return response.json().get("audio_url")
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
    """
    
    return None  # Browser TTS fallback


# ─────────────────────────────────────────────
# Audio Processing Helpers (COPIED FROM WORKING customer.py)
# ─────────────────────────────────────────────

MAX_CHUNK_SECONDS = 29

SARVAM_LANG_MAP = {
    "hi-IN": "Hindi",   "ta-IN": "Tamil",   "te-IN": "Telugu",
    "kn-IN": "Kannada", "ml-IN": "Malayalam","mr-IN": "Marathi",
    "gu-IN": "Gujarati","bn-IN": "Bengali", "en-IN": "English",
    "pa-IN": "Punjabi", "od-IN": "Odia",
}


def _convert_to_wav(input_path: str) -> str:
    """Convert audio file to WAV format (16kHz, mono) for Saaras."""
    output_path = input_path + ".wav"
    
    subprocess.run(
        [
            "ffmpeg",
            "-y",                # Overwrite output file if exists
            "-i", input_path,    # Input file
            "-ar", "16000",      # Sample rate: 16kHz (required by Saaras)
            "-ac", "1",          # Audio channels: 1 (mono)
            output_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    
    return output_path


def _split_audio(wav_path: str) -> list[str]:
    """Split audio into 29-second chunks (Saaras has 30s limit)."""
    chunk_dir = tempfile.mkdtemp()
    pattern = os.path.join(chunk_dir, "chunk_%03d.wav")
    
    subprocess.run(
        [
            "ffmpeg",
            "-i", wav_path,
            "-f", "segment",
            "-segment_time", str(MAX_CHUNK_SECONDS),
            "-c", "copy",
            pattern
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    
    return sorted(
        os.path.join(chunk_dir, f)
        for f in os.listdir(chunk_dir)
        if f.endswith(".wav")
    )


def transcribe_audio_with_sarvam(audio_data: bytes, filename: str = "audio.webm") -> dict:
    """
    Transcribe audio using Sarvam AI SDK (PROVEN WORKING APPROACH from customer.py).
    Returns: {"text": "transcribed text", "language": "hi-IN"}
    """
    
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    if not SARVAM_API_KEY:
        print("[Sarvam STT] API key not found. Voice input disabled.")
        return None
    
    input_path = None
    wav_path = None
    chunks = []
    
    try:
        print(f"[Sarvam STT] Audio size: {len(audio_data)} bytes, filename: {filename}")
        
        # Save uploaded audio data to temp file
        suffix = os.path.splitext(filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_data)
            tmp.flush()
            input_path = tmp.name
        print(f"[Sarvam STT] Saved to: {input_path}")
        
        # Initialize Sarvam AI client
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        
        # Convert to WAV (16kHz, mono) - Required by Sarvam
        print(f"[Sarvam STT] Converting to WAV format...")
        wav_path = _convert_to_wav(input_path)
        
        # Split into chunks (29s max)
        print(f"[Sarvam STT] Splitting audio...")
        chunks = _split_audio(wav_path)
        print(f"[Sarvam STT] Created {len(chunks)} chunk(s)")
        
        # Transcribe each chunk using SDK
        transcripts = []
        detected_lang = None
        
        for i, chunk_path in enumerate(chunks):
            print(f"[Sarvam STT] Transcribing chunk {i+1}/{len(chunks)}")
            
            with open(chunk_path, "rb") as audio_handle:
                # Use SDK transcribe method
                response = client.speech_to_text.transcribe(
                    file=audio_handle,
                    model="saaras:v3"
                )
            
            text = response.transcript.strip()
            lang = response.language_code
            
            print(f"✅ [Chunk {i+1}] Lang: {lang}, Text: '{text[:60]}'")
            
            if text:
                transcripts.append(text)
                detected_lang = lang
        
        if not transcripts:
            print("[Sarvam STT] No transcription produced")
            return None
        
        final_text = " ".join(transcripts)
        detected_lang = detected_lang or "en-IN"
        
        print(f"[Sarvam STT] SUCCESS - Transcribed: '{final_text}' (Language: {detected_lang})")
        
        return {
            "text": final_text,
            "language": detected_lang
        }
        
    except subprocess.CalledProcessError as e:
        print(f"[Sarvam STT] ffmpeg error: {e}")
        return None
    except Exception as e:
        print(f"[Sarvam STT] Exception: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Cleanup any remaining temp files
        try:
            if input_path and os.path.exists(input_path):
                os.unlink(input_path)
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)
            for chunk in chunks:
                if os.path.exists(chunk):
                    os.unlink(chunk)
        except:
            pass


def detect_language_from_text(text: str) -> str:
    """
    Detect language from text using simple heuristics.
    Fallback if STT doesn't provide language.
    """
    
    # Common Hindi words
    hindi_chars = set('अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह')
    # Tamil
    tamil_chars = set('அஆஇஈஉஊஎஏஐஒஓஔகஙசஞடணதநபமயரலவழளறன')
    # Telugu  
    telugu_chars = set('అఆఇఈఉఊఋఎఏఐఒఓఔకఖగఘఙచఛజఝఞటఠడఢణతథదధనపఫబభమయరలవశషసహళ')
    
    text_chars = set(text)
    
    if text_chars & hindi_chars:
        return "hi"
    elif text_chars & tamil_chars:
        return "ta"
    elif text_chars & telugu_chars:
        return "te"
    else:
        return "en"  # Default to English


def get_voice_id_for_language(language: str) -> dict:
    """Map language codes to D-ID voice IDs (Microsoft Azure)"""
    voice_map = {
        "en": {"type": "microsoft", "voice_id": "en-IN-NeerjaNeural"},      # English India Female
        "hi": {"type": "microsoft", "voice_id": "hi-IN-SwaraNeural"},       # Hindi Female
        "ta": {"type": "microsoft", "voice_id": "ta-IN-PallaviNeural"},     # Tamil Female
        "te": {"type": "microsoft", "voice_id": "te-IN-ShrutiNeural"},      # Telugu Female
        "kn": {"type": "microsoft", "voice_id": "kn-IN-SapnaNeural"},       # Kannada Female
        "ml": {"type": "microsoft", "voice_id": "ml-IN-SobhanaNeural"},     # Malayalam Female
        "bn": {"type": "microsoft", "voice_id": "bn-IN-TanishaaNeural"},    # Bengali Female
        "gu": {"type": "microsoft", "voice_id": "gu-IN-DhwaniNeural"},      # Gujarati Female
        "mr": {"type": "microsoft", "voice_id": "mr-IN-AarohiNeural"},      # Marathi Female
    }
    return voice_map.get(language, voice_map["en"])


def generate_video_with_did(text: str, language: str) -> str:
    """
    Generate lip-synced video using D-ID API.
    Returns video URL once generation is complete.
    """
    
    D_ID_API_KEY = os.getenv("DID_API_KEY")
    if not D_ID_API_KEY:
        print("D-ID API key not found. Set DID_API_KEY environment variable.")
        return None
    
    D_ID_API_URL = "https://api.d-id.com/talks"
    
    # Get voice configuration for language
    voice_config = get_voice_id_for_language(language)
    
    headers = {
        "Authorization": f"Basic {D_ID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Professional avatar for banking/financial services
    # Options:
    # 1. Professional female presenter (business attire, friendly)
    # avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_kYZmXDNL4MaWQWe5fuqKt/image.png"
    
    # 2. Professional male presenter (business suit, trustworthy)
    # avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_NMqLWiQVB4iHYjCCWFwYx/image.png"
    
    # 3. Professional Indian female (suitable for Indian banking context)
    avatar_url = "https://create-images-results.d-id.com/google-oauth2%7C112852062801826026703/upl_kYZmXDNL4MaWQWe5fuqKt/image.png"
    
    # Alternative: Use D-ID's preset presenters (more reliable)
    # avatar_url = "amy-jcwCkr1grs"  # Professional female presenter
    # avatar_url = "noah-jVnRDjO_Tw"  # Professional male presenter
    
    payload = {
        "script": {
            "type": "text",
            "input": text,
            "provider": voice_config
        },
        "source_url": avatar_url,
        "config": {
            "fluent": True,
            "pad_audio": 0.0,
            "stitch": True,
            "driver_expressions": {
                "expressions": [
                    {"start_frame": 0, "expression": "neutral", "intensity": 0.7}
                ]
            }
        }
    }
    
    try:
        # Create video generation job
        response = requests.post(D_ID_API_URL, json=payload, headers=headers)
        
        if response.status_code != 201:
            print(f"D-ID API Error: {response.status_code} - {response.text}")
            return None
        
        talk_id = response.json()["id"]
        print(f"D-ID video generation started: {talk_id}")
        
        # Poll for completion (max 60 seconds)
        import time
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            status_response = requests.get(f"{D_ID_API_URL}/{talk_id}", headers=headers)
            status_data = status_response.json()
            
            status = status_data.get("status")
            
            if status == "done":
                video_url = status_data.get("result_url")
                print(f"D-ID video ready: {video_url}")
                return video_url
            elif status == "error":
                print(f"D-ID generation error: {status_data.get('error')}")
                return None
            elif status in ["created", "started"]:
                print(f"D-ID status: {status} (attempt {attempt + 1}/{max_attempts})")
                time.sleep(2)
                attempt += 1
            else:
                print(f"Unknown D-ID status: {status}")
                return None
        
        print("D-ID generation timeout")
        return None
        
    except Exception as e:
        print(f"D-ID Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@router.post("/chat", response_model=VideoChatResponse)
async def video_agent_chat(
    request: VideoChatRequest,
    current_user: dict = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Handle video agent chat request.
    Returns AI-generated answer with optional audio URL.
    """
    
    try:
        # Get customer_id from token (token uses 'user_id' key)
        customer_id = current_user.get("user_id")
        if not customer_id:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        # Verify loan belongs to customer
        loan = db.query(Loan).filter(
            Loan.loan_id == request.loan_id,
            Loan.customer_id == customer_id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        # Get customer details
        customer = db.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        
        # Get loan context
        loan_context = get_loan_context(loan, customer, db)
        
        # Generate answer
        answer_text = generate_loan_answer(request.question, loan_context, request.language)
        
        # Generate D-ID video with lip-sync
        video_url = None
        video_status = "disabled"
        
        # Only generate video if D-ID API key is configured
        if os.getenv("DID_API_KEY"):
            print(f"Generating D-ID video for language: {request.language}")
            video_url = generate_video_with_did(answer_text, request.language)
            video_status = "ready" if video_url else "failed"
        else:
            print("D-ID API key not configured. Skipping video generation.")
            video_status = "disabled"
        
        # Generate audio fallback (for browser TTS)
        audio_url = generate_audio_url(answer_text, request.language)
        
        # Log interaction
        interaction = InteractionHistory(
            customer_id=customer_id,
            interaction_type="video_agent_chat",
            interaction_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            conversation_text=f"Q: {request.question}\nA: {answer_text}",
            sentiment_score=0.8,  # Default positive
            tonality_score="Positive",
            interaction_summary=f"Video Agent ({request.language}): {request.question[:50]}..."
        )
        db.add(interaction)
        db.commit()
        
        return VideoChatResponse(
            answer_text=answer_text,
            answer_audio_url=audio_url,
            answer_video_url=video_url,
            video_status=video_status,
            language=request.language,
            timestamp=datetime.now().isoformat(),
            loan_context=loan_context
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in video_agent_chat: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/loan-summary/{loan_id}")
async def get_loan_summary_for_agent(
    loan_id: str,
    current_user: dict = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get loan summary for video agent display.
    """
    
    # Get customer_id from token (token uses 'user_id' key)
    customer_id = current_user.get("user_id")
    
    loan = db.query(Loan).filter(
        Loan.loan_id == loan_id,
        Loan.customer_id == customer_id
    ).first()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()
    
    loan_context = get_loan_context(loan, customer, db)
    
    return {
        "loan": loan_context,
        "quick_questions": [
            "What is my next EMI due date?",
            "How much do I owe?",
            "Can I get a grace period?",
            "How do I enable Auto-Pay?",
            "What happens if I miss a payment?"
        ]
    }


@router.post("/transcribe-audio")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Transcribe audio to text using Sarvam AI STT.
    Automatically detects language.
    
    Returns: {
        "text": "transcribed question",
        "language": "hi",
        "detected": true
    }
    """
    
    try:
        # Read audio file
        audio_data = await audio_file.read()
        print(f"[Transcribe] Received audio file: {audio_file.filename}, size: {len(audio_data)} bytes, content_type: {audio_file.content_type}")
        
        # Check if audio file is too small
        if len(audio_data) < 1000:  # Less than 1KB
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please record for at least 2-3 seconds."
            )
        
        # Transcribe with Sarvam AI
        result = transcribe_audio_with_sarvam(audio_data, audio_file.filename)
        
        if not result:
            # Fallback: return error
            raise HTTPException(
                status_code=500, 
                detail="Speech-to-text service unavailable. Please type your question."
            )
        
        transcribed_text = result.get("text", "")
        detected_language = result.get("language", "en")
        
        print(f"[Sarvam STT] Transcribed text length: {len(transcribed_text)}")
        
        # Map Sarvam language codes to our codes
        language_map = {
            "hi-IN": "hi",
            "ta-IN": "ta",
            "te-IN": "te",
            "kn-IN": "kn",
            "ml-IN": "ml",
            "bn-IN": "bn",
            "gu-IN": "gu",
            "mr-IN": "mr",
            "en-IN": "en",
            "en-US": "en"
        }
        
        mapped_language = language_map.get(detected_language, detected_language[:2])
        
        # Check if transcription is empty
        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(
                status_code=400, 
                detail="No speech detected. Please speak clearly and try again. Make sure to speak for at least 2-3 seconds."
            )
        
        # If Sarvam didn't detect language, use heuristic
        if mapped_language == "auto":
            mapped_language = detect_language_from_text(transcribed_text)
        
        return {
            "text": transcribed_text,
            "language": mapped_language,
            "detected": True,
            "confidence": "high"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
