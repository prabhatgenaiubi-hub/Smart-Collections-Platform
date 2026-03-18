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
from backend.db.models import ChatSession, ChatMessage, Customer, Loan
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

    # ── Run LangGraph chat workflow ───────────────────────────────
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
        ai_response = ""

    # ── Fallback response if workflow fails ───────────────────────
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

    Handles:
      1. Emotional / abusive messages  → empathy response
      2. History / previous questions  → list user messages from this session
      3. Loan ID queries               → list active loans
      4. EMI / payment queries         → next EMI details
      5. Grace period queries          → eligibility check
      6. Restructuring queries         → how to apply
      7. Balance queries               → total outstanding
      8. Greetings                     → friendly intro
      9. Everything else               → contextual help prompt (not a canned loan dump)
    """
    msg   = user_message.strip().lower()
    loans = db.query(Loan).filter(Loan.customer_id == customer_id).all()
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    name = customer.customer_name.split()[0] if customer and customer.customer_name else ""

    # ── 1. Emotional / abusive ─────────────────────────────────────
    if any(kw in msg for kw in _EMOTIONAL_KEYWORDS):
        return (
            f"I'm sorry to hear you're feeling this way{', ' + name if name else ''}. "
            "Your concerns are important to us and I genuinely want to help. "
            "Could you share what's troubling you about your loan or account? "
            "I'm here to listen and find the best solution for you."
        )

    # ── 2. History / previous questions ───────────────────────────
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
        # Exclude the current message (last one)
        past_msgs = past_msgs[:-1] if past_msgs else []
        if past_msgs:
            lines = "\n".join(
                f"  {i+1}. {m.message_text} ({m.timestamp[11:16] if m.timestamp else ''})"
                for i, m in enumerate(past_msgs)
            )
            return (
                f"Here are the questions you've asked in this session{', ' + name if name else ''}:\n"
                f"{lines}\n\n"
                "Is there anything specific you'd like me to follow up on?"
            )
        return (
            f"This appears to be the start of our conversation{', ' + name if name else ''}. "
            "You haven't asked any previous questions yet. How can I help you today?"
        )

    # ── 3. Loan ID / list loans ────────────────────────────────────
    if any(kw in msg for kw in ["loan id", "loan number", "my loan", "which loan",
                                  "loan detail", "what is my loan", "list loan"]):
        if loans:
            lines = "\n".join(
                f"  • {l.loan_id} ({l.loan_type}) — ₹{l.outstanding_balance:,.0f} outstanding"
                for l in loans
            )
            return f"Here are your active loans{', ' + name if name else ''}:\n{lines}"
        return "You currently have no active loans on file."

    # ── 4. EMI / payment ──────────────────────────────────────────
    if any(kw in msg for kw in ["emi", "payment", "due", "next", "instalment", "installment"]):
        if loans:
            loan = loans[0]
            return (
                f"Your next EMI of ₹{loan.emi_amount:,.0f} is due on {loan.emi_due_date} "
                f"for loan {loan.loan_id}. "
                f"Your outstanding balance is ₹{loan.outstanding_balance:,.0f}."
            )
        return "I don't see any active loans on your account. Please contact us if you believe this is an error."

    # ── 5. Grace period ───────────────────────────────────────────
    if any(kw in msg for kw in ["grace", "extension", "more time", "extra time"]):
        if loans:
            dpd = loans[0].days_past_due
            if dpd < 30:
                return (
                    "Based on your current account status, you may be eligible for a grace period of up to 7 days. "
                    "You can submit a grace period request from the 'Your Loans' section. "
                    "A bank officer will review and respond within 1-2 business days."
                )
            return (
                "Your current overdue period may affect grace period eligibility. "
                "Please contact the bank directly — we can discuss the best options available to you, "
                "including loan restructuring."
            )

    # ── 6. Restructuring ──────────────────────────────────────────
    if any(kw in msg for kw in ["restructur", "reduce emi", "extend tenure", "lower emi"]):
        return (
            "Loan restructuring options are available if you are facing repayment difficulties. "
            "Options include extending your loan tenure or temporarily reducing your EMI. "
            "You can submit a restructure request from the 'Your Loans' section, "
            "and a bank officer will review it within 2 business days."
        )

    # ── 7. Balance ────────────────────────────────────────────────
    if any(kw in msg for kw in ["balance", "outstanding", "how much", "total due"]):
        if loans:
            total = sum(l.outstanding_balance for l in loans)
            if len(loans) > 1:
                lines = "\n".join(f"  • {l.loan_id}: ₹{l.outstanding_balance:,.0f}" for l in loans)
                return f"Your total outstanding balance is ₹{total:,.0f}:\n{lines}"
            return f"Your outstanding balance for {loans[0].loan_id} is ₹{loans[0].outstanding_balance:,.0f}."

    # ── 8. Greeting ───────────────────────────────────────────────
    if any(kw in msg for kw in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return (
            f"Hello{', ' + name if name else ''}! I'm your AI banking assistant. "
            "I can help you with EMI payment information, outstanding balances, "
            "grace period eligibility, loan restructuring options, and more. "
            "What would you like to know today?"
        )

    # ── 9. Contextual catch-all (no canned loan dump) ─────────────
    topics = []
    if loans:
        topics.append(f"your {loans[0].loan_id} EMI of ₹{loans[0].emi_amount:,.0f} due {loans[0].emi_due_date}")
    topics += ["grace period options", "loan restructuring", "outstanding balance"]
    topics_str = ", ".join(topics)

    return (
        f"I'm here to help{', ' + name if name else ''}. "
        f"I can assist with: {topics_str}. "
        "Could you clarify what you'd like to know? "
        "Or type 'my loans' to see your full loan summary."
    )