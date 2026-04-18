"""
Collections Agent Co-Pilot

Responsibilities:
  - Accept a call transcript (from Whisper or Sarvam STT)
  - Pull live customer context (loans, payments, interactions)
  - Run sentiment & tonality analysis on the transcript
  - Generate deterministic nudges from live DB data
  - Call LLM (Llama 3.1 via Ollama) for:
      * Suggested responses the officer can use
      * Root-cause diagnostic questions to ask the customer
  - Save CallSession + CopilotSuggestion to DB
  - Return fully structured result dict

Fallback:
  - If Ollama unavailable, rule-based suggestions are generated
    using transcript keywords + customer risk profile
"""

import json
import os
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.models import (
    Customer, Loan, PaymentHistory,
    InteractionHistory, GraceRequest, RestructureRequest,
    CallSession, CopilotSuggestion,
)
from backend.agents.sentiment_agent import (
    calculate_sentiment_score,
    classify_tonality,
)
from backend.agents.llm_reasoning_agent import call_ollama


# ─────────────────────────────────────────────
# Language Detection (lightweight keyword map)
# ─────────────────────────────────────────────

_LANG_MARKERS = {
    "Hindi":     ["नहीं", "मैं", "हूँ", "है", "कर", "नही", "पैसा", "लोन", "ईएमआई", "क्या"],
    "Tamil":     ["நான்", "இல்லை", "பணம்", "கடன்", "செலுத்த"],
    "Telugu":    ["నేను", "లేదు", "డబ్బు", "రుణం", "చెల్లించ"],
    "Kannada":   ["ನಾನು", "ಇಲ್ಲ", "ಹಣ", "ಸಾಲ"],
    "Malayalam": ["ഞാൻ", "ഇല്ല", "പണം", "വായ്പ"],
    "Marathi":   ["मी", "नाही", "पैसे", "कर्ज"],
    "Gujarati":  ["હું", "નથી", "પૈસા", "લોન"],
    "Bengali":   ["আমি", "না", "টাকা", "ঋণ"],
}


def detect_language(text: str) -> str:
    """Detect Indian language from transcript using Unicode markers."""
    for lang, markers in _LANG_MARKERS.items():
        if any(marker in text for marker in markers):
            return lang
    return "English"


# ─────────────────────────────────────────────
# Language → Sarvam language code map
# ─────────────────────────────────────────────

_SARVAM_LANG_CODES = {
    "Hindi":     "hi-IN",
    "Tamil":     "ta-IN",
    "Telugu":    "te-IN",
    "Kannada":   "kn-IN",
    "Malayalam": "ml-IN",
    "Marathi":   "mr-IN",
    "Gujarati":  "gu-IN",
    "Bengali":   "bn-IN",
}


# ─────────────────────────────────────────────
# Translate to English
# ─────────────────────────────────────────────

