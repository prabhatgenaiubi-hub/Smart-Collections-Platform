from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from backend.db.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Customer Table
# ─────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    customer_id         = Column(String, primary_key=True, default=gen_uuid)
    customer_name       = Column(String, nullable=False)
    mobile_number       = Column(String, nullable=False)
    email_id            = Column(String, nullable=False)
    preferred_language  = Column(String, default="English")
    preferred_channel   = Column(String, default="Email")
    relationship_assessment = Column(Text, nullable=True)
    credit_score        = Column(Integer, nullable=True)
    monthly_income      = Column(Float, nullable=True)
    password            = Column(String, nullable=False, default="password123")

    loans               = relationship("Loan", back_populates="customer")
    interactions        = relationship("InteractionHistory", back_populates="customer")
    grace_requests      = relationship("GraceRequest", back_populates="customer")
    restructure_requests = relationship("RestructureRequest", back_populates="customer")
    chat_sessions       = relationship("ChatSession", back_populates="customer")
    preferences         = relationship("CustomerPreference", back_populates="customer", uselist=False)


# ─────────────────────────────────────────────
# Loan Table
# ─────────────────────────────────────────────
class Loan(Base):
    __tablename__ = "loans"

    loan_id              = Column(String, primary_key=True, default=gen_uuid)
    customer_id          = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    loan_type            = Column(String, nullable=False)
    loan_amount          = Column(Float, nullable=False)
    interest_rate        = Column(Float, nullable=False)
    emi_amount           = Column(Float, nullable=False)
    emi_due_date         = Column(String, nullable=False)
    outstanding_balance  = Column(Float, nullable=False)
    days_past_due        = Column(Integer, default=0)
    risk_segment         = Column(String, default="Low")        # Low / Medium / High
    self_cure_probability = Column(Float, default=0.5)
    recommended_channel  = Column(String, default="Email")

    customer             = relationship("Customer", back_populates="loans")
    payment_history      = relationship("PaymentHistory", back_populates="loan")
    grace_requests       = relationship("GraceRequest", back_populates="loan")
    restructure_requests = relationship("RestructureRequest", back_populates="loan")


# ─────────────────────────────────────────────
# Payment History Table
# ─────────────────────────────────────────────
class PaymentHistory(Base):
    __tablename__ = "payment_history"

    payment_id      = Column(String, primary_key=True, default=gen_uuid)
    loan_id         = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    payment_date    = Column(String, nullable=False)
    payment_amount  = Column(Float, nullable=False)
    payment_method  = Column(String, default="Bank Transfer")

    loan            = relationship("Loan", back_populates="payment_history")


# ─────────────────────────────────────────────
# Interaction History Table
# ─────────────────────────────────────────────
class InteractionHistory(Base):
    __tablename__ = "interaction_history"

    interaction_id      = Column(String, primary_key=True, default=gen_uuid)
    customer_id         = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    interaction_type    = Column(String, nullable=False)   # Call / Chat / Email / SMS
    interaction_time    = Column(String, nullable=False)
    conversation_text   = Column(Text, nullable=True)
    sentiment_score     = Column(Float, default=0.0)       # -1.0 to 1.0
    tonality_score      = Column(String, default="Neutral") # Positive / Neutral / Negative
    interaction_summary = Column(Text, nullable=True)

    customer            = relationship("Customer", back_populates="interactions")


# ─────────────────────────────────────────────
# Grace Requests Table
# ─────────────────────────────────────────────
class GraceRequest(Base):
    __tablename__ = "grace_requests"

    request_id       = Column(String, primary_key=True, default=gen_uuid)
    loan_id          = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    customer_id      = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    request_status   = Column(String, default="Pending")   # Pending / Approved / Rejected
    decision_comment = Column(Text, nullable=True)
    request_date     = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    approved_by      = Column(String, nullable=True)
    decision_date    = Column(String, nullable=True)

    loan             = relationship("Loan", back_populates="grace_requests")
    customer         = relationship("Customer", back_populates="grace_requests")


# ─────────────────────────────────────────────
# Restructure Requests Table
# ─────────────────────────────────────────────
class RestructureRequest(Base):
    __tablename__ = "restructure_requests"

    request_id       = Column(String, primary_key=True, default=gen_uuid)
    loan_id          = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    customer_id      = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    request_status   = Column(String, default="Pending")   # Pending / Approved / Rejected
    decision_comment = Column(Text, nullable=True)
    request_date     = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    approved_by      = Column(String, nullable=True)
    decision_date    = Column(String, nullable=True)

    loan             = relationship("Loan", back_populates="restructure_requests")
    customer         = relationship("Customer", back_populates="restructure_requests")


