"""
Bank Officer Router

Endpoints:
  GET  /officer/dashboard              → Portfolio dashboard stats + chart data
  GET  /officer/search                 → Customer / loan search (OR logic)
  GET  /officer/loan-intelligence/{loan_id}  → Full loan intelligence panel
  GET  /officer/sentiment              → Sentiment summary across all customers
  POST /officer/sentiment/analyze-call → Transcribe audio + run sentiment analysis
  GET  /officer/customer/{customer_id}/interactions  → Full interaction history for a customer
  GET  /officer/customers/{customer_id}      → Customer full profile for officer
"""

import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from backend.db.database import get_db
from backend.db.models import (
    Customer, Loan, PaymentHistory,
    InteractionHistory, GraceRequest, RestructureRequest
)
from backend.routers.auth import get_current_officer
from backend.agents.collections_intelligence_agent import analyze_loan
from backend.agents.sentiment_agent import (
    aggregate_sentiment,
    analyze_and_store_interaction,
)
from backend.agents.llm_reasoning_agent import generate_recovery_recommendation
from analytics.npv_calculator import calculate_portfolio_npv

router = APIRouter(prefix="/officer", tags=["Bank Officer"])


# ─────────────────────────────────────────────
# Helper: Build Loan Summary Dict
# ─────────────────────────────────────────────

def build_loan_summary(loan: Loan, customer: Customer) -> dict:
    return {
        "loan_id":             loan.loan_id,
        "customer_id":         customer.customer_id,
        "customer_name":       customer.customer_name,
        "loan_type":           loan.loan_type,
        "loan_amount":         loan.loan_amount,
        "outstanding_balance": loan.outstanding_balance,
        "emi_amount":          loan.emi_amount,
        "emi_due_date":        loan.emi_due_date,
        "days_past_due":       loan.days_past_due,
        "risk_segment":        loan.risk_segment,
        "self_cure_probability": loan.self_cure_probability,
        "recommended_channel": loan.recommended_channel,
    }


# ─────────────────────────────────────────────
# GET /officer/dashboard
# ─────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(
    current_user: dict = Depends(get_current_officer),
    db: Session        = Depends(get_db)
):
    """
    Return portfolio-level dashboard statistics for the bank officer.

    Includes:
      - Total borrowers
      - High / Medium / Low risk account counts
      - Expected recovery
      - Self cure rate
      - NPV estimate
      - Risk distribution chart data
      - Recovery strategy mix chart data
    """

    # ── Fetch all loans ───────────────────────────────────────────
    all_loans    = db.query(Loan).all()
    all_customers = db.query(Customer).all()

    total_borrowers = len(all_customers)
    total_loans     = len(all_loans)

    # ── Risk counts ───────────────────────────────────────────────
    high_risk   = [l for l in all_loans if l.risk_segment == "High"]
    medium_risk = [l for l in all_loans if l.risk_segment == "Medium"]
    low_risk    = [l for l in all_loans if l.risk_segment == "Low"]

    # ── Self cure rate ────────────────────────────────────────────
    avg_self_cure = (
        sum(l.self_cure_probability for l in all_loans) / len(all_loans)
        if all_loans else 0.0
    )

    # ── Total outstanding ─────────────────────────────────────────
    total_outstanding = sum(l.outstanding_balance for l in all_loans)

    # ── Portfolio NPV ─────────────────────────────────────────────
    from analytics.risk_models import recommend_recovery_strategy
    loan_inputs = []
    for loan in all_loans:
        strategy = recommend_recovery_strategy(
            days_past_due         = loan.days_past_due,
            risk_segment          = loan.risk_segment or "Medium",
            self_cure_probability = loan.self_cure_probability or 0.5,
            outstanding_balance   = loan.outstanding_balance,
            missed_payments       = 0,
        )
        loan_inputs.append({
            "outstanding_balance":   loan.outstanding_balance,
            "strategy":              strategy["strategy"],
            "self_cure_probability": loan.self_cure_probability or 0.5,
        })

    portfolio_npv = calculate_portfolio_npv(loan_inputs)

    # ── Pending requests ──────────────────────────────────────────
    pending_grace       = db.query(GraceRequest).filter(GraceRequest.request_status == "Pending").count()
    pending_restructure = db.query(RestructureRequest).filter(RestructureRequest.request_status == "Pending").count()

    # ── Risk Distribution (for pie/bar chart) ─────────────────────
    risk_distribution = [
        {"segment": "High",   "count": len(high_risk),   "color": "#EF4444"},
        {"segment": "Medium", "count": len(medium_risk), "color": "#F59E0B"},
        {"segment": "Low",    "count": len(low_risk),    "color": "#10B981"},
    ]

    # ── Recovery Strategy Mix (for chart) ────────────────────────
    strategy_counts = {}
    for li in loan_inputs:
        strat = li["strategy"]
        strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

    recovery_strategy_mix = [
        {"strategy": k, "count": v}
        for k, v in sorted(strategy_counts.items(), key=lambda x: -x[1])
    ]

    # ── Overdue loans breakdown ───────────────────────────────────
    overdue_loans = [l for l in all_loans if l.days_past_due > 0]

    return {
        "summary": {
            "total_borrowers":          total_borrowers,
            "total_loans":              total_loans,
            "high_risk_accounts":       len(high_risk),
            "medium_risk_accounts":     len(medium_risk),
            "low_risk_accounts":        len(low_risk),
            "overdue_loans":            len(overdue_loans),
            "total_outstanding":        round(total_outstanding, 2),
            "expected_recovery":        portfolio_npv["total_expected_recovery"],
            "total_npv":                portfolio_npv["total_npv"],
            "overall_recovery_rate":    round(portfolio_npv["overall_recovery_rate"] * 100, 1),
            "self_cure_rate":           round(avg_self_cure * 100, 1),
            "pending_grace_requests":   pending_grace,
            "pending_restructure_requests": pending_restructure,
        },
        "charts": {
            "risk_distribution":    risk_distribution,
            "recovery_strategy_mix": recovery_strategy_mix,
        }
    }


