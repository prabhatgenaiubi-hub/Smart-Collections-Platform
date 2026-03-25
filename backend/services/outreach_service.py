"""
Outreach Service
================
Orchestrates the full digital outreach pipeline for the officer portal:

  1. generate_draft()  – builds AI-personalised message using existing
                         outreach_agent templates + customer/loan data from DB.
  2. send_message()    – sends the officer-reviewed final message via the
                         appropriate channel adapter and logs the event.
  3. get_history()     – returns all logged outreach events for a customer.

In-memory store
---------------
Outreach events are kept in a plain Python list (_outreach_log) for the MVP.
This resets on server restart.  To persist to DB later:
  - Replace the _append / _get helpers below with SQLAlchemy calls.
  - The rest of the service stays unchanged.

Channel routing
---------------
  "whatsapp"  →  WhatsAppChannel
  "email"     →  EmailChannel
"""

import uuid
from datetime import datetime
from typing   import List, Optional

from sqlalchemy.orm import Session

from backend.db.models                       import Customer, Loan
from backend.agents.outreach_agent           import generate_outreach_message
from backend.services.channels.whatsapp     import WhatsAppChannel
from backend.services.channels.email        import EmailChannel
from backend.services.channels.base         import ChannelResult
from backend.schemas.outreach               import (
    GenerateResponse,
    SendResponse,
    OutreachHistoryItem,
)


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Log  (replace with DB calls to make persistent)
# ─────────────────────────────────────────────────────────────────────────────

_outreach_log: List[dict] = []          # list of OutreachHistoryItem-compatible dicts


def _append_event(event: dict) -> None:
    """Add one outreach event to the in-memory log."""
    _outreach_log.append(event)


def _get_events_for_customer(customer_id: str) -> List[dict]:
    """Return all events for a given customer_id (most-recent first)."""
    return [e for e in reversed(_outreach_log) if e["customer_id"] == customer_id]


# ─────────────────────────────────────────────────────────────────────────────
# Channel factory
# ─────────────────────────────────────────────────────────────────────────────

def _get_channel(channel: str):
    """Return the correct channel sender instance."""
    if channel == "whatsapp":
        return WhatsAppChannel()
    if channel == "email":
        return EmailChannel()
    raise ValueError(f"Unsupported channel: {channel!r}. Must be 'whatsapp' or 'email'.")


# ─────────────────────────────────────────────────────────────────────────────
# Objective → existing outreach_agent message_type mapping
# ─────────────────────────────────────────────────────────────────────────────

