"""
Digital Outreach Router
=======================
All endpoints are officer-only (JWT token with role='officer' required).

Endpoints:
  POST /outreach/generate               → Generate AI-personalised draft
  POST /outreach/send                   → Send officer-reviewed message
  GET  /outreach/history/{customer_id}  → In-memory send history

Design notes:
  • generate  returns a draft + metadata; NOTHING is sent yet.
  • send       accepts the (possibly edited) final_message; runs it through
               the channel adapter; logs both ai_draft and final_message.
  • history    returns most-recent-first list of outreach events.
"""

from fastapi      import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database    import get_db
from backend.routers.auth   import get_current_officer

from backend.schemas.outreach import (
    GenerateRequest,
    GenerateResponse,
    SendRequest,
    SendResponse,
    OutreachHistoryItem,
)
from backend.services import outreach_service

router = APIRouter(prefix="/outreach", tags=["Digital Outreach"])


# ─────────────────────────────────────────────
# POST /outreach/generate
# ─────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
def generate_draft(
    request      : GenerateRequest,
    current_user : dict    = Depends(get_current_officer),
    db           : Session = Depends(get_db),
):
    """
    Generate an AI-personalised outreach message draft.

    The draft is built from customer + loan data and the existing
    outreach_agent message templates (WhatsApp / Email).

    The officer should review — and optionally edit — this draft
    before calling POST /outreach/send.

    Supported channels   : whatsapp, email
    Supported objectives : reminder, overdue, grace_followup, restructure_followup
    """
    try:
        response = outreach_service.generate_draft(
            db          = db,
            customer_id = request.customer_id,
            loan_id     = request.loan_id,
            channel     = request.channel,
            objective   = request.objective,
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {str(e)}")


# ─────────────────────────────────────────────
# POST /outreach/send
# ─────────────────────────────────────────────

@router.post("/send", response_model=SendResponse)
def send_message(
    request      : SendRequest,
    current_user : dict    = Depends(get_current_officer),
    db           : Session = Depends(get_db),
):
    """
    Send the officer-approved (and possibly edited) outreach message.

    Human-in-the-loop contract:
      • `ai_draft`      – the original draft returned by /outreach/generate
                          (stored for audit; never directly sent)
      • `final_message` – the text the officer approved (may be edited)
                          (this is what actually gets sent)

    If `final_message` differs from `ai_draft`, the event is flagged as
    `officer_edited=true` in the audit log.

    If channel credentials are missing, the message is logged as
    `mock_sent` (safe fallback for development / demo).
    """
    try:
        response = outreach_service.send_message(
            customer_id   = request.customer_id,
            loan_id       = request.loan_id,
            channel       = request.channel,
            contact       = request.contact,
            ai_draft      = request.ai_draft,
            final_message = request.final_message,
            objective     = request.objective,
            officer_id    = current_user.get("user_id", "unknown"),
            subject       = request.subject,
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}")


# ─────────────────────────────────────────────
# GET /outreach/history/{customer_id}
# ─────────────────────────────────────────────

@router.get("/history/{customer_id}", response_model=list[OutreachHistoryItem])
def get_history(
    customer_id  : str,
    current_user : dict = Depends(get_current_officer),
):
    """
    Return the outreach history for a specific customer.

    Results are from the in-memory log (most-recent first).
    Data resets on server restart for MVP; extend to DB later without
    changing this endpoint signature.
    """
    return outreach_service.get_history(customer_id)