# ─────────────────────────────────────────────
# GET /officer/search
# ─────────────────────────────────────────────

@router.get("/search")
def search_customers(
    loan_id:      Optional[str] = Query(None, description="Search by Loan ID"),
    customer_id:  Optional[str] = Query(None, description="Search by Customer ID"),
    name:         Optional[str] = Query(None, description="Search by Customer Name"),
    loan_type:    Optional[str] = Query(None, description="Search by Loan Type"),
    risk_segment: Optional[str] = Query(None, description="Search by Risk Segment"),
    current_user: dict          = Depends(get_current_officer),
    db: Session                 = Depends(get_db)
):
    """
    Search customers and loans using OR logic across all filters.

    At least one search parameter must be provided.
    Returns a list of matching loan records with customer details.
    """
    if not any([loan_id, customer_id, name, loan_type, risk_segment]):
        raise HTTPException(
            status_code = 400,
            detail      = "At least one search parameter is required: loan_id, customer_id, name, loan_type, or risk_segment."
        )

    # ── Build filter conditions (OR logic) ────────────────────────
    conditions = []

    if loan_id:
        conditions.append(Loan.loan_id.ilike(f"%{loan_id}%"))

    if loan_type:
        conditions.append(Loan.loan_type.ilike(f"%{loan_type}%"))

    if risk_segment:
        conditions.append(Loan.risk_segment.ilike(f"%{risk_segment}%"))

    # ── Customer-based filters (join required) ────────────────────
    customer_ids_from_search = []

    if customer_id:
        matched = db.query(Customer.customer_id).filter(
            Customer.customer_id.ilike(f"%{customer_id}%")
        ).all()
        customer_ids_from_search.extend([c[0] for c in matched])

    if name:
        matched = db.query(Customer.customer_id).filter(
            Customer.customer_name.ilike(f"%{name}%")
        ).all()
        customer_ids_from_search.extend([c[0] for c in matched])

    if customer_ids_from_search:
        conditions.append(Loan.customer_id.in_(customer_ids_from_search))

    # ── Execute query ─────────────────────────────────────────────
    if not conditions:
        return {"results": [], "total": 0}

    matched_loans = (
        db.query(Loan)
        .filter(or_(*conditions))
        .order_by(Loan.days_past_due.desc())
        .limit(50)
        .all()
    )

    # ── Build results ─────────────────────────────────────────────
    results = []
    for loan in matched_loans:
        customer = db.query(Customer).filter(
            Customer.customer_id == loan.customer_id
        ).first()
        if customer:
            results.append(build_loan_summary(loan, customer))

    return {
        "results": results,
        "total":   len(results),
    }


# ─────────────────────────────────────────────
# GET /officer/loan-intelligence/{loan_id}
# ─────────────────────────────────────────────

@router.get("/loan-intelligence/{loan_id}")
def get_loan_intelligence(
    loan_id:      str,
    current_user: dict  = Depends(get_current_officer),
    db: Session         = Depends(get_db)
):
    """
    Full Loan Intelligence Panel for bank officers.

    Returns:
      - Loan details
      - Customer details
      - Payment history + trend
      - Risk analytics (delinquency score, VaR, self cure)
      - Sentiment & tonality analysis
      - Last 3 interaction summaries
      - Recovery recommendation (LLM-generated narrative)
      - NPV analysis
      - Policy validation
      - Grace / Restructure request history
    """

    # ── Fetch Loan ────────────────────────────────────────────────
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found.")

    # ── Fetch Customer ────────────────────────────────────────────
    customer = db.query(Customer).filter(Customer.customer_id == loan.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # ── Payment History ───────────────────────────────────────────
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
            "emi_amount":     loan.emi_amount,
        }
        for p in payments
    ]

    # ── Analytics ─────────────────────────────────────────────────
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

    # ── Interactions (last 3) ─────────────────────────────────────
    interactions = (
        db.query(InteractionHistory)
        .filter(InteractionHistory.customer_id == loan.customer_id)
        .order_by(InteractionHistory.interaction_time.desc())
        .limit(3)
        .all()
    )
    interaction_dicts = [
        {
            "interaction_id":      i.interaction_id,
            "interaction_type":    i.interaction_type,
            "interaction_time":    i.interaction_time,
            "sentiment_score":     i.sentiment_score,
            "tonality_score":      i.tonality_score,
            "interaction_summary": i.interaction_summary,
        }
        for i in interactions
    ]

    # ── Sentiment Aggregation ─────────────────────────────────────
    sentiment_summary = aggregate_sentiment(interaction_dicts)

    # ── LLM Recovery Recommendation ──────────────────────────────
    context = {
        "customer_profile": {
            "customer_name":    customer.customer_name,
            "credit_score":     customer.credit_score,
            "monthly_income":   customer.monthly_income,
            "preferred_channel": customer.preferred_channel,
        },
        "loans": [{
            "loan_id":             loan.loan_id,
            "loan_type":           loan.loan_type,
            "outstanding_balance": loan.outstanding_balance,
            "emi_amount":          loan.emi_amount,
            "days_past_due":       loan.days_past_due,
            "risk_segment":        analytics.get("risk_segment"),
        }],
        "payment_history":  payment_dicts[:3],
        "interactions":     interaction_dicts,
        "vector_memories":  [],
    }

    llm_recommendation = generate_recovery_recommendation(
        context   = context,
        analytics = analytics,
    )

    # ── Policy Validation ─────────────────────────────────────────
    from backend.agents.policy_guardrail_agent import validate_recovery_recommendation
    policy_validation = validate_recovery_recommendation(
        strategy            = analytics.get("recovery_strategy", {}).get("strategy", "Standard Follow-Up"),
        risk_segment        = analytics.get("risk_segment", "Low"),
        days_past_due       = loan.days_past_due,
        outstanding_balance = loan.outstanding_balance,
    )

    # ── Grace Request History ─────────────────────────────────────
    grace_requests = (
        db.query(GraceRequest)
        .filter(GraceRequest.loan_id == loan_id)
        .order_by(GraceRequest.request_date.desc())
        .all()
    )
    grace_history = [
        {
            "request_id":       gr.request_id,
            "request_status":   gr.request_status,
            "decision_comment": gr.decision_comment,
            "request_date":     gr.request_date,
            "decision_date":    gr.decision_date,
            "approved_by":      gr.approved_by,
        }
        for gr in grace_requests
    ]

    # ── Restructure Request History ───────────────────────────────
    restructure_requests = (
        db.query(RestructureRequest)
        .filter(RestructureRequest.loan_id == loan_id)
        .order_by(RestructureRequest.request_date.desc())
        .all()
    )
    restructure_history = [
        {
            "request_id":       rr.request_id,
            "request_status":   rr.request_status,
            "decision_comment": rr.decision_comment,
            "request_date":     rr.request_date,
            "decision_date":    rr.decision_date,
            "approved_by":      rr.approved_by,
        }
        for rr in restructure_requests
    ]

    return {
        # ── Loan Details ──────────────────────────────────────────
        "loan": {
            "loan_id":             loan.loan_id,
            "loan_type":           loan.loan_type,
            "loan_amount":         loan.loan_amount,
            "interest_rate":       loan.interest_rate,
            "emi_amount":          loan.emi_amount,
            "emi_due_date":        loan.emi_due_date,
            "outstanding_balance": loan.outstanding_balance,
            "days_past_due":       loan.days_past_due,
        },

        # ── Customer Details ──────────────────────────────────────
        "customer": {
            "customer_id":      customer.customer_id,
            "customer_name":    customer.customer_name,
            "mobile_number":    customer.mobile_number,
            "email_id":         customer.email_id,
            "credit_score":     customer.credit_score,
            "monthly_income":   customer.monthly_income,
            "preferred_channel": customer.preferred_channel,
            "preferred_language": customer.preferred_language,
        },

        # ── Analytics ─────────────────────────────────────────────
        "analytics": {
            "risk_segment":          analytics.get("risk_segment"),
            "self_cure_probability": analytics.get("self_cure_probability"),
            "delinquency_score":     analytics.get("delinquency_score"),
            "value_at_risk":         analytics.get("value_at_risk"),
            "payment_trend":         analytics.get("payment_trend"),
            "recovery_strategy":     analytics.get("recovery_strategy"),
            "recommended_channel":   analytics.get("recommended_channel"),
            "npv_result":            analytics.get("npv_result"),
            "strategy_comparison":   analytics.get("strategy_comparison", [])[:3],
        },

        # ── Sentiment ─────────────────────────────────────────────
        "sentiment": sentiment_summary,

        # ── Interactions ──────────────────────────────────────────
        "interactions":        interaction_dicts,

        # ── Payment History ───────────────────────────────────────
        "payment_history":     payment_dicts,

        # ── LLM Recommendation ────────────────────────────────────
        "llm_recommendation":  llm_recommendation,

        # ── Policy Validation ─────────────────────────────────────
        "policy_validation":   policy_validation,

        # ── Request History ───────────────────────────────────────
        "grace_history":       grace_history,
        "restructure_history": restructure_history,
    }