_OBJECTIVE_TO_TEMPLATE = {
    "reminder"              : "reminder",
    "overdue"               : "overdue",
    "grace_followup"        : "grace_approved",     # closest template
    "restructure_followup"  : "grace_approved",     # reuse as base; officer can edit
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Generate Draft
# ─────────────────────────────────────────────────────────────────────────────

def generate_draft(
    db          : Session,
    customer_id : str,
    loan_id     : str,
    channel     : str,
    objective   : str,
) -> GenerateResponse:
    """
    Fetch customer + loan from DB and produce a personalised AI draft.

    The draft is built using the existing outreach_agent MESSAGE_TEMPLATES
    (no extra LLM call needed for MVP; plug in LLM call here if desired later).

    Returns:
        GenerateResponse – includes ai_draft, contact, and metadata.

    Raises:
        ValueError  if customer or loan not found.
    """
    # ── Load customer ─────────────────────────────────────────────────────────
    customer: Optional[Customer] = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()
    if not customer:
        raise ValueError(f"Customer '{customer_id}' not found.")

    # ── Load loan ─────────────────────────────────────────────────────────────
    loan: Optional[Loan] = db.query(Loan).filter(
        Loan.loan_id  == loan_id,
        Loan.customer_id == customer_id,
    ).first()
    if not loan:
        raise ValueError(f"Loan '{loan_id}' not found for customer '{customer_id}'.")

    # ── Determine contact for this channel ───────────────────────────────────
    contact = (
        customer.mobile_number if channel == "whatsapp"
        else customer.email_id
    )

    # ── Map channel to template key ───────────────────────────────────────────
    channel_key    = "WhatsApp" if channel == "whatsapp" else "Email"
    template_type  = _OBJECTIVE_TO_TEMPLATE.get(objective, "reminder")

    # ── Generate draft using existing outreach_agent function ─────────────────
    ai_draft = generate_outreach_message(
        channel       = channel_key,
        message_type  = template_type,
        customer_name = customer.customer_name,
        loan_id       = loan.loan_id,
        emi_amount    = loan.emi_amount,
        due_date      = loan.emi_due_date,
        dpd           = loan.days_past_due,
        outstanding   = loan.outstanding_balance,
        comment       = (
            "Please contact us to discuss restructuring options."
            if objective == "restructure_followup" else ""
        ),
    )

    # ── Extract email subject if channel is email ─────────────────────────────
    subject = None
    if channel == "email" and ai_draft.startswith("Subject:"):
        lines    = ai_draft.split("\n", 2)
        subject  = lines[0].replace("Subject:", "").strip()
        ai_draft = lines[2].strip() if len(lines) > 2 else ai_draft

    return GenerateResponse(
        customer_id   = customer_id,
        customer_name = customer.customer_name,
        channel       = channel,
        objective     = objective,
        ai_draft      = ai_draft,
        subject       = subject,
        contact       = contact,
        loan_id       = loan_id,
        generated_at  = datetime.now().isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Send Message  (officer-reviewed final text)
# ─────────────────────────────────────────────────────────────────────────────

def send_message(
    customer_id   : str,
    loan_id       : str,
    channel       : str,
    contact       : str,
    ai_draft      : str,
    final_message : str,
    objective     : str,
    officer_id    : str,
    subject       : Optional[str] = None,
) -> SendResponse:
    """
    Send the officer-approved (and possibly edited) message via the channel.

    Audit trail:
      Both `ai_draft` and `final_message` are stored in the in-memory log.
      `officer_edited` flag is set True when they differ.

    Returns:
        SendResponse with status, event_id, and officer_edited flag.
    """
    event_id       = str(uuid.uuid4())
    sent_at        = datetime.now().isoformat()
    officer_edited = (final_message.strip() != ai_draft.strip())

    # ── Basic guardrail: refuse to send empty messages ────────────────────────
    if not final_message.strip():
        return SendResponse(
            success        = False,
            channel        = channel,
            contact        = contact,
            status         = "failed",
            message        = "Cannot send an empty message.",
            sent_at        = sent_at,
            officer_edited = officer_edited,
            event_id       = event_id,
        )

    # ── Send via channel ──────────────────────────────────────────────────────
    sender : any = _get_channel(channel)
    result : ChannelResult = sender.send(
        recipient = contact,
        message   = final_message,
        subject   = subject,
    )

    # ── Log event to in-memory store ──────────────────────────────────────────
    _append_event({
        "event_id"      : event_id,
        "customer_id"   : customer_id,
        "loan_id"       : loan_id,
        "channel"       : channel,
        "objective"     : objective,
        "contact"       : contact,
        "ai_draft"      : ai_draft,
        "final_message" : final_message,
        "subject"       : subject,
        "status"        : result.status,
        "error"         : result.error,
        "officer_edited": officer_edited,
        "sent_at"       : sent_at,
        "sent_by"       : officer_id,
    })

    return SendResponse(
        success        = result.success,
        channel        = channel,
        contact        = contact,
        status         = result.status,
        message        = result.message,
        sent_at        = sent_at,
        officer_edited = officer_edited,
        event_id       = event_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Get History
# ─────────────────────────────────────────────────────────────────────────────

def get_history(customer_id: str) -> List[OutreachHistoryItem]:
    """
    Return outreach history for a customer from the in-memory log.
    Most recent events are returned first.

    To switch to DB later:
      Replace `_get_events_for_customer` with a SQLAlchemy query.
    """
    events = _get_events_for_customer(customer_id)
    return [OutreachHistoryItem(**e) for e in events]