# ─────────────────────────────────────────────
# Customer Preferences Table
# ─────────────────────────────────────────────
class CustomerPreference(Base):
    __tablename__ = "customer_preferences"

    customer_id        = Column(String, ForeignKey("customers.customer_id"), primary_key=True)
    preferred_channel  = Column(String, default="Email")
    preferred_language = Column(String, default="English")
    updated_at         = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    customer           = relationship("Customer", back_populates="preferences")


# ─────────────────────────────────────────────
# Chat Sessions Table
# ─────────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id    = Column(String, primary_key=True, default=gen_uuid)
    customer_id   = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    session_title = Column(String, default="New Chat")
    created_at    = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    last_updated  = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    customer      = relationship("Customer", back_populates="chat_sessions")
    messages      = relationship("ChatMessage", back_populates="session")


# ─────────────────────────────────────────────
# Chat Messages Table
# ─────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id        = Column(String, primary_key=True, default=gen_uuid)
    session_id        = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    role              = Column(String, nullable=False)   # user / assistant / system
    message_text      = Column(Text, nullable=False)     # original script (native language)
    english_text      = Column(Text, nullable=True)      # English translation (for LLM / search)
    original_language = Column(String, nullable=True)    # detected language e.g. 'Hindi'
    timestamp         = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    session           = relationship("ChatSession", back_populates="messages")


# ─────────────────────────────────────────────
# Bank Officer Table
# ─────────────────────────────────────────────
class BankOfficer(Base):
    __tablename__ = "bank_officers"

    officer_id   = Column(String, primary_key=True, default=gen_uuid)
    officer_name = Column(String, nullable=False)
    email        = Column(String, nullable=False)
    password     = Column(String, nullable=False, default="officer123")
    department   = Column(String, default="Collections")


# ─────────────────────────────────────────────
# Call Sessions Table  (Co-Pilot Feature)
# ─────────────────────────────────────────────
class CallSession(Base):
    __tablename__ = "call_sessions"

    call_session_id   = Column(String, primary_key=True, default=gen_uuid)
    customer_id       = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    loan_id           = Column(String, nullable=True)          # optional — specific loan
    officer_id        = Column(String, nullable=True)          # officer who ran the analysis
    upload_time       = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    transcript        = Column(Text, nullable=True)            # full transcribed text
    language_detected = Column(String, default="English")      # detected language
    status            = Column(String, default="completed")    # completed / failed

    customer          = relationship("Customer", foreign_keys=[customer_id])
    suggestion        = relationship("CopilotSuggestion", back_populates="call_session", uselist=False)


# ─────────────────────────────────────────────
# Copilot Suggestions Table  (Co-Pilot Feature)
# ─────────────────────────────────────────────
class CopilotSuggestion(Base):
    __tablename__ = "copilot_suggestions"

    suggestion_id       = Column(String, primary_key=True, default=gen_uuid)
    call_session_id     = Column(String, ForeignKey("call_sessions.call_session_id"), nullable=False)
    customer_id         = Column(String, nullable=False)
    sentiment_score     = Column(Float, default=0.0)
    tonality            = Column(String, default="Neutral")
    suggested_responses = Column(Text, nullable=True)   # JSON list of strings
    questions_to_ask    = Column(Text, nullable=True)   # JSON list of strings
    nudges              = Column(Text, nullable=True)   # JSON list of strings
    created_at          = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    call_session        = relationship("CallSession", back_populates="suggestion")


# ─────────────────────────────────────────────
# Agent Performance Table (Coaching & Performance Feature)
# ─────────────────────────────────────────────
class AgentPerformance(Base):
    __tablename__ = "agent_performance"

    performance_id    = Column(String, primary_key=True, default=gen_uuid)
    officer_id        = Column(String, ForeignKey("bank_officers.officer_id"), nullable=False)
    period_start      = Column(String, nullable=False)
    period_end        = Column(String, nullable=False)
    total_calls       = Column(Integer, default=0)
    successful_calls  = Column(Integer, default=0)
    success_rate      = Column(Float, default=0.0)
    avg_sentiment     = Column(Float, default=0.0)
    avg_call_duration = Column(Float, default=0.0)  # in seconds
    first_call_resolution_rate = Column(Float, default=0.0)
    escalation_count  = Column(Integer, default=0)
    escalation_rate   = Column(Float, default=0.0)
    positive_calls    = Column(Integer, default=0)
    neutral_calls     = Column(Integer, default=0)
    negative_calls    = Column(Integer, default=0)
    angry_calls       = Column(Integer, default=0)
    overall_score     = Column(Float, default=0.0)  # 0-10 scale
    created_at        = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    officer           = relationship("BankOfficer", foreign_keys=[officer_id])