# ─────────────────────────────────────────────
# GET /officer/sentiment
# ─────────────────────────────────────────────

@router.get("/sentiment")
def get_sentiment_overview(
    current_user: dict = Depends(get_current_officer),
    db: Session        = Depends(get_db)
):
    """
    Return a sentiment overview across all customers.

    Returns:
      - summary: total_customers, positive/neutral/negative counts
      - customers: list of per-customer sentiment info (last 3 interactions)
      - all_customers: lightweight list for dropdowns (id + name)
    """
    all_customers = db.query(Customer).all()

    positive_count = 0
    neutral_count  = 0
    negative_count = 0

    customer_rows = []

    for customer in all_customers:
        interactions = (
            db.query(InteractionHistory)
            .filter(InteractionHistory.customer_id == customer.customer_id)
            .order_by(InteractionHistory.interaction_time.desc())
            .limit(3)
            .all()
        )

        if not interactions:
            continue

        interaction_dicts = [
            {
                "interaction_id":      i.interaction_id,
                "interaction_type":    i.interaction_type,
                "interaction_time":    i.interaction_time,
                "sentiment_score":     i.sentiment_score,
                "tonality_score":      i.tonality_score,
                "interaction_summary": i.interaction_summary,
                "conversation_text":   i.conversation_text,
            }
            for i in interactions
        ]

        # Aggregate sentiment for this customer
        sentiment = aggregate_sentiment(interaction_dicts)

        dominant = sentiment.get("dominant_tonality", "Neutral")
        if dominant == "Positive":
            positive_count += 1
        elif dominant == "Negative":
            negative_count += 1
        else:
            neutral_count += 1

        # Trend: compare latest vs previous score
        scores = [i.sentiment_score for i in interactions if i.sentiment_score is not None]
        trend = "Stable"
        if len(scores) >= 2:
            if scores[0] > scores[1] + 0.1:
                trend = "Improving"
            elif scores[0] < scores[1] - 0.1:
                trend = "Deteriorating"

        avg_score = sentiment.get("avg_sentiment_score", 0.0) or 0.0

        # All-time interactions count
        total_count = db.query(InteractionHistory).filter(
            InteractionHistory.customer_id == customer.customer_id
        ).count()

        customer_rows.append({
            # identity
            "customer_id":          customer.customer_id,
            "customer_name":        customer.customer_name,
            # tonality fields (both naming conventions for safety)
            "dominant_tonality":    dominant,
            "last3_tonality":       dominant,
            # sentiment score fields
            "avg_sentiment_score":  avg_score,
            "average_sentiment":    avg_score,       # expected by frontend scoreBar()
            "last3_sentiment":      avg_score,       # expected by frontend headerScore
            # trend fields
            "trend":                trend,
            "last3_trend":          trend,           # expected by frontend headerTrend
            "sentiment_trend":      trend,           # fallback alias
            # interaction counts
            "interaction_count":    len(interaction_dicts),
            "total_interactions":   total_count,     # expected by frontend subtitle
            # recent interactions list (expected by frontend .map())
            "recent_interactions":  interaction_dicts,
            "interactions":         interaction_dicts,
            # last interaction preview
            "last_interaction":     interactions[0].interaction_time if interactions else None,
            "last_summary":         interactions[0].interaction_summary if interactions else None,
            "last_type":            interactions[0].interaction_type if interactions else None,
        })

    # Sort: Negative first, then by avg score ascending
    customer_rows.sort(key=lambda c: (
        0 if c["dominant_tonality"] == "Negative" else (1 if c["dominant_tonality"] == "Neutral" else 2),
        c["avg_sentiment_score"]
    ))

    return {
        "summary": {
            "total_customers": len(customer_rows),
            "positive_count":  positive_count,
            "neutral_count":   neutral_count,
            "negative_count":  negative_count,
        },
        "customers":     customer_rows,
        "all_customers": [
            {"customer_id": c.customer_id, "customer_name": c.customer_name}
            for c in all_customers
        ],
    }