def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate text to English.

    Strategy:
      1. Try Sarvam Translate API  (fast, high quality for Indian languages)
      2. Fall back to Ollama LLM   (slower, works when Sarvam key missing)
      3. Return original text if both fail (graceful degradation)
    """
    if source_language == "English":
        return text

    # ── 1. Sarvam Translate API ───────────────────────────────────
    sarvam_key = os.getenv("SARVAM_API_KEY", "")
    source_code = _SARVAM_LANG_CODES.get(source_language, "")

    if sarvam_key and source_code:
        try:
            resp = requests.post(
                "https://api.sarvam.ai/translate",
                headers={
                    "api-subscription-key": sarvam_key,
                    "Content-Type": "application/json",
                },
                json={
                    "input":                   text,
                    "source_language_code":    source_code,
                    "target_language_code":    "en-IN",
                    "speaker_gender":          "Male",
                    "mode":                    "formal",
                    "model":                   "mayura:v1",
                    "enable_preprocessing":    False,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                translated = resp.json().get("translated_text", "").strip()
                if translated:
                    print(f"[CopilotAgent] Sarvam translated {source_language} → English ✅")
                    return translated
                print(f"[CopilotAgent] Sarvam returned empty translation, trying Ollama.")
            else:
                print(f"[CopilotAgent] Sarvam translate HTTP {resp.status_code}, trying Ollama.")
        except Exception as e:
            print(f"[CopilotAgent] Sarvam translate error: {e}, trying Ollama.")

    # ── 2. Ollama LLM fallback ────────────────────────────────────
    try:
        prompt = (
            f"Translate the following {source_language} text to English. "
            f"Return ONLY the translated English text, no explanations:\n\n{text}"
        )
        translated = call_ollama(prompt, system_prompt="You are a professional translator.")
        if translated and translated.strip():
            print(f"[CopilotAgent] Ollama translated {source_language} → English ✅")
            return translated.strip()
    except Exception as e:
        print(f"[CopilotAgent] Ollama translate error: {e}")

    # ── 3. Graceful degradation ───────────────────────────────────
    print(f"[CopilotAgent] Both translators failed — using original text.")
    return text


# ─────────────────────────────────────────────
# Build Nudges from Live DB Data (deterministic)
# ─────────────────────────────────────────────

def _build_nudges(
    customer: Customer,
    loans: list,
    interactions: list,
    grace_pending: int,
    restructure_pending: int,
) -> list:
    """
    Generate 2–4 contextual nudges from live customer data.
    No LLM required — purely rule-based from DB values.
    """
    nudges = []

    # ── Loan risk / DPD nudge ─────────────────────────────────────
    if loans:
        primary_loan = loans[0]
        dpd = primary_loan.days_past_due
        risk = primary_loan.risk_segment
        self_cure = primary_loan.self_cure_probability or 0.5

        if dpd > 60:
            nudges.append(
                f"⛔ {primary_loan.loan_id} is {dpd} days past due — critical risk. "
                "Legal escalation may be required."
            )
        elif dpd > 30:
            nudges.append(
                f"🔴 {primary_loan.loan_id} is {dpd} days past due ({risk} risk). "
                "Consider restructuring before legal action."
            )
        elif dpd > 0:
            nudges.append(
                f"⚠️ {primary_loan.loan_id} is {dpd} days past due. "
                f"Self-cure probability: {self_cure * 100:.0f}% — "
                f"{'grace period may suffice' if self_cure >= 0.6 else 'proactive outreach needed'}."
            )
        else:
            nudges.append(
                f"✅ {primary_loan.loan_id} is current (0 DPD). "
                f"Self-cure probability: {self_cure * 100:.0f}%."
            )

        # Outstanding balance nudge
        nudges.append(
            f"💰 Outstanding balance: ₹{primary_loan.outstanding_balance:,.0f} "
            f"| EMI: ₹{primary_loan.emi_amount:,.0f} | Due: {primary_loan.emi_due_date}"
        )

    # ── Last interaction nudge ────────────────────────────────────
    if interactions:
        last = interactions[0]
        nudges.append(
            f"📌 Last interaction ({last.interaction_type}, "
            f"{str(last.interaction_time)[:10]}): "
            f"{last.interaction_summary or 'No summary available.'}"
        )

    # ── Pending requests nudge ────────────────────────────────────
    if grace_pending > 0:
        nudges.append(
            f"📋 {grace_pending} pending grace request(s) for this customer — review before calling."
        )
    if restructure_pending > 0:
        nudges.append(
            f"📋 {restructure_pending} pending restructure request(s) — discuss eligibility on this call."
        )

    return nudges[:4]   # cap at 4 nudges


# ─────────────────────────────────────────────
# LLM Prompt Builder
# ─────────────────────────────────────────────

def _build_copilot_prompt(
    transcript: str,
    customer_name: str,
    customer_context: str,
    sentiment_score: float,
    tonality: str,
) -> tuple[str, str]:
    """
    Build system + user prompt for co-pilot LLM call.
    Returns (system_prompt, user_prompt).
    """
    system_prompt = (
        "You are an expert collections co-pilot AI assistant for bank officers in India. "
        "Analyse the call transcript and customer data provided. "
        "Return ONLY a valid JSON object — no markdown, no explanation, no extra text. "
        "The JSON must have exactly two keys: 'suggested_responses' and 'questions_to_ask'. "
        "Each key must contain a list of exactly 3 strings. "
        "Responses must be empathetic, professional, and in the context of Indian banking collections. "
        "Questions must help the officer perform root-cause analysis."
    )

    user_prompt = f"""
Customer: {customer_name}
Transcript of the call:
\"\"\"{transcript}\"\"\"

Customer Context:
{customer_context}

Sentiment Score: {sentiment_score:.2f} | Tonality: {tonality}

Based on the above, generate:
1. 3 suggested responses the officer can say to the customer
2. 3 root-cause diagnostic questions the officer should ask

