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
import os, tempfile
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

@router.post("/self-cure/transcribe")
async def self_cure_transcribe(
    audio_file:    UploadFile         = File(...),
    language_hint: Optional[str]      = Form(None),   # BCP-47 hint e.g. 'hi-IN'
    current_user:  dict               = Depends(get_current_customer),
):
    """
    Transcribe a voice recording and return:
      - transcript       (str)  — ENGLISH text (what user said, translated to English)
      - detected_language (str) — detected language display name ('Hindi', 'Tamil', etc.)
      - language_code    (str)  — BCP-47 code ('hi-IN', etc.)

    Pipeline:
      1. Saaras STT → native script (Devanagari, Tamil script, etc.)
      2. Language validation/correction (map Urdu→Hindi, Chinese→Telugu, etc.)
      3. Mayura translation → English text
      4. Return English transcript + corrected source language
      5. Chat endpoint uses corrected language for response translation
    """
    # ── Save temp file ────────────────────────────────────────────
    suffix = os.path.splitext(audio_file.filename or "audio.webm")[1] or ".webm"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        transcript = ""
        detected_lang = ""
        source_lang_code = ""
        sarvam_api_key = os.getenv("SARVAM_API_KEY", "")

        SARVAM_LANG_MAP = {
            "hi-IN": "Hindi",   "ta-IN": "Tamil",   "te-IN": "Telugu",
            "kn-IN": "Kannada", "ml-IN": "Malayalam","mr-IN": "Marathi",
            "gu-IN": "Gujarati","bn-IN": "Bengali", "en-IN": "English",
            "en-US": "English", "pa-IN": "Punjabi", "od-IN": "Odia",
        }

        # ── Language correction map (commonly confused languages) ──
        # Maps non-Indian languages to their Indian equivalents
        LANG_CORRECTION_MAP = {
            "ur-PK": "hi-IN",  # Urdu → Hindi (script/pronunciation similar)
            "ur-IN": "hi-IN",  # Urdu (India) → Hindi
            "zh-CN": "te-IN",  # Chinese → Telugu (common Saaras misdetection)
            "zh-TW": "te-IN",  # Chinese Traditional → Telugu
            "ar-SA": "hi-IN",  # Arabic → Hindi (fallback)
            "fa-IR": "hi-IN",  # Farsi → Hindi (fallback)
            "ko-KR": "hi-IN",  # Korean → Hindi (fallback for audio quality issues)
            "ja-JP": "hi-IN",  # Japanese → Hindi (fallback)
            "th-TH": "hi-IN",  # Thai → Hindi (fallback)
            "vi-VN": "hi-IN",  # Vietnamese → Hindi (fallback)
            "id-ID": "hi-IN",  # Indonesian → Hindi (fallback)
            "ru-RU": "hi-IN",  # Russian → Hindi (Cyrillic misdetection)
            "uk-UA": "hi-IN",  # Ukrainian → Hindi (Cyrillic misdetection)
            "bg-BG": "hi-IN",  # Bulgarian → Hindi (Cyrillic misdetection)
            "sr-RS": "hi-IN",  # Serbian → Hindi (Cyrillic misdetection)
            "tr-TR": "hi-IN",  # Turkish → Hindi (fallback)
            "pl-PL": "hi-IN",  # Polish → Hindi (fallback)
            "cs-CZ": "hi-IN",  # Czech → Hindi (fallback)
        }

        # ── Determine language hint to use ────────────────────────
        # Always pass language hint (default to Hindi if not provided)
        hint_to_use = language_hint if language_hint and language_hint != "en-IN" else "hi-IN"
        print(f"[Transcribe] Language hint: {language_hint} → Using: {hint_to_use}")

        # ── Strategy: Use Whisper for Indian languages (more reliable) ──
        # Saaras often misdetects Indian languages as Russian/Chinese/etc.
        # Whisper is more reliable for Indian languages but slower
        use_whisper_first = hint_to_use != "en-IN"  # Use Whisper for all non-English
        
        # ── Primary: Whisper for Indian languages ─────────────────
        if use_whisper_first:
            print(f"[Transcribe] Using Whisper for {hint_to_use} (more reliable than Saaras)")
            try:
                import whisper
                model = whisper.load_model("tiny")
                result = model.transcribe(
                    tmp_path,
                    language=hint_to_use.split("-")[0] if hint_to_use != "en-IN" else "en",
                    task="transcribe"
                )
                native_transcript = result["text"].strip()
                source_lang_code = hint_to_use
                detected_lang = SARVAM_LANG_MAP.get(source_lang_code, "Hindi")
                
                print(f"✅ [Transcribe] Whisper: language={detected_lang}, transcript='{native_transcript[:60]}'")
                
                # Translate to English if not English
                transcript = native_transcript
                if not source_lang_code.startswith("en") and native_transcript:
                    try:
                        async with httpx.AsyncClient(timeout=20.0) as client:
                            mayura_resp = await client.post(
                                "https://api.sarvam.ai/translate",
                                headers={
                                    "api-subscription-key": sarvam_api_key,
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "input":                 native_transcript,
                                    "source_language_code":  source_lang_code,
                                    "target_language_code":  "en-IN",
                                    "speaker_gender":        "Male",
                                    "mode":                  "formal",
                                    "model":                 "mayura:v1",
                                    "enable_preprocessing":  True,
                                },
                            )
                        if mayura_resp.status_code == 200:
                            translated = mayura_resp.json().get("translated_text", "").strip()
                            if translated:
                                transcript = translated
                                print(f"✅ [Transcribe] Mayura translated: '{transcript[:60]}'")
                        else:
                            print(f"⚠️ [Transcribe] Mayura failed, using native transcript")
                    except Exception as e:
                        print(f"⚠️ [Transcribe] Mayura error: {e}, using native transcript")
                
                if transcript:
                    return {
                        "transcript":         transcript,
                        "detected_language":  detected_lang,
                        "language_code":      source_lang_code,
                    }
            except Exception as e:
                print(f"⚠️ [Transcribe] Whisper error: {e}, falling back to Saaras")
        
        # ── Fallback: Sarvam Saaras STT (for English or Whisper failure) ──
        if sarvam_api_key:
            print(f"[Transcribe] Using Saaras STT (English or fallback)")
            try:
                import httpx
                with open(tmp_path, "rb") as f:
                    audio_bytes = f.read()

                _MIME_MAP = {
                    ".webm": "audio/webm", ".ogg": "audio/ogg",
                    ".mp4":  "audio/mp4",  ".m4a": "audio/mp4",
                    ".wav":  "audio/wav",  ".mp3": "audio/mpeg",
                }
                audio_mime = _MIME_MAP.get(suffix.lower(), "audio/webm")
                fname      = audio_file.filename or f"audio{suffix}"

                saaras_data: dict = {
                    "model":                 "saaras:v2",
                    "with_timestamps":       "false",
                    "with_disfluencies":     "false",
                    "language_code":         hint_to_use,  # Use the hint determined earlier
                }
                print(f"[Transcribe] ===== SAARAS STT REQUEST =====")
                print(f"[Transcribe] Using hint: {hint_to_use}")
                print(f"[Transcribe] Audio file: {fname}, size: {len(audio_bytes)} bytes, mime: {audio_mime}")

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.sarvam.ai/speech-to-text",
                        headers={"api-subscription-key": sarvam_api_key},
                        files={"file": (fname, audio_bytes, audio_mime)},
                        data=saaras_data,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    native_transcript = (data.get("transcript") or "").strip()
                    source_lang_code  = data.get("language_code", "") or language_hint or ""
                    original_detected = source_lang_code  # Store original for logging
                    
                    print(f"[Transcribe] ===== SAARAS RESPONSE =====")
                    print(f"[Transcribe] Detected language: {source_lang_code}")
                    print(f"[Transcribe] Native transcript: '{native_transcript}'")
                    print(f"[Transcribe] Transcript length: {len(native_transcript)} chars")
                    
                    # ── Validate and correct language (Indian languages only) ──
                    # If Saaras detected a non-Indian language, map it to closest Indian language
                    if source_lang_code in LANG_CORRECTION_MAP:
                        corrected_code = LANG_CORRECTION_MAP[source_lang_code]
                        print(f"⚠️ [Transcribe] Language correction: {source_lang_code} → {corrected_code}")
                        source_lang_code = corrected_code
                    
                    # If still not in our supported list, default to Hindi
                    if source_lang_code not in SARVAM_LANG_MAP:
                        print(f"⚠️ [Transcribe] Unsupported language '{source_lang_code}', defaulting to Hindi")
                        source_lang_code = "hi-IN"
                    
                    detected_lang = SARVAM_LANG_MAP.get(source_lang_code, "Hindi")
                    
                    if original_detected != source_lang_code:
                        print(f"✅ [Transcribe] Corrected: {original_detected} → {source_lang_code} ({detected_lang})")
                    
                    # ── Validate transcript quality ──────────────────────────
                    # Check if transcript contains non-Indian/Latin characters (indicates wrong detection)
                    is_invalid_script = False
                    if native_transcript:
                        # Check for East Asian (CJK), Cyrillic, or other non-Indian scripts
                        import re
                        has_cjk = bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', native_transcript))
                        has_cyrillic = bool(re.search(r'[\u0400-\u04ff]', native_transcript))
                        has_arabic_persian = bool(re.search(r'[\u0600-\u06ff\u0750-\u077f]', native_transcript))
                        
                        if has_cjk or has_cyrillic or (has_arabic_persian and source_lang_code == "hi-IN"):
                            is_invalid_script = True
                            print(f"❌ [Transcribe] INVALID SCRIPT DETECTED in transcript!")
                            print(f"❌ [Transcribe] Transcript contains: CJK={has_cjk}, Cyrillic={has_cyrillic}, Arabic={has_arabic_persian}")
                            print(f"❌ [Transcribe] This is NOT a valid Indian language transcription")
                            print(f"❌ [Transcribe] Rejecting transcript: '{native_transcript}'")
                            # Don't process this garbage - let Whisper handle it
                            native_transcript = ""
                            transcript = ""
                    
                    if not is_invalid_script:
                        print(f"✅ [Transcribe] Script validation passed")
                    
                    print(f"✅ [Transcribe] Saaras: language={detected_lang} ({source_lang_code}), native='{native_transcript[:60] if native_transcript else '(rejected)'}'")
                    
                    # ── Translate to English using Mayura (if not English) ────
                    transcript = ""  # Will be set if valid
                    if native_transcript and not is_invalid_script:  # Only translate if valid
                        transcript = native_transcript  # Default to native
                        if not source_lang_code.startswith("en"):
                            try:
                                async with httpx.AsyncClient(timeout=20.0) as client:
                                    mayura_resp = await client.post(
                                        "https://api.sarvam.ai/translate",
                                        headers={
                                            "api-subscription-key": sarvam_api_key,
                                            "Content-Type": "application/json",
                                        },
                                        json={
                                            "input":                 native_transcript,
                                            "source_language_code":  source_lang_code,
                                            "target_language_code":  "en-IN",
                                            "speaker_gender":        "Male",
                                            "mode":                  "formal",
                                            "model":                 "mayura:v1",
                                            "enable_preprocessing":  True,
                                        },
                                    )
                                if mayura_resp.status_code == 200:
                                    translated = mayura_resp.json().get("translated_text", "").strip()
                                    if translated:
                                        transcript = translated
                                        print(f"✅ [Transcribe] Mayura translated: '{transcript[:60]}'")
                                    else:
                                        print(f"⚠️ [Transcribe] Mayura returned empty, using native transcript")
                                else:
                                    print(f"⚠️ [Transcribe] Mayura HTTP {mayura_resp.status_code}, using native transcript")
                            except Exception as e:
                                print(f"⚠️ [Transcribe] Mayura error: {e}, using native transcript")
                        else:
                            print(f"✅ [Transcribe] English detected, no translation needed")
                    
                    if transcript:
                        return {
                            "transcript":         transcript,  # English text (translated by Mayura)
                            "detected_language":  detected_lang or "auto",
                            "language_code":      source_lang_code or "",
                        }
                else:
                    print(f"[Transcribe] Sarvam {resp.status_code}: {resp.text[:200]}")
            except Exception as sarvam_err:
                print(f"[Transcribe] Saaras error: {sarvam_err}")

        # ── Fallback: Whisper tiny ────────────────────────────────
        if not transcript:
            print("[Transcribe] Falling back to Whisper tiny")
            try:
                import whisper
                model          = whisper.load_model("tiny")
                whisper_result = model.transcribe(tmp_path)
                transcript = (whisper_result.get("text") or "").strip()
                from backend.agents.copilot_agent import detect_language
                detected_lang = detect_language(transcript)
                source_lang_code = {
                    "Hindi": "hi-IN", "Tamil": "ta-IN", "Telugu": "te-IN",
                    "Kannada": "kn-IN", "Malayalam": "ml-IN",
                }.get(detected_lang, "")
            except Exception as w_err:
                print(f"[Transcribe] Whisper error: {w_err}")

        if not transcript:
            raise HTTPException(status_code=422, detail="Could not transcribe audio. Please speak clearly and try again.")

        return {
            "transcript":         transcript,           # English text (for UI + LLM)
            "detected_language":  detected_lang or "auto",
            "language_code":      source_lang_code or "",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transcribe] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