# ─────────────────────────────────────────────
# POST /officer/sentiment/analyze-call
# ─────────────────────────────────────────────

@router.post("/sentiment/analyze-call")
async def analyze_call_audio(
    customer_id: str          = Form(...),
    audio_file:  UploadFile   = File(...),
    current_user: dict        = Depends(get_current_officer),
    db: Session               = Depends(get_db),
):
    """
    Accept an audio file (upload or recorded blob), transcribe it with
    OpenAI Whisper (tiny model – runs locally, no API key needed),
    run sentiment analysis, save to InteractionHistory, and return results.

    Form fields:
      - customer_id  (str)
      - audio_file   (binary audio – mp3 / wav / m4a / webm / ogg / flac)
    """
    # ── 1. Validate customer ──────────────────────────────────────
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")

    # ── 2. Save upload to a temp file ────────────────────────────
    suffix = os.path.splitext(audio_file.filename or "audio.webm")[1] or ".webm"
    tmp_path = None
    transcript = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            contents = await audio_file.read()
            tmp.write(contents)

        # ── 3. Transcribe with Whisper ────────────────────────────
        try:
            import whisper as _whisper
            model = _whisper.load_model("tiny")          # ~39 MB, fast
            result = model.transcribe(tmp_path, fp16=False)
            transcript = result.get("text", "").strip()
        except Exception as whisper_err:
            print(f"[AnalyzeCall] Whisper error: {whisper_err}")
            # Graceful fallback: use filename as a stub transcript
            transcript = (
                f"[Transcription unavailable – Whisper error: {whisper_err}] "
                f"Audio file: {audio_file.filename}"
            )

    finally:
        # Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    if not transcript:
        transcript = "[No speech detected in the audio file.]"

    # ── 4. Sentiment + summary + save to DB ──────────────────────
    result_dict = analyze_and_store_interaction(
        db                = db,
        customer_id       = customer_id,
        interaction_type  = "Call",
        conversation_text = transcript,
        customer_name     = customer.customer_name,
    )

    return {
        "success":            True,
        "customer_id":        customer_id,
        "customer_name":      customer.customer_name,
        "transcript":         transcript,
        "sentiment_score":    result_dict["sentiment_score"],
        "tonality":           result_dict["tonality_score"],
        "interaction_summary": result_dict["interaction_summary"],
        "interaction_id":     result_dict.get("interaction_id"),
    }


# ─────────────────────────────────────────────
# GET /officer/customer/{customer_id}/interactions
# ─────────────────────────────────────────────

@router.get("/customer/{customer_id}/interactions")
def get_customer_interactions_for_officer(
    customer_id:  str,
    current_user: dict  = Depends(get_current_officer),
    db: Session         = Depends(get_db)
):
    """
    Return full interaction history for a customer (for officer view).

    Returns:
      - chat_sessions: list of chat sessions with messages
      - calls: list of call interactions with transcript + summary
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

    # ── Chat Sessions ─────────────────────────────────────────────
    from backend.db.models import ChatSession, ChatMessage

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.customer_id == customer_id)
        .order_by(ChatSession.last_updated.desc())
        .all()
    )

    # Keywords that indicate negative / distressed customer messages
    _NEG_KEYWORDS = {
        "can't pay", "cannot pay", "unable to pay", "no money", "broke",
        "struggling", "hardship", "difficult", "problem", "trouble",
        "lost job", "lost my job", "unemployed", "no income", "no funds",
        "angry", "frustrated", "unfair", "ridiculous", "disgusting",
        "threatening", "legal action", "sue", "complaint", "complain",
        "harassment", "harassing", "stop calling", "do not call",
        "never", "never paying", "refuse", "refusing", "won't pay",
        "why so much", "too high", "overcharged", "wrong amount",
        "bad service", "terrible", "worst", "awful", "horrible",
        "this is wrong", "mistake", "error", "incorrect",
        "please help", "desperate", "emergency", "crisis",
        "depressed", "stressed", "anxiety", "worried", "scared",
    }

    def _classify_message(role: str, text: str) -> str:
        if role != "user":
            return "Neutral"
        lower = text.lower()
        for kw in _NEG_KEYWORDS:
            if kw in lower:
                return "Negative"
        # Exclamation-heavy or all-caps short messages are often negative
        if text.count("!") >= 2:
            return "Negative"
        if len(text) <= 60 and text.isupper() and len(text) > 5:
            return "Negative"
        return "Neutral"

    chat_sessions = []
    for s in sessions:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.session_id)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )
        chat_sessions.append({
            "session_id":    s.session_id,
            "session_title": s.session_title,
            "created_at":    s.created_at,
            "last_updated":  s.last_updated,
            "messages": [
                {
                    "message_id":      m.message_id,
                    "role":            m.role,
                    "message_text":    m.message_text,
                    "timestamp":       m.timestamp,
                    "sentiment_label": _classify_message(m.role, m.message_text or ""),
                }
                for m in messages
            ],
        })

    # ── Call Interactions ─────────────────────────────────────────
    calls = (
        db.query(InteractionHistory)
        .filter(
            InteractionHistory.customer_id    == customer_id,
            InteractionHistory.interaction_type == "Call",
        )
        .order_by(InteractionHistory.interaction_time.desc())
        .all()
    )

    call_list = [
        {
            "interaction_id":      c.interaction_id,
            "interaction_time":    c.interaction_time,
            "sentiment_score":     c.sentiment_score,
            "tonality_score":      c.tonality_score,
            "interaction_summary": c.interaction_summary,
            "conversation_text":   c.conversation_text,
        }
        for c in calls
    ]

    return {
        "customer_id":   customer_id,
        "customer_name": customer.customer_name,
        "chat_sessions": chat_sessions,
        "calls":         call_list,
    }


# ─────────────────────────────────────────────
# GET /officer/customers/{customer_id}
# ─────────────────────────────────────────────

@router.get("/customers/{customer_id}")
def get_customer_for_officer(
    customer_id:  str,
    current_user: dict  = Depends(get_current_officer),
    db: Session         = Depends(get_db)
):
    """
    Return full customer profile and all loans for officer view.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()

    loan_summaries = [build_loan_summary(l, customer) for l in loans]

    total_outstanding = sum(l.outstanding_balance for l in loans)
    high_risk_loans   = [l for l in loans if l.risk_segment == "High"]

    # Latest interactions
    interactions = (
        db.query(InteractionHistory)
        .filter(InteractionHistory.customer_id == customer_id)
        .order_by(InteractionHistory.interaction_time.desc())
        .limit(5)
        .all()
    )

    return {
        "customer": {
            "customer_id":      customer.customer_id,
            "customer_name":    customer.customer_name,
            "mobile_number":    customer.mobile_number,
            "email_id":         customer.email_id,
            "credit_score":     customer.credit_score,
            "monthly_income":   customer.monthly_income,
            "preferred_channel": customer.preferred_channel,
            "preferred_language": customer.preferred_language,
            "relationship_assessment": customer.relationship_assessment,
        },
        "loans":              loan_summaries,
        "total_loans":        len(loans),
        "total_outstanding":  total_outstanding,
        "high_risk_loans":    len(high_risk_loans),
        "interactions": [
            {
                "interaction_type":    i.interaction_type,
                "interaction_time":    i.interaction_time,
                "sentiment_score":     i.sentiment_score,
                "tonality_score":      i.tonality_score,
                "interaction_summary": i.interaction_summary,
            }
            for i in interactions
        ],
    }


