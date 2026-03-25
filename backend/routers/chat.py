"""
Chat Router

Customer AI Assistant Endpoints:
  GET  /chat/sessions                        → List all chat sessions for customer
  POST /chat/sessions                        → Create a new chat session
  GET  /chat/sessions/{session_id}           → Get session details + messages
  POST /chat/sessions/{session_id}/message   → Send a message and get AI response
  DELETE /chat/sessions/{session_id}         → Delete a chat session

All chat responses are powered by the LangGraph chat workflow
(Context Memory Agent → LLM Reasoning Agent).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import threading

from backend.db.database import get_db
from backend.db.models import ChatSession, ChatMessage, Customer, Loan, PaymentHistory
from backend.routers.auth import get_current_customer
from backend.langgraph.workflow import run_chat_response

router = APIRouter(prefix="/chat", tags=["Chat Assistant"])


# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────

class NewSessionRequest(BaseModel):
    session_title: Optional[str] = "New Chat"


class SendMessageRequest(BaseModel):
    message:  str
    loan_id:  Optional[str] = None     # optional loan context


# ─────────────────────────────────────────────
# Helper: format session
# ─────────────────────────────────────────────

def format_session(session: ChatSession, db: Session) -> dict:
    message_count = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.session_id
    ).count()

    # Get last message preview
    last_msg = (
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
        "message_count": message_count,
        "last_message":  last_msg.message_text[:80] + "..." if last_msg and len(last_msg.message_text) > 80 else (last_msg.message_text if last_msg else None),
    }


# ─────────────────────────────────────────────
# GET /chat/sessions  (Customer)
# ─────────────────────────────────────────────

@router.get("/sessions")
def list_chat_sessions(
    current_user: dict = Depends(get_current_customer),
    db: Session        = Depends(get_db)
):
    """
    Return all chat sessions for the logged-in customer.
    Ordered by last_updated descending (most recent first).
    """
    customer_id = current_user["user_id"]

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.customer_id == customer_id)
        .order_by(ChatSession.last_updated.desc())
        .all()
    )

    return {
        "sessions": [format_session(s, db) for s in sessions],
        "total":    len(sessions),
    }


# ─────────────────────────────────────────────
# POST /chat/sessions  (Customer)
# ─────────────────────────────────────────────

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_chat_session(
    body:         NewSessionRequest,
    current_user: dict    = Depends(get_current_customer),
    db: Session           = Depends(get_db)
):
    """
    Create a new chat session for the customer.
    Returns the new session with a system welcome message.
    """
    customer_id = current_user["user_id"]
    customer    = db.query(Customer).filter(Customer.customer_id == customer_id).first()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create session
    session = ChatSession(
        customer_id   = customer_id,
        session_title = body.session_title or "New Chat",
        created_at    = now,
        last_updated  = now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Add system welcome message
    welcome_text = (
        f"Hello{', ' + customer.customer_name if customer else ''}! "
        "I'm your AI banking assistant. I can help you with:\n"
        "• EMI payment information\n"
        "• Outstanding balance queries\n"
        "• Grace period eligibility\n"
        "• Loan restructuring options\n\n"
        "How can I assist you today?"
    )

    system_msg = ChatMessage(
        session_id   = session.session_id,
        role         = "assistant",
        message_text = welcome_text,
        timestamp    = now,
    )
    db.add(system_msg)
    db.commit()

    return {
        "success":    True,
        "session_id": session.session_id,
        "session":    format_session(session, db),
        "message":    "Chat session created successfully.",
    }


# ─────────────────────────────────────────────
# GET /chat/sessions/{session_id}  (Customer)
# ─────────────────────────────────────────────

@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id:   str,
    current_user: dict  = Depends(get_current_customer),
    db: Session         = Depends(get_db)
):
    """
    Return a chat session with all messages.
    """
    customer_id = current_user["user_id"]

    session = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == customer_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )

    return {
        "session_id":    session.session_id,
        "session_title": session.session_title,
        "created_at":    session.created_at,
        "last_updated":  session.last_updated,
        "messages": [
            {
                "message_id":   m.message_id,
                "role":         m.role,
                "message_text": m.message_text,
                "timestamp":    m.timestamp,
            }
            for m in messages
        ],
        "total_messages": len(messages),
    }


# ─────────────────────────────────────────────
# POST /chat/sessions/{session_id}/message  (Customer)
# ─────────────────────────────────────────────

@router.post("/sessions/{session_id}/message")
def send_message(
    session_id:   str,
    body:         SendMessageRequest,
    current_user: dict    = Depends(get_current_customer),
    db: Session           = Depends(get_db)
):
    """
    Customer sends a message in a chat session.

    Pipeline:
      1. Save user message to SQL
      2. Run LangGraph chat workflow (context + LLM reasoning)
      3. Save AI response to SQL
      4. Store interaction summary in Chroma Vector DB
      5. Return AI response

    The LLM uses:
      - Recent chat history
      - Customer profile + loan data
      - Semantic vector memory
    """
    customer_id = current_user["user_id"]

    # ── Validate session ownership ────────────────────────────────
    session = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == customer_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found.")

    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Save user message ─────────────────────────────────────────
    user_msg = ChatMessage(
        session_id   = session_id,
        role         = "user",
        message_text = body.message.strip(),
        timestamp    = now,
    )
    db.add(user_msg)
    db.commit()

    # ── Greeting intercept — bypass LLM for hi/hello ──────────────
    _msg_stripped = body.message.strip().lower()
    _GREET_EXACT  = {"hi", "hello", "hey", "hii", "helo", "helo!", "hi!", "hello!", "hey!",
                     "good morning", "good afternoon", "good evening"}
    _is_greeting  = (_msg_stripped in _GREET_EXACT or
                     any(_msg_stripped.startswith(g + " ") for g in ("hi", "hello", "hey")))

    if _is_greeting:
        customer  = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        cust_name = customer.customer_name if customer else ""
        # Detect loan-wise session (title like "Loan LOAN005 – Business Loan")
        import re as _re_greet
        _loan_match = _re_greet.match(r'Loan\s+(\w+)\s+[–-]\s+(.+)', session.session_title or "")
        if _loan_match:
            loan_id_str  = _loan_match.group(1)
            loan_type_str = _loan_match.group(2)
            ai_response = (
                f"Hello, {cust_name}! I'm your AI banking assistant for "
                f"{loan_id_str} ({loan_type_str}). I can help you with:\n"
                f"• EMI payment information\n"
                f"• Outstanding balance queries\n"
                f"• Grace period eligibility\n"
                f"• Loan restructuring options\n\n"
                "How can I assist you today?"
            )
        else:
            ai_response = (
                f"Hello, {cust_name}! I'm your AI banking assistant. I can help you with:\n"
                "• EMI payment information\n"
                "• Outstanding balance queries\n"
                "• Grace period eligibility\n"
                "• Loan restructuring options\n\n"
                "How can I assist you today?"
            )
    else:
        # ── Run LangGraph chat workflow ───────────────────────────
        ai_response = ""
        try:
            result = run_chat_response(
                db          = db,
                customer_id = customer_id,
                session_id  = session_id,
                user_query  = body.message.strip(),
                loan_id     = body.loan_id,
            )
            ai_response = result.get("llm_response", "")
        except Exception as e:
            print(f"[ChatRouter] Workflow error: {e}")

        # ── Fallback response if workflow fails ───────────────────
        if not ai_response:
            ai_response = _fallback_response(body.message, db, customer_id, session_id)

    # ── Save assistant response ───────────────────────────────────
    assistant_msg = ChatMessage(
        session_id   = session_id,
        role         = "assistant",
        message_text = ai_response,
        timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(assistant_msg)

    # ── Update session last_updated ───────────────────────────────
    session.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Auto-update session title from first user message ─────────
    if session.session_title == "New Chat":
        title = body.message.strip()[:50]
        session.session_title = title

    db.commit()
    db.refresh(assistant_msg)

    # ── Session-wise Sentiment Analysis (background thread) ────────
    # Score the WHOLE session's user messages as one blob, but only
    # if no InteractionHistory row has been written for this session
    # in the last 5 minutes (debounce).  This prevents one row per
    # message and instead produces one meaningful sentiment record
    # per conversation session.
    def _run_session_sentiment_bg(cust_id: str, cust_name: str, sess_id: str):
        try:
            from backend.db.database import SessionLocal
            from backend.agents.sentiment_agent import analyze_and_store_interaction
            from backend.db.models import InteractionHistory as IH
            bg_db = SessionLocal()
            try:
                # Debounce: skip if a row for this session was written < 5 min ago
                DEBOUNCE_SECONDS = 300
                last = (
                    bg_db.query(IH)
                    .filter(IH.customer_id == cust_id)
                    .filter(IH.interaction_type == "Chat")
                    .filter(IH.conversation_text.ilike(f"%[session:{sess_id}]%"))
                    .order_by(IH.interaction_time.desc())
                    .first()
                )
                if last:
                    try:
                        from datetime import datetime as _dt
                        last_time = _dt.strptime(last.interaction_time, "%Y-%m-%d %H:%M:%S")
                        elapsed = (_dt.now() - last_time).total_seconds()
                        if elapsed < DEBOUNCE_SECONDS:
                            print(f"[ChatRouter] Sentiment debounced for session {sess_id} ({elapsed:.0f}s ago)")
                            return
                    except Exception:
                        pass  # If parse fails, proceed

                # Collect all user messages in this session
                msgs = (
                    bg_db.query(ChatMessage)
                    .filter(
                        ChatMessage.session_id == sess_id,
                        ChatMessage.role == "user",
                    )
                    .order_by(ChatMessage.timestamp.asc())
                    .all()
                )
                if not msgs:
                    return

                # Concatenate all user turns into one text blob
                full_text = " ".join(m.message_text for m in msgs)
                # Tag with session ID so debounce query can find it
                tagged_text = f"{full_text} [session:{sess_id}]"

                analyze_and_store_interaction(
                    db                = bg_db,
                    customer_id       = cust_id,
                    interaction_type  = "Chat",
                    conversation_text = tagged_text,
                    customer_name     = cust_name,
                )
                print(f"[ChatRouter] Session sentiment written for {sess_id}")
            finally:
                bg_db.close()
        except Exception as bg_err:
            print(f"[ChatRouter] Background sentiment error (non-critical): {bg_err}")

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    cust_name = customer.customer_name if customer else customer_id
    threading.Thread(
        target  = _run_session_sentiment_bg,
        args    = (customer_id, cust_name, session_id),
        daemon  = True,
    ).start()

    # ── Store interaction in Vector DB (async-style, non-blocking) ─
    try:
        from backend.vector.chroma_store import store_memory
        store_memory(
            customer_id = customer_id,
            summary     = f"User asked: {body.message.strip()[:100]}. Assistant replied: {ai_response[:100]}",
            metadata    = {
                "session_id": session_id,
                "timestamp":  now,
                "type":       "chat_interaction",
            }
        )
    except Exception as e:
        print(f"[ChatRouter] Vector store failed (non-critical): {e}")

    return {
        "success":       True,
        "session_id":    session_id,
        "user_message": {
            "role":         "user",
            "message_text": body.message.strip(),
            "timestamp":    now,
        },
        "ai_response": {
            "message_id":   assistant_msg.message_id,
            "role":         "assistant",
            "message_text": ai_response,
            "timestamp":    assistant_msg.timestamp,
        },
    }


# ─────────────────────────────────────────────
# DELETE /chat/sessions/{session_id}  (Customer)
# ─────────────────────────────────────────────

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id:   str,
    current_user: dict  = Depends(get_current_customer),
    db: Session         = Depends(get_db)
):
    """
    Delete a chat session and all its messages.
    """
    customer_id = current_user["user_id"]

    session = db.query(ChatSession).filter(
        ChatSession.session_id  == session_id,
        ChatSession.customer_id == customer_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found.")

    # ── Final sentiment score before deleting ─────────────────────
    # Collect all user messages, score the whole session as one blob,
    # write one definitive InteractionHistory row (overrides any debounced
    # draft rows written during the conversation).
    try:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )
        if msgs:
            from backend.agents.sentiment_agent import analyze_and_store_interaction
            full_text = " ".join(m.message_text for m in msgs)
            customer  = db.query(Customer).filter(Customer.customer_id == customer_id).first()
            cust_name = customer.customer_name if customer else customer_id
            analyze_and_store_interaction(
                db                = db,
                customer_id       = customer_id,
                interaction_type  = "Chat",
                conversation_text = full_text,
                customer_name     = cust_name,
            )
    except Exception as e:
        print(f"[ChatRouter] Final session sentiment error (non-critical): {e}")

    # Delete all messages first
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()

    return {
        "success": True,
        "message": f"Chat session {session_id} deleted successfully.",
    }


# ─────────────────────────────────────────────
# Fallback Response (if LLM + workflow both fail)
# ─────────────────────────────────────────────

# Words that signal the customer is emotional or distressed
_EMOTIONAL_KEYWORDS = [
    "disappointed", "frustrated", "angry", "upset", "disgusted", "terrible",
    "worst", "useless", "hopeless", "pathetic", "horrible", "ridiculous",
    "not happy", "unhappy", "dissatisfied", "fed up", "sick of",
    "fuck", "shit", "damn", "hell", "stupid", "idiot", "rubbish",
    "cancel", "leave", "quit", "stop", "not continue", "will not continue",
    "discontinue", "close my account", "close account",
]

# Words that ask for conversation history
_HISTORY_KEYWORDS = [
    "previous", "last", "earlier", "before", "history", "list",
    "what did i ask", "what have i asked", "my questions", "past question",
    "conversation", "chat history", "what i said", "recap",
]


def _fallback_response(
    user_message: str,
    db: Session,
    customer_id: str,
    session_id: str = "",
) -> str:
    """
    Rule-based fallback when LangGraph/Ollama workflow is unavailable.

    Key behaviours:
      - If the session was opened from a loan page (title contains "Loan LOANXXX"),
        ALL answers are scoped to that single loan only.
      - Payment history check runs BEFORE the session-history check to avoid
        keyword clashes ("previous", "history").
      - Multi-loan follow-up: customer can say "what about LOAN010" mid-chat.
    """
    msg   = user_message.strip().lower()
    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    name = customer.customer_name.split()[0] if customer and customer.customer_name else ""

    # ── Determine active loan context ─────────────────────────────
    # Priority 1: session locked to a loan (opened from Loan page)
    # Priority 2: loan ID explicitly mentioned in this message
    # Priority 3: first/only loan
    session_loan_id = None
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if session and session.session_title:
            import re as _re
            m = _re.search(r'Loan\s+(LOAN\w+)', session.session_title, _re.IGNORECASE)
            if m:
                session_loan_id = m.group(1).upper()

    # Check if user mentions a specific loan ID in this message
    import re as _re
    mentioned_loan_id = None
    lm = _re.search(r'\b(LOAN\w+)\b', user_message, _re.IGNORECASE)
    if lm:
        mentioned_loan_id = lm.group(1).upper()

    # Resolve which loan to use for this response
    if session_loan_id:
        # Session is locked — only answer for this loan
        active_loans = [l for l in loans if l.loan_id == session_loan_id]
        if not active_loans:
            active_loans = loans  # safety fallback
        is_locked = True
    elif mentioned_loan_id:
        active_loans = [l for l in loans if l.loan_id == mentioned_loan_id]
        if not active_loans:
            active_loans = loans
        is_locked = False
    else:
        active_loans = loans
        is_locked = False

    primary_loan = active_loans[0] if active_loans else None

    # ── 1. Emotional / abusive ────────────────────────────────────
    if any(kw in msg for kw in _EMOTIONAL_KEYWORDS):
        return (
            "I'm sorry to hear you're going through a difficult time. "
            "Please let me know what's concerning you — I'm here to help."
        )

    # ── 2. Payment history — BEFORE session-history to avoid clash ──
    if any(kw in msg for kw in ["payment history", "previous payment", "past payment",
                                  "payment record", "show payment", "repayment",
                                  "show my payment", "my payment"]):
        if not primary_loan:
            return "I don't see any active loans on your account."
        payments = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.loan_id == primary_loan.loan_id)
            .order_by(PaymentHistory.payment_date.desc())
            .limit(6)
            .all()
        )
        if not payments:
            return f"No payment records found for {primary_loan.loan_id}."
        lines = "\n".join(
            f"  {i+1}. {p.payment_date}  —  ₹{p.payment_amount:,.0f}  via {p.payment_method}"
            for i, p in enumerate(payments)
        )
        return (
            f"Recent payments for {primary_loan.loan_id}:\n{lines}"
        )

    # ── 3. Number of payments due / pending EMIs ─────────────────
    if any(kw in msg for kw in ["payments due", "how many payment", "number of payment",
                                  "pending payment", "overdue payment", "total payment",
                                  "payments pending", "emi pending", "emis due",
                                  "payment count", "how many emi"]):
        if not primary_loan:
            return "I don't see any active loans on your account."
        if is_locked or mentioned_loan_id or len(active_loans) == 1:
            loan = primary_loan
            dpd = loan.days_past_due
            overdue_emis = max(0, dpd // 30) if dpd > 0 else 0
            if dpd > 0:
                return (
                    f"{loan.loan_id}: {dpd} days past due (~{overdue_emis} overdue EMI(s)).\n"
                    f"Next EMI: ₹{loan.emi_amount:,.0f} due {loan.emi_due_date}."
                )
            return f"{loan.loan_id}: Account is current. Next EMI ₹{loan.emi_amount:,.0f} due {loan.emi_due_date}."
        lines = "\n".join(
            f"  • {l.loan_id}: ₹{l.emi_amount:,.0f} due {l.emi_due_date}"
            + (f" — ⚠️ {l.days_past_due}d overdue" if l.days_past_due > 0 else " ✅")
            for l in loans
        )
        return f"Upcoming EMIs:\n{lines}"

    # ── 4. Session history / previous questions ───────────────────
    if any(kw in msg for kw in _HISTORY_KEYWORDS) and session_id:
        past_msgs = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session_id,
                ChatMessage.role       == "user",
            )
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )
        past_msgs = past_msgs[:-1] if past_msgs else []
        if past_msgs:
            lines = "\n".join(
                f"  {i+1}. {m.message_text} ({m.timestamp[11:16] if m.timestamp else ''})"
                for i, m in enumerate(past_msgs)
            )
            return f"Questions asked in this session:\n{lines}"
        return "No previous questions in this session yet."

    # ── 5. Loan ID query ──────────────────────────────────────────
    if any(kw in msg for kw in ["loan id", "loan number", "my loan", "which loan",
                                  "loan detail", "what is my loan", "list loan"]):
        if is_locked and primary_loan:
            return (
                f"Loan ID: {primary_loan.loan_id} ({primary_loan.loan_type})\n"
                f"Outstanding: ₹{primary_loan.outstanding_balance:,.0f} | EMI: ₹{primary_loan.emi_amount:,.0f} due {primary_loan.emi_due_date}"
            )
        if loans:
            lines = "\n".join(
                f"  • {l.loan_id} ({l.loan_type}) — ₹{l.outstanding_balance:,.0f} outstanding"
                for l in loans
            )
            return f"Your active loans:\n{lines}"
        return "You currently have no active loans on file."

    # ── 6. EMI / payment due ──────────────────────────────────────
    if any(kw in msg for kw in ["emi", "due", "next", "instalment", "installment", "due date"]):
        if not primary_loan:
            return "I don't see any active loans on your account."
        if is_locked or mentioned_loan_id or len(active_loans) == 1:
            loan = primary_loan
            status = "✅ Current" if loan.days_past_due == 0 else f"⚠️ {loan.days_past_due} days past due"
            return (
                f"{loan.loan_id} EMI: ₹{loan.emi_amount:,.0f} due {loan.emi_due_date} | {status}"
            )
        lines = "\n".join(
            f"  • {l.loan_id}: ₹{l.emi_amount:,.0f} due {l.emi_due_date}"
            for l in loans
        )
        return f"Your upcoming EMIs:\n{lines}"

    # ── 7. Grace period ───────────────────────────────────────────
    if any(kw in msg for kw in ["grace", "extension", "more time", "extra time"]):
        if primary_loan and primary_loan.days_past_due < 30:
            return (
                "You may be eligible for a grace period of up to 7 days. "
                "Submit a request from the 'Your Loans' section — a bank officer will review within 1-2 business days."
            )
        return (
            "Your overdue status may affect grace period eligibility. "
            "Please contact the bank to discuss available options."
        )

    # ── 8. Restructuring ──────────────────────────────────────────
    if any(kw in msg for kw in ["restructur", "reduce emi", "extend tenure", "lower emi"]):
        return (
            "Loan restructuring (EMI reduction or tenure extension) is available if you're facing difficulties. "
            "Submit a request from 'Your Loans' — a bank officer will review within 2 business days."
        )

    # ── 9. Balance ────────────────────────────────────────────────
    if any(kw in msg for kw in ["balance", "outstanding", "how much", "total due"]):
        if not primary_loan:
            return "I don't see any active loans on your account."
        if is_locked or mentioned_loan_id or len(active_loans) == 1:
            loan = primary_loan
            return f"Outstanding balance for {loan.loan_id}: ₹{loan.outstanding_balance:,.0f}."
        total = sum(l.outstanding_balance for l in loans)
        lines = "\n".join(f"  • {l.loan_id}: ₹{l.outstanding_balance:,.0f}" for l in loans)
        return f"Total outstanding: ₹{total:,.0f}\n{lines}"

    # ── 10. Customer name query ────────────────────────────────────
    if any(kw in msg for kw in ["my name", "what is my name", "what's my name",
                                  "who am i", "name is"]):
        full_name = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if full_name:
            return f"Your name is {full_name.customer_name}."
        return "I don't have your name on file."

    # ── 11. Late payments / missed payments ────────────────────────
    if any(kw in msg for kw in ["late payment", "missed payment", "how many late",
                                  "late emi", "missed emi", "delayed payment",
                                  "overdue count", "default count"]):
        if not primary_loan:
            return "I don't see any active loans on your account."
        # Count payments that are likely late (using days_past_due as indicator)
        # and also check PaymentHistory for any records to count
        all_payments = (
            db.query(PaymentHistory)
            .filter(PaymentHistory.loan_id == primary_loan.loan_id)
            .order_by(PaymentHistory.payment_date.desc())
            .all()
        )
        dpd = primary_loan.days_past_due
        overdue_emis = max(0, dpd // 30) if dpd > 0 else 0
        if overdue_emis > 0:
            return (
                f"Loan {primary_loan.loan_id} is currently {dpd} days past due, "
                f"indicating approximately {overdue_emis} overdue EMI(s)."
            )
        return f"No late payments detected for {primary_loan.loan_id} — account is current."

    # ── 12. Greeting ───────────────────────────────────────────────
    if any(kw in msg for kw in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return (
            f"Hello{', ' + name if name else ''}! I'm your AI banking assistant. "
            "What would you like to know today?"
        )

    # ── 13. Contextual catch-all ──────────────────────────────────
    if primary_loan:
        return (
            f"For loan {primary_loan.loan_id} ({primary_loan.loan_type}): "
            f"EMI ₹{primary_loan.emi_amount:,.0f} due {primary_loan.emi_due_date}, "
            f"outstanding ₹{primary_loan.outstanding_balance:,.0f}. "
            "Ask me anything specific about your loan."
        )
    return "How can I help you? Ask me about your loan, EMI, balance, or payment history."