Return ONLY this JSON (no other text):
{{
  "suggested_responses": ["<response 1>", "<response 2>", "<response 3>"],
  "questions_to_ask": ["<question 1>", "<question 2>", "<question 3>"]
}}
"""
    return system_prompt, user_prompt


# ─────────────────────────────────────────────
# Rule-based Fallback Suggestions
# ─────────────────────────────────────────────

def _fallback_suggestions(
    transcript: str,
    sentiment_score: float,
    dpd: int,
    risk_segment: str,
    self_cure: float,
) -> tuple[list, list]:
    """
    Generate rule-based suggestions when Ollama is unavailable.
    Returns (suggested_responses, questions_to_ask).
    """
    text = transcript.lower()

    # Suggested responses based on DPD + sentiment
    if dpd > 30 or sentiment_score < -0.5:
        responses = [
            "I completely understand the difficulty you're facing. Let me check all available options including grace period and restructuring for your loan.",
            "Thank you for being honest with me. Based on your situation, I'd like to discuss a repayment plan that fits your current income.",
            "We are here to support you, not to add pressure. Let me escalate your case to our senior officer for a customised solution.",
        ]
        questions = [
            "Can you tell me if this financial difficulty is temporary or is it likely to continue for the next few months?",
            "Have you faced similar situations before, and if so, how did you manage to recover?",
            "Are there any upcoming income sources — such as a business payment, salary, or asset sale — that could help clear the overdue?",
        ]
    elif sentiment_score < -0.2:
        responses = [
            "I appreciate you sharing your concern. Your next EMI is due soon — shall I walk you through the payment options available?",
            "I understand there may be some inconvenience. Let me see if a short grace period of 7 days can be arranged for you.",
            "Thank you for reaching out. I can see your payment history and you've been largely consistent — this delay can be resolved quickly.",
        ]
        questions = [
            "Is there a specific reason for this month's delay that we should note in your account?",
            "Would you be comfortable committing to a payment date in the next 5–7 days?",
            "Is your preferred payment method still UPI or would you like to use a payment link via WhatsApp?",
        ]
    else:
        responses = [
            "Thank you for your timely payments. I'm calling to confirm your upcoming EMI and ensure everything is in order.",
            "Your account is in good standing. Is there anything you'd like to know about your loan, prepayment, or balance?",
            "Great to connect with you. Your next EMI is coming up — shall I send a confirmation on WhatsApp?",
        ]
        questions = [
            "Is your registered mobile number and email still active for reminders?",
            "Are you interested in exploring prepayment options to reduce your overall interest burden?",
            "Do you have any other financial commitments we should be aware of while managing your EMI schedule?",
        ]

    return responses, questions


# ─────────────────────────────────────────────
# Main Copilot Agent Function
# ─────────────────────────────────────────────

def run_copilot_agent(
    db:          Session,
    customer_id: str,
    transcript:  str,
    officer_id:  str,
    loan_id:     str = None,
) -> dict:
    """
    Main entry point for the Co-Pilot agent.

    Args:
        db:          SQLAlchemy session
        customer_id: Target customer
        transcript:  Full transcribed text of the call
        officer_id:  Officer who uploaded the recording
        loan_id:     Optional — specific loan to focus on

    Returns:
        {
            call_session_id:     str,
            customer_name:       str,
            transcript:          str,
            language_detected:   str,
            sentiment_score:     float,
            tonality:            str,
            suggested_responses: list[str],
            questions_to_ask:    list[str],
            nudges:              list[str],
        }
    """

    # ── 1. Fetch customer ─────────────────────────────────────────
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": f"Customer {customer_id} not found."}

    # ── 2. Fetch loans ────────────────────────────────────────────
    if loan_id:
        loans = db.query(Loan).filter(Loan.loan_id == loan_id).all()
    else:
        loans = (
            db.query(Loan)
            .filter(Loan.customer_id == customer_id)
            .order_by(Loan.days_past_due.desc())
            .all()
        )

    # ── 3. Fetch recent interactions ──────────────────────────────
    interactions = (
        db.query(InteractionHistory)
        .filter(InteractionHistory.customer_id == customer_id)
        .order_by(InteractionHistory.interaction_time.desc())
        .limit(3)
        .all()
    )

    # ── 4. Pending grace + restructure requests ───────────────────
    grace_pending = (
        db.query(GraceRequest)
        .filter(
            GraceRequest.customer_id == customer_id,
            GraceRequest.request_status == "Pending",
        )
        .count()
    )
    restructure_pending = (
        db.query(RestructureRequest)
        .filter(
            RestructureRequest.customer_id == customer_id,
            RestructureRequest.request_status == "Pending",
        )
        .count()
    )

    # ── 5. Detect language ────────────────────────────────────────
    language_detected = detect_language(transcript)

    # ── 5b. Translate to English if needed ───────────────────────
    transcript_original = transcript    # always keep the raw transcript
    if language_detected != "English":
        print(f"[CopilotAgent] Detected language: {language_detected}. Translating to English…")
        transcript_english = translate_to_english(transcript, language_detected)
    else:
        transcript_english = transcript

    # Use the English version for sentiment + LLM analysis
    transcript_for_analysis = transcript_english

    # ── 6. Sentiment + tonality ───────────────────────────────────
    sentiment_score = calculate_sentiment_score(transcript_for_analysis)
    tonality        = classify_tonality(sentiment_score)

    # ── 7. Build nudges (deterministic, no LLM) ───────────────────
    nudges = _build_nudges(
        customer            = customer,
        loans               = loans,
        interactions        = interactions,
        grace_pending       = grace_pending,
        restructure_pending = restructure_pending,
    )

    # ── 8. Build customer context string for LLM ──────────────────
    primary_loan = loans[0] if loans else None
    context_lines = [
        f"Name: {customer.customer_name}",
        f"Credit Score: {customer.credit_score}",
        f"Monthly Income: ₹{customer.monthly_income:,.0f}" if customer.monthly_income else "Monthly Income: N/A",
        f"Preferred Channel: {customer.preferred_channel}",
        f"Preferred Language: {customer.preferred_language}",
    ]
    if primary_loan:
        context_lines += [
            f"Loan ID: {primary_loan.loan_id}",
            f"Loan Type: {primary_loan.loan_type}",
            f"Outstanding Balance: ₹{primary_loan.outstanding_balance:,.0f}",
            f"EMI: ₹{primary_loan.emi_amount:,.0f} | Due: {primary_loan.emi_due_date}",
            f"Days Past Due: {primary_loan.days_past_due}",
            f"Risk Segment: {primary_loan.risk_segment}",
            f"Self-Cure Probability: {(primary_loan.self_cure_probability or 0.5) * 100:.0f}%",
        ]
    if interactions:
        context_lines.append("\nRecent Interactions:")
        for i in interactions[:2]:
            context_lines.append(
                f"  - [{i.interaction_type}] {str(i.interaction_time)[:10]}: "
                f"{i.interaction_summary or 'No summary.'}"
            )
    customer_context = "\n".join(context_lines)

    # ── 9. LLM call → suggested responses + questions ─────────────
    suggested_responses = []
    questions_to_ask    = []

    system_prompt, user_prompt = _build_copilot_prompt(
        transcript       = transcript_for_analysis,
        customer_name    = customer.customer_name,
        customer_context = customer_context,
        sentiment_score  = sentiment_score,
        tonality         = tonality,
    )

    llm_raw = call_ollama(user_prompt, system_prompt)

    if llm_raw:
        # Strip markdown fences if present
        cleaned = llm_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[-2] if "```" in cleaned[3:] else cleaned[3:]
            cleaned = cleaned.lstrip("json").strip()

        try:
            parsed = json.loads(cleaned)
            suggested_responses = parsed.get("suggested_responses", [])[:3]
            questions_to_ask    = parsed.get("questions_to_ask", [])[:3]
        except (json.JSONDecodeError, Exception) as e:
            print(f"[CopilotAgent] JSON parse error: {e}. Using fallback.")

    # ── 10. Fallback if LLM unavailable or parse failed ───────────
    if not suggested_responses or not questions_to_ask:
        dpd        = primary_loan.days_past_due if primary_loan else 0
        risk       = primary_loan.risk_segment  if primary_loan else "Medium"
        self_cure  = (primary_loan.self_cure_probability or 0.5) if primary_loan else 0.5
        suggested_responses, questions_to_ask = _fallback_suggestions(
            transcript      = transcript_for_analysis,
            sentiment_score = sentiment_score,
            dpd             = dpd,
            risk_segment    = risk,
            self_cure       = self_cure,
        )

    # Ensure exactly 3 items each
    suggested_responses = (suggested_responses + [""])[:3]
    questions_to_ask    = (questions_to_ask    + [""])[:3]
    suggested_responses = [r for r in suggested_responses if r]
    questions_to_ask    = [q for q in questions_to_ask    if q]

    # ── 11. Save CallSession to DB ────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    call_session = CallSession(
        customer_id       = customer_id,
        loan_id           = loan_id,
        officer_id        = officer_id,
        upload_time       = now,
        transcript        = transcript_english,   # store English version
        language_detected = language_detected,
        status            = "completed",
    )
    db.add(call_session)
    db.flush()   # get call_session_id before saving suggestion

    # ── 12. Save CopilotSuggestion to DB ──────────────────────────
    suggestion = CopilotSuggestion(
        call_session_id     = call_session.call_session_id,
        customer_id         = customer_id,
        sentiment_score     = sentiment_score,
        tonality            = tonality,
        suggested_responses = json.dumps(suggested_responses),
        questions_to_ask    = json.dumps(questions_to_ask),
        nudges              = json.dumps(nudges),
        created_at          = now,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(call_session)
    db.refresh(suggestion)

    return {
        "call_session_id":     call_session.call_session_id,
        "customer_id":         customer_id,
        "customer_name":       customer.customer_name,
        "transcript":          transcript_english,
        "transcript_original": transcript_original,
        "transcript_english":  transcript_english,
        "language_detected":   language_detected,
        "sentiment_score":     sentiment_score,
        "tonality":            tonality,
        "suggested_responses": suggested_responses,
        "questions_to_ask":    questions_to_ask,
        "nudges":              nudges,
    }