# ─────────────────────────────────────────────
# OFFICER CHAT  (/officer/chat/sessions/...)
# ─────────────────────────────────────────────
# Reuses ChatSession / ChatMessage tables.
# Officer sessions are stored with a synthetic customer_id
# equal to  "OFFICER:<officer_id>"  so they never mix with
# real customer sessions.
# ─────────────────────────────────────────────

from backend.db.models import ChatSession, ChatMessage
from backend.langgraph.workflow import run_chat_response
from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional

class _OfficerNewSession(_BaseModel):
    session_title: _Optional[str] = "General Collections Chat"

class _OfficerSendMsg(_BaseModel):
    message: str
    loan_id: _Optional[str] = None


def _officer_session_owner(officer_id: str) -> str:
    """Synthetic 'customer_id' used to isolate officer chat sessions."""
    return f"OFFICER:{officer_id}"


def _fmt_officer_session(session: ChatSession, db: Session) -> dict:
    count = db.query(ChatMessage).filter(ChatMessage.session_id == session.session_id).count()
    last  = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.timestamp.desc())
        .first()
    )
    return {
        "session_id":    session.session_id,
        "session_title": session.session_title,
        "created_at":    session.created_at,
        "last_updated":  session.last_updated,
        "message_count": count,
        "last_message":  (last.message_text[:80] + "...") if last and len(last.message_text) > 80 else (last.message_text if last else None),
    }


@router.get("/chat/sessions")
def officer_list_sessions(
    current_user: dict = Depends(get_current_officer),
    db: Session        = Depends(get_db)
):
    owner_id = _officer_session_owner(current_user["user_id"])
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.customer_id == owner_id)
        .order_by(ChatSession.last_updated.desc())
        .all()
    )
    return {"sessions": [_fmt_officer_session(s, db) for s in sessions], "total": len(sessions)}


@router.post("/chat/sessions", status_code=201)
def officer_create_session(
    body:         _OfficerNewSession,
    current_user: dict    = Depends(get_current_officer),
    db: Session           = Depends(get_db)
):
    from datetime import datetime as _dt
    owner_id = _officer_session_owner(current_user["user_id"])
    now      = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    session = ChatSession(
        customer_id   = owner_id,
        session_title = body.session_title or "General Collections Chat",
        created_at    = now,
        last_updated  = now,
    )
    db.add(session); db.commit(); db.refresh(session)

    welcome = ChatMessage(
        session_id   = session.session_id,
        role         = "assistant",
        message_text = (
            "Hello! I'm your Collections Intelligence AI assistant. I can help you with:\n"
            "• Portfolio risk analysis and recovery strategies\n"
            "• Loan-specific sentiment and behaviour analysis\n"
            "• Grace period and restructure decision support\n"
            "• Customer outreach channel recommendations\n\n"
            "How can I assist you today?"
        ),
        timestamp    = now,
    )
    db.add(welcome); db.commit()

    return {
        "success":    True,
        "session_id": session.session_id,
        "session":    _fmt_officer_session(session, db),
    }


@router.get("/chat/sessions/{session_id}")
def officer_get_session(
    session_id:   str,
    current_user: dict  = Depends(get_current_officer),
    db: Session         = Depends(get_db)
):
    owner_id = _officer_session_owner(current_user["user_id"])
    session  = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == owner_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    return {
        "session_id":    session.session_id,
        "session_title": session.session_title,
        "messages": [
            {"role": m.role, "message_text": m.message_text, "timestamp": m.timestamp}
            for m in messages
        ],
    }


