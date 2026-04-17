"""
Customer Router

Endpoints:
  GET  /customer/profile              → Get customer profile + relationship assessment
  GET  /customer/loans                → Get all loans for the customer
  GET  /customer/loans/{loan_id}      → Get loan details with analytics
  GET  /customer/loans/{loan_id}/payments → Get payment history for a loan
  GET  /customer/interactions         → Get interaction history
  GET  /customer/dashboard            → Get customer dashboard summary
  POST /customer/self-cure/chat       → Multilingual self-cure bot (Feature 3)
  POST /customer/self-cure/transcribe → Voice → text for Self-Cure Bot mic input
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import os, tempfile, subprocess
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.db.database import get_db
from backend.db.models import (
    Customer, Loan, PaymentHistory, InteractionHistory,
    GraceRequest, RestructureRequest
)
from backend.routers.auth import get_current_customer
from backend.agents.collections_intelligence_agent import analyze_loan
from backend.agents.llm_reasoning_agent import generate_relationship_assessment

# Import Sarvam AI SDK
from sarvamai import SarvamAI

router = APIRouter(prefix="/customer", tags=["Customer"])


# ─────────────────────────────────────────────
# Helper: format loan dict
# ─────────────────────────────────────────────

def format_loan(loan: Loan, db: Session) -> dict:
    """Format a Loan ORM object into a response dict with grace/restructure status."""

    # Latest grace request status
    grace = (
        db.query(GraceRequest)
        .filter(GraceRequest.loan_id == loan.loan_id)
        .order_by(GraceRequest.request_date.desc())
        .first()
    )

    # Latest restructure request status
    restructure = (
        db.query(RestructureRequest)
        .filter(RestructureRequest.loan_id == loan.loan_id)
        .order_by(RestructureRequest.request_date.desc())
        .first()
    )

    return {
        "loan_id":               loan.loan_id,
        "loan_type":             loan.loan_type,
        "loan_amount":           loan.loan_amount,
        "interest_rate":         loan.interest_rate,
        "emi_amount":            loan.emi_amount,
        "emi_due_date":          loan.emi_due_date,
        "outstanding_balance":   loan.outstanding_balance,
        "days_past_due":         loan.days_past_due,
        "risk_segment":          loan.risk_segment,
        "self_cure_probability": loan.self_cure_probability,
        "recommended_channel":   loan.recommended_channel,
        "grace_status":          grace.request_status          if grace       else "None",
        "grace_comment":         grace.decision_comment        if grace       else None,
        "restructure_status":    restructure.request_status    if restructure else "None",
        "restructure_comment":   restructure.decision_comment  if restructure else None,
    }


# ─────────────────────────────────────────────
# GET /customer/profile
# ─────────────────────────────────────────────

@router.get("/profile")
def get_customer_profile(
    current_user: dict  = Depends(get_current_customer),
    db: Session         = Depends(get_db)
):
    """
    Return full customer profile including relationship assessment.
    Relationship assessment is generated/refreshed via LLM if needed.
    """
    customer_id = current_user["user_id"]

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Fetch loans and payment history for assessment context
    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()
    loan_dicts = [format_loan(l, db) for l in loans]

    payments = []
    if loans:
        payments = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.loan_id == loans[0].loan_id)
            .order_by(PaymentHistory.payment_date.desc())
            .limit(6)
            .all()
        )
        payments = [
            {
                "payment_date":   p.payment_date,
                "payment_amount": p.payment_amount,
                "payment_method": p.payment_method,
            }
            for p in payments
        ]

    interactions = (
        db.query(InteractionHistory)
        .filter(InteractionHistory.customer_id == customer_id)
        .order_by(InteractionHistory.interaction_time.desc())
        .limit(3)
        .all()
    )
    interaction_dicts = [
        {"interaction_type": i.interaction_type, "interaction_summary": i.interaction_summary}
        for i in interactions
    ]

    # Generate / refresh relationship assessment
    assessment = customer.relationship_assessment
    if not assessment:
        assessment = generate_relationship_assessment(
            customer_name   = customer.customer_name,
            loans           = loan_dicts,
            payment_history = payments,
            interactions    = interaction_dicts,
        )
        # Persist updated assessment
        customer.relationship_assessment = assessment
        db.commit()

    # Total loan exposure
    total_exposure = sum(l.outstanding_balance for l in loans)

    return {
        "customer_id":             customer.customer_id,
        "customer_name":           customer.customer_name,
        "mobile_number":           customer.mobile_number,
        "email_id":                customer.email_id,
        "preferred_language":      customer.preferred_language,
        "preferred_channel":       customer.preferred_channel,
        "credit_score":            customer.credit_score,
        "monthly_income":          customer.monthly_income,
        "total_loan_exposure":     total_exposure,
        "relationship_assessment": assessment,
        "total_loans":             len(loans),
    }


# ─────────────────────────────────────────────
# GET /customer/loans
# ─────────────────────────────────────────────

@router.get("/loans")
def get_customer_loans(
    current_user: dict = Depends(get_current_customer),
    db: Session        = Depends(get_db)
):
    """
    Return all loans for the logged-in customer.
    Includes grace and restructure request status for each loan.
    """
    customer_id = current_user["user_id"]

    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()
    if not loans:
        return {"loans": [], "total": 0}

    return {
        "loans": [format_loan(l, db) for l in loans],
        "total": len(loans),
    }


# ─────────────────────────────────────────────
# GET /customer/loans/{loan_id}
# ─────────────────────────────────────────────

@router.get("/loans/{loan_id}")
def get_loan_detail(
    loan_id:      str,
    current_user: dict    = Depends(get_current_customer),
    db: Session           = Depends(get_db)
):
    """
    Return detailed loan information including:
      - Loan details
      - Payment history
      - Delinquency score
      - Risk analytics
      - AI recommendation
    """
    customer_id = current_user["user_id"]

    loan = db.query(Loan).filter(
        Loan.loan_id    == loan_id,
        Loan.customer_id == customer_id
    ).first()

    if not loan:
        raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found.")

    # Payment history
    payments = (
        db.query(PaymentHistory)
        .filter(PaymentHistory.loan_id == loan_id)
        .order_by(PaymentHistory.payment_date.desc())
        .limit(12)
        .all()
    )
    payment_dicts = [
        {
            "payment_date":   p.payment_date,
            "payment_amount": p.payment_amount,
            "payment_method": p.payment_method,
        }
        for p in payments
    ]

    # Customer info for analytics
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()

    # Run analytics
    analytics = analyze_loan(
        days_past_due       = loan.days_past_due,
        credit_score        = customer.credit_score or 650,
        monthly_income      = customer.monthly_income or 30000.0,
        emi_amount          = loan.emi_amount,
        outstanding_balance = loan.outstanding_balance,
        preferred_channel   = customer.preferred_channel or "Email",
        payment_history     = [
            {"payment_amount": p["payment_amount"], "emi_amount": loan.emi_amount}
            for p in payment_dicts
        ],
    )

    # Grace & restructure status
    grace = (
        db.query(GraceRequest)
        .filter(GraceRequest.loan_id == loan_id)
        .order_by(GraceRequest.request_date.desc())
        .first()
    )
    restructure = (
        db.query(RestructureRequest)
        .filter(RestructureRequest.loan_id == loan_id)
        .order_by(RestructureRequest.request_date.desc())
        .first()
    )

    return {
        "loan_id":               loan.loan_id,
        "loan_type":             loan.loan_type,
        "loan_amount":           loan.loan_amount,
        "interest_rate":         loan.interest_rate,
        "emi_amount":            loan.emi_amount,
        "emi_due_date":          loan.emi_due_date,
        "outstanding_balance":   loan.outstanding_balance,
        "days_past_due":         loan.days_past_due,

        # Analytics
        "risk_segment":          analytics.get("risk_segment"),
        "self_cure_probability": analytics.get("self_cure_probability"),
        "delinquency_score":     analytics.get("delinquency_score"),
        "value_at_risk":         analytics.get("value_at_risk"),
        "payment_trend":         analytics.get("payment_trend"),
        "recovery_strategy":     analytics.get("recovery_strategy"),
        "recommended_channel":   analytics.get("recommended_channel"),

        # Payment history (for graph)
        "payment_history": payment_dicts,

        # Request statuses
        "grace_status":          grace.request_status       if grace       else "None",
        "grace_comment":         grace.decision_comment     if grace       else None,
        "restructure_status":    restructure.request_status if restructure else "None",
        "restructure_comment":   restructure.decision_comment if restructure else None,
    }


# ─────────────────────────────────────────────
# GET /customer/loans/{loan_id}/payments
# ─────────────────────────────────────────────

@router.get("/loans/{loan_id}/payments")
def get_loan_payments(
    loan_id:      str,
    current_user: dict  = Depends(get_current_customer),
    db: Session         = Depends(get_db)
):
    """
    Return full payment history for a specific loan.
    """
    customer_id = current_user["user_id"]

    loan = db.query(Loan).filter(
        Loan.loan_id     == loan_id,
        Loan.customer_id == customer_id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found.")

    payments = (
        db.query(PaymentHistory)
        .filter(PaymentHistory.loan_id == loan_id)
        .order_by(PaymentHistory.payment_date.desc())
        .all()
    )

    return {
        "loan_id":  loan_id,
        "payments": [
            {
                "payment_id":     p.payment_id,
                "payment_date":   p.payment_date,
                "payment_amount": p.payment_amount,
                "payment_method": p.payment_method,
                "emi_amount":     loan.emi_amount,
            }
            for p in payments
        ],
        "total": len(payments),
    }


# ─────────────────────────────────────────────
# GET /customer/interactions
# ─────────────────────────────────────────────

@router.get("/interactions")
def get_customer_interactions(
    current_user: dict = Depends(get_current_customer),
    db: Session        = Depends(get_db)
):
    """
    Return interaction history for the logged-in customer.
    """
    customer_id = current_user["user_id"]

    interactions = (
        db.query(InteractionHistory)
        .filter(InteractionHistory.customer_id == customer_id)
        .order_by(InteractionHistory.interaction_time.desc())
        .all()
    )

    return {
        "interactions": [
            {
                "interaction_id":      i.interaction_id,
                "interaction_type":    i.interaction_type,
                "interaction_time":    i.interaction_time,
                "sentiment_score":     i.sentiment_score,
                "tonality_score":      i.tonality_score,
                "interaction_summary": i.interaction_summary,
            }
            for i in interactions
        ],
        "total": len(interactions),
    }


# ─────────────────────────────────────────────
# GET /customer/dashboard
# ─────────────────────────────────────────────

@router.get("/dashboard")
def get_customer_dashboard(
    current_user: dict = Depends(get_current_customer),
    db: Session        = Depends(get_db)
):
    """
    Return a dashboard summary for the customer portal home page.
    """
    customer_id = current_user["user_id"]

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()

    total_exposure    = sum(l.outstanding_balance for l in loans)
    overdue_loans     = [l for l in loans if l.days_past_due > 0]
    pending_grace     = db.query(GraceRequest).filter(
        GraceRequest.customer_id  == customer_id,
        GraceRequest.request_status == "Pending"
    ).count()
    pending_restructure = db.query(RestructureRequest).filter(
        RestructureRequest.customer_id    == customer_id,
        RestructureRequest.request_status == "Pending"
    ).count()

    next_due = None
    if loans:
        next_due = min(loans, key=lambda l: l.emi_due_date).emi_due_date

    return {
        "customer_name":          customer.customer_name,
        "total_loans":            len(loans),
        "total_loan_exposure":    total_exposure,
        "overdue_loans":          len(overdue_loans),
        "next_emi_due_date":      next_due,
        "pending_grace_requests": pending_grace,
        "pending_restructure_requests": pending_restructure,
        "credit_score":           customer.credit_score,
        "preferred_channel":      customer.preferred_channel,
        "relationship_assessment": customer.relationship_assessment,
    }


# ═════════════════════════════════════════════════════════════════
# SELF-CURE BOT  (/customer/self-cure/chat)
# ═════════════════════════════════════════════════════════════════

class SelfCureRequest(BaseModel):
    message:  str
    stage:    Optional[str] = "greeting"   # conversation stage (client tracks + sends back)
    language: Optional[str] = "auto"       # detected language (sticky across turns)


@router.post("/self-cure/chat")
def self_cure_chat(
    body:         SelfCureRequest,
    current_user: dict    = Depends(get_current_customer),
    db: Session           = Depends(get_db),
):
    """
    One turn of the multilingual Self-Cure Bot conversation.

    The client is responsible for maintaining the conversation state
    (stage, language) and sending it back with each request.

    Request body:
        message  (str, required)  — customer's text input
        stage    (str, optional)  — current stage; defaults to "greeting"
        language (str, optional)  — detected language; "auto" = detect from message

    Returns:
        reply         (str)   — bot response text
        stage         (str)   — next stage to send with the following request
        quick_replies (list)  — pre-built button options (empty = free text)
        escalate      (bool)  — True when officer follow-up is needed
        language      (str)   — detected/carried language name
        saved         (bool)  — True when a DB record was written this turn
    """
    from backend.agents.self_cure_agent import run_self_cure_agent

    customer_id = current_user["user_id"]

    result = run_self_cure_agent(
        db          = db,
        customer_id = customer_id,
        message     = body.message,
        stage       = body.stage or "greeting",
        language    = body.language or "auto",
    )

    return result


# ═════════════════════════════════════════════════════════════════
# SELF-CURE VOICE TRANSCRIBE  (/customer/self-cure/transcribe)
# ═════════════════════════════════════════════════════════════════

# Constants for audio processing
MAX_CHUNK_SECONDS = 29

# Language mapping
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


@router.post("/self-cure/transcribe")
async def self_cure_transcribe(
    audio_file:    UploadFile         = File(...),
    language_hint: Optional[str]      = Form(None),   # BCP-47 hint e.g. 'hi-IN'
    current_user:  dict               = Depends(get_current_customer),
):
    """
    Transcribe voice recording using Sarvam AI Saaras v2.5 (PROVEN APPROACH).
    
    Returns:
      - transcript       (str)  — ENGLISH text (auto-translated by Saaras)
      - native_transcript (str) — NATIVE script text (Hindi, Tamil, etc.)
      - detected_language (str) — language display name ('Hindi', 'Tamil', etc.)
      - language_code    (str)  — BCP-47 code ('hi-IN', 'ta-IN', etc.)
    
    Pipeline (matches your working application):
      1. Convert audio to WAV (16kHz mono) - Saaras requirement
      2. Split into 29-second chunks - Saaras has 30s limit
      3. Transcribe each chunk with Saaras v2.5 using transcribe() method
      4. Translate to English using Mayura
      5. Return both native and English transcripts
    """
    print(f"\n{'='*60}")
    print(f"[Transcribe] ===== NEW TRANSCRIPTION REQUEST =====")
    print(f"[Transcribe] Filename: {audio_file.filename}")
    print(f"[Transcribe] Language hint: {language_hint}")
    print(f"{'='*60}\n")
    
    input_path = None
    wav_path = None
    chunks = []
    
    try:
        # ── Save uploaded file ────────────────────────────────────
        suffix = os.path.splitext(audio_file.filename or "audio.webm")[1] or ".webm"
        print(f"[Transcribe] Saving uploaded file with suffix: {suffix}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp.flush()
            input_path = tmp.name
        print(f"[Transcribe] Saved to: {input_path}, size: {len(content)} bytes")
        
        # ── Initialize Sarvam AI client ───────────────────────────
        sarvam_api_key = os.getenv("SARVAM_API_KEY", "")
        if not sarvam_api_key:
            raise HTTPException(status_code=500, detail="SARVAM_API_KEY not configured")
        
        client = SarvamAI(api_subscription_key=sarvam_api_key)
        
        # ── Convert to WAV (16kHz, mono) ──────────────────────────
        print(f"[Transcribe] Converting {audio_file.filename} to WAV format...")
        wav_path = _convert_to_wav(input_path)
        
        # ── Split into chunks (29s max) ───────────────────────────
        print(f"[Transcribe] Splitting audio into {MAX_CHUNK_SECONDS}s chunks...")
        chunks = _split_audio(wav_path)
        print(f"[Transcribe] Created {len(chunks)} chunk(s)")
        
        # ── Transcribe each chunk ─────────────────────────────────
        native_transcripts = []
        english_transcripts = []
        detected_lang_code = None
        
        for i, chunk_path in enumerate(chunks):
            print(f"[Transcribe] Processing chunk {i+1}/{len(chunks)}: {chunk_path}")
            
            with open(chunk_path, "rb") as audio_file_handle:
                # Use transcribe() method - returns NATIVE script (Hindi, Tamil, etc.)
                response = client.speech_to_text.transcribe(
                    file=audio_file_handle,
                    model="saaras:v3"  # Latest Saaras model
                )
            
            native_text = response.transcript.strip()
            chunk_lang = response.language_code
            
            print(f"✅ [Chunk {i+1}] Language: {chunk_lang}, Native text: '{native_text[:60]}'")
            
            if native_text:
                native_transcripts.append(native_text)
                detected_lang_code = chunk_lang
        
        # ── Combine native transcripts ────────────────────────────
        if not native_transcripts:
            raise HTTPException(
                status_code=422, 
                detail="Could not transcribe audio. Please speak clearly and try again."
            )
        
        final_native_transcript = " ".join(native_transcripts)
        detected_lang_code = detected_lang_code or language_hint or "hi-IN"
        detected_lang_name = SARVAM_LANG_MAP.get(detected_lang_code, "Hindi")
        
        # ── Translate to English using Mayura (for LLM processing) ─
        final_english_transcript = final_native_transcript  # Default fallback
        
        if not detected_lang_code.startswith("en"):
            print(f"[Transcribe] Translating {detected_lang_name} → English using Mayura...")
            try:
                translate_response = client.text.translate(
                    input=final_native_transcript,
                    source_language_code=detected_lang_code,
                    target_language_code="en-IN",
                    model="mayura:v1"
                )
                final_english_transcript = translate_response.translated_text.strip()
                print(f"✅ [Transcribe] Mayura translation: '{final_english_transcript[:60]}'")
            except Exception as e:
                print(f"⚠️ [Transcribe] Mayura translation failed: {e}, using native text")
        
        print(f"✅ [Transcribe] SUCCESS!")
        print(f"   Language: {detected_lang_name} ({detected_lang_code})")
        print(f"   Native text: '{final_native_transcript[:100]}'")
        print(f"   English text: '{final_english_transcript[:100]}'")
        
        return {
            "transcript":         final_english_transcript,  # English (for LLM)
            "native_transcript":  final_native_transcript,   # Original language (for UI display)
            "detected_language":  detected_lang_name,        # Display name
            "language_code":      detected_lang_code,        # BCP-47 code
        }
    
    except subprocess.CalledProcessError as e:
        print(f"❌ [Transcribe] FFmpeg error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Audio conversion failed. Please ensure audio file is valid."
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"❌ [Transcribe] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # ── Cleanup temporary files ───────────────────────────────
        for path in [input_path, wav_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass
        
        for chunk in chunks:
            if os.path.exists(chunk):
                try:
                    os.unlink(chunk)
                except Exception:
                    pass