# ─────────────────────────────────────────────
# Call Summary Table (AI-Generated Call Analysis)
# ─────────────────────────────────────────────
class CallSummary(Base):
    __tablename__ = "call_summaries"

    summary_id        = Column(String, primary_key=True, default=gen_uuid)
    call_session_id   = Column(String, ForeignKey("call_sessions.call_session_id"), nullable=False)
    customer_id       = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    officer_id        = Column(String, ForeignKey("bank_officers.officer_id"), nullable=False)
    call_date         = Column(String, nullable=False)
    call_duration     = Column(Float, nullable=False)  # seconds
    outcome           = Column(String, nullable=True)  # 'Payment Promise', 'Grace Request', 'Escalated', etc.
    sentiment_start   = Column(Float, default=0.0)
    sentiment_end     = Column(Float, default=0.0)
    sentiment_trend   = Column(String, nullable=True)  # 'Improved', 'Declined', 'Stable'
    tonality          = Column(String, nullable=True)
    key_moments       = Column(Text, nullable=True)  # JSON: [{"time": "1:30", "event": "..."}]
    strengths         = Column(Text, nullable=True)  # JSON array
    improvements      = Column(Text, nullable=True)  # JSON array
    coaching_tips     = Column(Text, nullable=True)  # JSON array
    overall_score     = Column(Float, default=0.0)
    created_at        = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    call_session      = relationship("CallSession", foreign_keys=[call_session_id])
    customer          = relationship("Customer", foreign_keys=[customer_id])
    officer           = relationship("BankOfficer", foreign_keys=[officer_id])


# ─────────────────────────────────────────────
# Coaching Feedback Table
# ─────────────────────────────────────────────
class CoachingFeedback(Base):
    __tablename__ = "coaching_feedback"

    feedback_id       = Column(String, primary_key=True, default=gen_uuid)
    officer_id        = Column(String, ForeignKey("bank_officers.officer_id"), nullable=False)
    supervisor_id     = Column(String, nullable=True)  # who provided feedback
    feedback_type     = Column(String, nullable=False)  # 'Automated', 'Manual', 'Peer Review'
    priority          = Column(String, default='Medium')  # 'High', 'Medium', 'Low'
    issue_category    = Column(String, nullable=True)  # 'De-escalation', 'Product Knowledge', etc.
    feedback_text     = Column(Text, nullable=False)
    recommendations   = Column(Text, nullable=True)  # JSON array of action items
    related_calls     = Column(Text, nullable=True)  # JSON array of call_session_ids
    status            = Column(String, default='Pending')  # 'Pending', 'In Progress', 'Completed'
    created_at        = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    reviewed_at       = Column(String, nullable=True)

    officer           = relationship("BankOfficer", foreign_keys=[officer_id])


# ─────────────────────────────────────────────
# Coaching Sessions Table
# ─────────────────────────────────────────────
class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    session_id        = Column(String, primary_key=True, default=gen_uuid)
    officer_id        = Column(String, ForeignKey("bank_officers.officer_id"), nullable=False)
    supervisor_id     = Column(String, nullable=True)
    session_type      = Column(String, nullable=True)  # '1-on-1', 'Group', 'Shadowing', 'Training Module'
    topic             = Column(String, nullable=False)
    scheduled_date    = Column(String, nullable=True)
    completed_date    = Column(String, nullable=True)
    duration_minutes  = Column(Integer, nullable=True)
    notes             = Column(Text, nullable=True)
    improvement_observed = Column(Integer, default=0)  # 0 = False, 1 = True (SQLite doesn't have boolean)
    created_at        = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    officer           = relationship("BankOfficer", foreign_keys=[officer_id])


# ─────────────────────────────────────────────
# Success Patterns Table (Best Practices from Top Performers)
# ─────────────────────────────────────────────
class SuccessPattern(Base):
    __tablename__ = "success_patterns"

    pattern_id        = Column(String, primary_key=True, default=gen_uuid)
    officer_id        = Column(String, ForeignKey("bank_officers.officer_id"), nullable=False)  # top performer
    pattern_type      = Column(String, nullable=False)  # 'De-escalation', 'Grace Conversion', 'Empathy', etc.
    description       = Column(Text, nullable=False)
    key_phrases       = Column(Text, nullable=True)  # JSON array of effective phrases
    timing_notes      = Column(Text, nullable=True)  # When to use this pattern
    success_rate      = Column(Float, default=0.0)
    sample_calls      = Column(Text, nullable=True)  # JSON array of call_session_ids
    created_at        = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    officer           = relationship("BankOfficer", foreign_keys=[officer_id])