@router.post("/chat/sessions/{session_id}/message")
def officer_send_message(
    session_id:   str,
    body:         _OfficerSendMsg,
    current_user: dict    = Depends(get_current_officer),
    db: Session           = Depends(get_db)
):
    from datetime import datetime as _dt
    owner_id = _officer_session_owner(current_user["user_id"])
    session  = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == owner_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save user message
    user_msg = ChatMessage(
        session_id   = session_id,
        role         = "user",
        message_text = body.message.strip(),
        timestamp    = now,
    )
    db.add(user_msg); db.commit()

    # ── Greeting intercept — bypass LLM for hi/hello in loan-wise chat ──
    _msg_lower   = body.message.strip().lower()
    _GREET_EXACT = {"hi", "hello", "hey", "hii", "helo", "hi!", "hello!", "hey!",
                    "good morning", "good afternoon", "good evening"}
    _is_greeting = (_msg_lower in _GREET_EXACT or
                    any(_msg_lower.startswith(g + " ") for g in ("hi", "hello", "hey")))

    # Extract effective loan_id
    ai_text = ""
    effective_loan_id = body.loan_id
    if not effective_loan_id:
        import re as _re
        prefix_match = _re.match(r'\[Loan:\s*(\S+)\]', body.message.strip(), _re.IGNORECASE)
        if prefix_match:
            effective_loan_id = prefix_match.group(1).upper()

    if _is_greeting and effective_loan_id:
        # Loan-wise greeting — show loan-specific welcome for the officer
        loan_obj = db.query(Loan).filter(Loan.loan_id == effective_loan_id.strip().upper()).first()
        if loan_obj:
            from backend.db.models import Customer as _Customer
            cust = db.query(_Customer).filter(_Customer.customer_id == loan_obj.customer_id).first()
            cust_name = cust.customer_name if cust else loan_obj.customer_id
            ai_text = (
                f"Loan {loan_obj.loan_id} — {loan_obj.loan_type} | Customer: {cust_name}\n"
                f"  Outstanding  : ₹{loan_obj.outstanding_balance:,.0f}\n"
                f"  EMI          : ₹{loan_obj.emi_amount:,.0f} due {loan_obj.emi_due_date}\n"
                f"  Days Past Due: {loan_obj.days_past_due} | Risk: {loan_obj.risk_segment}\n\n"
                "You can ask about payment history, behaviour, EMI details, grace/restructure status, or recovery strategy."
            )
        else:
            ai_text = f"Loan {effective_loan_id} not found. Please check the Loan ID and try again."

    if not ai_text:
        # Try LangGraph workflow (using a pseudo customer_id for context)
        try:
            # If a loan_id is given, we can pull a real customer_id from it
            target_customer = None
            if effective_loan_id:
                loan_obj = db.query(Loan).filter(Loan.loan_id == effective_loan_id.strip().upper()).first()
                if loan_obj:
                    target_customer = loan_obj.customer_id

            if target_customer:
                result  = run_chat_response(
                    db          = db,
                    customer_id = target_customer,
                    session_id  = session_id,
                    user_query  = body.message.strip(),
                    loan_id     = effective_loan_id,
                    is_officer  = True,
                )
                ai_text = result.get("llm_response", "")
        except Exception as e:
            print(f"[OfficerChat] Workflow error: {e}")

        # Fallback: officer-specific rule-based response
        if not ai_text:
            ai_text = _officer_fallback(body.message, effective_loan_id, db, session_id)

    ai_msg = ChatMessage(
        session_id   = session_id,
        role         = "assistant",
        message_text = ai_text,
        timestamp    = _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(ai_msg)
    session.last_updated = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    if session.session_title in ("General Collections Chat", "New Chat"):
        session.session_title = body.message.strip()[:50]
    db.commit(); db.refresh(ai_msg)

    return {
        "success":    True,
        "session_id": session_id,
        "user_message": {"role": "user", "message_text": body.message.strip(), "timestamp": now},
        "ai_response":  {"role": "assistant", "message_text": ai_text, "timestamp": ai_msg.timestamp},
    }


@router.delete("/chat/sessions/{session_id}")
def officer_delete_session(
    session_id:   str,
    current_user: dict  = Depends(get_current_officer),
    db: Session         = Depends(get_db)
):
    owner_id = _officer_session_owner(current_user["user_id"])
    session  = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == owner_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session); db.commit()
    return {"success": True, "message": "Session deleted."}


def _officer_fallback(
    message:    str,
    loan_id:    _Optional[str],
    db:         Session,
    session_id: str = "",
) -> str:
    """
    Rule-based fallback for officer chat when LLM / Ollama is unavailable.

    Handles:
      1. Previous questions / chat history
      2. Loan-wise queries  (grace, sentiment, outreach, recovery)
      3. Overdue accounts summary
      4. Portfolio overview
      5. Risk segment breakdown
      6. Pending requests
      7. Recovery strategies
      8. Generic help (actionable, not a canned intro)
    """
    msg = message.strip().lower()

    # ── 1. Loan-wise queries ──────────────────────────────────────
    if loan_id:
        loan = db.query(Loan).filter(Loan.loan_id == loan_id.strip().upper()).first()
        if loan:
            customer = db.query(Customer).filter(Customer.customer_id == loan.customer_id).first()
            name = customer.customer_name if customer else "the customer"

            # ── Payment history — checked FIRST to avoid hist_kw clash ──
            if any(k in msg for k in ["payment history", "previous payment", "past payment",
                                       "payment record", "show payment", "repayment"]):
                payments = (
                    db.query(PaymentHistory)
                    .filter(PaymentHistory.loan_id == loan.loan_id)
                    .order_by(PaymentHistory.payment_date.desc())
                    .limit(6)
                    .all()
                )
                if not payments:
                    return f"No payment records found for loan {loan.loan_id}."
                lines = "\n".join(
                    f"  {i+1}. {p.payment_date}  —  ₹{p.payment_amount:,.0f}  via {p.payment_method}"
                    for i, p in enumerate(payments)
                )
                total_paid = sum(p.payment_amount for p in payments)
                return (
                    f"Payment History for {loan.loan_id} ({name}) — last {len(payments)} records:\n"
                    f"{lines}\n\n"
                    f"Total paid in this view: ₹{total_paid:,.0f}"
                )

            # ── Payment behaviour — checked before sentiment to avoid clash ──
            if any(k in msg for k in ["payment behaviour", "payment behavior",
                                       "paying behaviour", "payment pattern",
                                       "paying pattern", "consistency", "irregular", "regular"]):
                payments = (
                    db.query(PaymentHistory)
                    .filter(PaymentHistory.loan_id == loan.loan_id)
                    .order_by(PaymentHistory.payment_date.desc())
                    .all()
                )
                if not payments:
                    return f"No payment data available to assess behaviour for loan {loan.loan_id}."
                total        = len(payments)
                on_time      = sum(1 for p in payments if p.payment_amount >= loan.emi_amount * 0.95)
                missed_ratio = (total - on_time) / total if total > 0 else 0
                avg_amount   = sum(p.payment_amount for p in payments) / total
                if missed_ratio < 0.1:
                    pattern = "✅ Consistent payer — very low risk of default."
                elif missed_ratio < 0.3:
                    pattern = "⚠️ Occasional delays — moderate risk. Monitor closely."
                else:
                    pattern = "🔴 Irregular payment behaviour — high default risk. Consider escalation."
                return (
                    f"Payment Behaviour for {loan.loan_id} ({name}):\n"
                    f"  Total Payments Recorded : {total}\n"
                    f"  On-Time / Full Payments : {on_time}\n"
                    f"  Avg Payment Amount      : ₹{avg_amount:,.0f}  (EMI: ₹{loan.emi_amount:,.0f})\n"
                    f"  Days Past Due (current) : {loan.days_past_due}\n\n"
                    f"Assessment: {pattern}"
                )

            if any(k in msg for k in ["grace", "approve", "eligible"]):
                if loan.days_past_due < 30:
                    return (
                        f"Loan {loan.loan_id} ({name}): With {loan.days_past_due} days past due "
                        f"and a {loan.risk_segment} risk segment, this customer is likely eligible "
                        f"for a grace period of up to 7 days. "
                        f"Recommend approving if no prior grace was granted this cycle."
                    )
                return (
                    f"Loan {loan.loan_id} has {loan.days_past_due} DPD (High Risk). "
                    f"Grace period eligibility is low. Consider restructuring instead."
                )

            # ── Sentiment — only tonality/mood/attitude, NOT "behaviour" ──
            if any(k in msg for k in ["sentiment", "tonality", "attitude", "mood"]):
                interactions = (
                    db.query(InteractionHistory)
                    .filter(InteractionHistory.customer_id == loan.customer_id)
                    .order_by(InteractionHistory.interaction_time.desc())
                    .limit(3)
                    .all()
                )
                if interactions:
                    latest = interactions[0]
                    trend_lines = "\n".join(
                        f"  - [{i.interaction_type}] {i.interaction_time[:10]}  "
                        f"{i.tonality_score} (score: {i.sentiment_score:.2f})"
                        for i in interactions
                    )
                    return (
                        f"Sentiment trend for {name} ({loan.loan_id}) — last {len(interactions)} interactions:\n"
                        f"{trend_lines}\n\n"
                        f"Latest summary: {latest.interaction_summary or 'N/A'}"
                    )
                return f"No interaction history found for loan {loan.loan_id}."

            if any(k in msg for k in ["channel", "outreach", "contact", "reach"]):
                return (
                    f"Recommended outreach channel for {name} ({loan.loan_id}): "
                    f"{loan.recommended_channel or 'Phone'}. "
                    f"Risk: {loan.risk_segment}, DPD: {loan.days_past_due}, "
                    f"Self-cure probability: {(loan.self_cure_probability or 0) * 100:.0f}%."
                )

            if any(k in msg for k in ["recovery", "strategy", "action", "recommend", "probability"]):
                return (
                    f"Recovery strategy for {loan.loan_id} ({name}): "
                    f"Outstanding ₹{loan.outstanding_balance:,.0f}, "
                    f"{loan.days_past_due} DPD, Risk: {loan.risk_segment}. "
                    f"Recommended channel: {loan.recommended_channel or 'Phone'}. "
                    f"Self-cure probability: {(loan.self_cure_probability or 0) * 100:.0f}%. "
                    f"Suggested action: {'Immediate escalation' if loan.days_past_due > 30 else 'Friendly payment reminder'}."
                )

            if any(k in msg for k in ["emi", "due date", "next emi", "next payment", "due on", "when is"]):
                return (
                    f"EMI Details for {loan.loan_id} ({name}):\n"
                    f"  Next EMI Due Date : {loan.emi_due_date}\n"
                    f"  EMI Amount        : ₹{loan.emi_amount:,.0f}\n"
                    f"  Days Past Due     : {loan.days_past_due}\n"
                    f"  Outstanding Bal   : ₹{loan.outstanding_balance:,.0f}\n"
                    + (
                        f"\n⚠️ This account is overdue by {loan.days_past_due} days."
                        if loan.days_past_due > 0 else
                        "\n✅ Account is current — no overdue."
                    )
                )

            if any(k in msg for k in ["payments due", "how many payment", "number of payment",
                                       "pending payment", "overdue payment", "total payment",
                                       "payment count", "how many emi", "emis due", "emi pending"]):
                dpd = loan.days_past_due
                overdue_emis = max(0, dpd // 30) if dpd > 0 else 0
                status_line = (
                    f"⚠️ {dpd} days past due — approximately {overdue_emis} overdue EMI(s). Action recommended."
                    if dpd > 0
                    else "✅ Account is current — no overdue EMIs."
                )
                return (
                    f"Payment Status for {loan.loan_id} ({name}):\n"
                    f"  Next EMI Due Date  : {loan.emi_due_date}\n"
                    f"  Monthly EMI Amount : ₹{loan.emi_amount:,.0f}\n"
                    f"  Outstanding Balance: ₹{loan.outstanding_balance:,.0f}\n"
                    f"  {status_line}"
                )

            return (
                f"Loan {loan.loan_id} — Customer: {name}, Type: {loan.loan_type}, "
                f"Outstanding: ₹{loan.outstanding_balance:,.0f}, EMI: ₹{loan.emi_amount:,.0f}, "
                f"DPD: {loan.days_past_due}, Risk: {loan.risk_segment}."
            )
        return f"Loan '{loan_id}' not found in the system."

    # ── 2. Previous questions / session history ────────────────────
    _hist_kw = [
        "previous", "earlier", "last question", "before",
        "list down", "what did i ask", "what have i asked",
        "my questions", "past question", "recap", "conversation",
    ]
    if any(k in msg for k in _hist_kw) and session_id:
        past = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )
        past = past[:-1] if past else []
        if past:
            lines = "\n".join(
                f"  {i+1}. {m.message_text}  ({m.timestamp[11:16] if m.timestamp else ''})"
                for i, m in enumerate(past)
            )
            return (
                f"Here are the questions asked in this session:\n{lines}\n\n"
                "Would you like me to follow up on any of these?"
            )
        return (
            "This is the start of the session — no previous questions yet. "
            "You can ask about a loan ID, portfolio overview, risk segments, or pending requests."
        )

    # ── 3. Overdue / delinquent accounts ──────────────────────────
    if any(k in msg for k in ["overdue", "past due", "delinquent", "delayed", "missed"]):
        overdue_loans = (
            db.query(Loan)
            .filter(Loan.days_past_due > 0)
            .order_by(Loan.days_past_due.desc())
            .all()
        )
        if not overdue_loans:
            return "No overdue accounts found in the portfolio currently."
        total_bal = sum(l.outstanding_balance for l in overdue_loans)
        high   = [l for l in overdue_loans if l.risk_segment == "High"]
        medium = [l for l in overdue_loans if l.risk_segment == "Medium"]
        low    = [l for l in overdue_loans if l.risk_segment == "Low"]
        top5   = overdue_loans[:5]
        top5_lines = "\n".join(
            f"  - {l.loan_id} ({l.loan_type}) — {l.days_past_due} DPD, "
            f"₹{l.outstanding_balance:,.0f}, Risk: {l.risk_segment}"
            for l in top5
        )
        return (
            f"Overdue Accounts Summary: {len(overdue_loans)} accounts, "
            f"total outstanding ₹{total_bal:,.0f}.\n"
            f"  High risk: {len(high)}  |  Medium: {len(medium)}  |  Low: {len(low)}\n\n"
            f"Top {len(top5)} by DPD:\n{top5_lines}"
        )

    # ── 4. Portfolio overview ─────────────────────────────────────
    if any(k in msg for k in ["portfolio", "total", "outstanding", "overview", "summary"]):
        all_loans   = db.query(Loan).all()
        total_out   = sum(l.outstanding_balance for l in all_loans)
        high_risk   = sum(1 for l in all_loans if l.risk_segment == "High")
        med_risk    = sum(1 for l in all_loans if l.risk_segment == "Medium")
        low_risk    = sum(1 for l in all_loans if l.risk_segment == "Low")
        overdue_cnt = sum(1 for l in all_loans if l.days_past_due > 0)
        avg_dpd     = (
            sum(l.days_past_due for l in all_loans) / len(all_loans)
            if all_loans else 0
        )
        return (
            f"Portfolio Overview ({len(all_loans)} loans):\n"
            f"  Total Outstanding:  ₹{total_out:,.0f}\n"
            f"  Risk Breakdown:     High {high_risk}  |  Medium {med_risk}  |  Low {low_risk}\n"
            f"  Overdue Accounts:   {overdue_cnt}\n"
            f"  Avg Days Past Due:  {avg_dpd:.1f} days"
        )

    # ── 5. Risk segment breakdown ─────────────────────────────────
    if any(k in msg for k in ["high risk", "high-risk", "risk segment", "how many risk"]):
        high   = db.query(Loan).filter(Loan.risk_segment == "High").count()
        medium = db.query(Loan).filter(Loan.risk_segment == "Medium").count()
        low    = db.query(Loan).filter(Loan.risk_segment == "Low").count()
        return (
            f"Risk Segment Breakdown:\n"
            f"  High Risk:   {high} loans\n"
            f"  Medium Risk: {medium} loans\n"
            f"  Low Risk:    {low} loans"
        )

    # ── 6. Pending requests ───────────────────────────────────────
    if any(k in msg for k in ["pending", "grace request", "restructure request", "requests"]):
        g = db.query(GraceRequest).filter(GraceRequest.request_status == "Pending").count()
        r = db.query(RestructureRequest).filter(RestructureRequest.request_status == "Pending").count()
        return (
            f"Pending Requests:\n"
            f"  Grace Period:   {g} pending\n"
            f"  Restructuring:  {r} pending\n\n"
            "You can review them in the Loan Intelligence panel."
        )

    # ── 7. Recovery strategies ────────────────────────────────────
    if any(k in msg for k in ["recovery strateg", "best strateg", "strateg"]):
        return (
            "Key recovery strategies in the portfolio:\n"
            "  - Self-Cure Monitoring: low-DPD customers likely to pay independently\n"
            "  - Friendly Reminder (SMS/Email): for 1-15 DPD accounts\n"
            "  - Proactive Outreach (Phone/WhatsApp): for 15-30 DPD accounts\n"
            "  - Negotiation & Restructuring: for 30+ DPD with cooperative customers\n"
            "  - Legal / Escalation: for 60+ DPD non-cooperative cases\n\n"
            "Ask about a specific loan ID for a tailored recommendation."
        )

    # ── 8. Generic help (actionable, not canned) ──────────────────
    return (
        "I can help you with:\n"
        "  - Portfolio overview — 'Show portfolio summary'\n"
        "  - Overdue accounts  — 'Show overdue accounts'\n"
        "  - Specific loan     — enter Loan ID in the sidebar and ask\n"
        "  - Risk breakdown    — 'How many high risk loans?'\n"
        "  - Pending requests  — 'Show pending grace requests'\n"
        "  - Recovery strategy — 'What are the best recovery strategies?'"
    )