# ═════════════════════════════════════════════════════════════════
# BOUNCE PREVENTION & PAYMENT ASSURANCE TABLES
# ═════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────
# Bounce Risk Profile Table
# ─────────────────────────────────────────────
class BounceRiskProfile(Base):
    __tablename__ = "bounce_risk_profiles"

    profile_id        = Column(String, primary_key=True, default=gen_uuid)
    loan_id           = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    customer_id       = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    
    # Risk Metrics
    risk_score        = Column(Float, default=0.0)  # 0-100
    risk_level        = Column(String, default="Low")  # Low/Medium/High
    risk_factors      = Column(Text, nullable=True)  # JSON: {'past_delays': 3, 'balance_volatility': 'high'}
    
    # Historical Bounce Data
    bounce_count_3m   = Column(Integer, default=0)
    bounce_count_6m   = Column(Integer, default=0)
    bounce_count_12m  = Column(Integer, default=0)
    last_bounce_date  = Column(DateTime, nullable=True)
    
    # Predictions
    next_emi_bounce_probability = Column(Float, default=0.0)  # 0-1
    predicted_bounce_date       = Column(String, nullable=True)  # YYYY-MM-DD
    
    # Timestamps
    calculated_at     = Column(DateTime, default=datetime.now)
    updated_at        = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    loan              = relationship("Loan", foreign_keys=[loan_id])
    customer          = relationship("Customer", foreign_keys=[customer_id])


# ─────────────────────────────────────────────
# Auto-Pay Mandate Table (e-NACH tracking)
# ─────────────────────────────────────────────
class AutoPayMandate(Base):
    __tablename__ = "auto_pay_mandates"

    mandate_id        = Column(String, primary_key=True, default=gen_uuid)
    loan_id           = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    customer_id       = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    
    # Mandate Details
    status            = Column(String, default="Pending")  # Active/Pending/Failed/Cancelled
    mandate_type      = Column(String, default="e-NACH")  # e-NACH/Standing Instruction/UPI AutoPay
    bank_account_number = Column(String, nullable=True)  # Masked: XXXX1234
    ifsc_code         = Column(String, nullable=True)
    max_amount        = Column(Float, nullable=True)
    
    # Activation
    activated_at      = Column(DateTime, nullable=True)
    activated_by      = Column(String, nullable=True)  # customer/officer
    activation_channel = Column(String, nullable=True)  # app/whatsapp/branch/web
    
    # Lifecycle
    first_debit_date  = Column(String, nullable=True)  # YYYY-MM-DD
    expiry_date       = Column(String, nullable=True)  # YYYY-MM-DD
    last_success_date = Column(DateTime, nullable=True)
    failure_count     = Column(Integer, default=0)
    
    # Timestamps
    created_at        = Column(DateTime, default=datetime.now)
    updated_at        = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    loan              = relationship("Loan", foreign_keys=[loan_id])
    customer          = relationship("Customer", foreign_keys=[customer_id])


# ─────────────────────────────────────────────
# Bounce Prevention Action Table (Campaign tracking)
# ─────────────────────────────────────────────
class BouncePreventionAction(Base):
    __tablename__ = "bounce_prevention_actions"

    action_id         = Column(String, primary_key=True, default=gen_uuid)
    loan_id           = Column(String, ForeignKey("loans.loan_id"), nullable=False)
    customer_id       = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    
    # Action Details
    action_type       = Column(String, nullable=False)  # whatsapp/voice_call/email/sms/auto_pay_link
    risk_level_at_trigger = Column(String, nullable=True)  # Low/Medium/High
    recommended_by    = Column(String, default="AI")  # AI/Officer/System
    message_content   = Column(Text, nullable=True)  # Message text or link
    
    # Execution
    triggered_at      = Column(DateTime, default=datetime.now)
    executed_at       = Column(DateTime, nullable=True)
    status            = Column(String, default="pending")  # pending/sent/delivered/failed
    
    # Outcome Tracking
    customer_response = Column(String, nullable=True)  # opened/clicked/enrolled/ignored
    bounce_prevented  = Column(Integer, default=0)  # 0 = False, 1 = True (effectiveness metric)
    response_time_hours = Column(Float, nullable=True)
    
    # Timestamps
    created_at        = Column(DateTime, default=datetime.now)
    updated_at        = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    loan              = relationship("Loan", foreign_keys=[loan_id])
    customer          = relationship("Customer", foreign_keys=[customer_id])