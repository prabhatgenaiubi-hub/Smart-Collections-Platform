"""
Outreach Schemas
================
Pydantic request/response models for the Digital Outreach Agent endpoints.

Endpoints served:
  POST /outreach/generate  → GenerateRequest  → GenerateResponse
  POST /outreach/send      → SendRequest      → SendResponse
  GET  /outreach/history/{customer_id}        → list[OutreachHistoryItem]
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


# ─────────────────────────────────────────────
# Allowed values (single source of truth)
# ─────────────────────────────────────────────

SUPPORTED_CHANNELS   = Literal["whatsapp", "email"]
SUPPORTED_OBJECTIVES = Literal["reminder", "overdue", "grace_followup", "restructure_followup"]


# ─────────────────────────────────────────────
# POST /outreach/generate
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Request body for AI draft generation."""

    customer_id : str = Field(..., description="Customer ID to generate message for")
    loan_id     : str = Field(..., description="Specific loan ID context")
    channel     : SUPPORTED_CHANNELS   = Field(..., description="whatsapp | email")
    objective   : SUPPORTED_OBJECTIVES = Field(..., description="reminder | overdue | grace_followup | restructure_followup")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id" : "CUST001",
                "loan_id"     : "LOAN001",
                "channel"     : "whatsapp",
                "objective"   : "overdue",
            }
        }


class GenerateResponse(BaseModel):
    """Response with AI-generated draft for officer to review/edit."""

    customer_id   : str
    customer_name : str
    channel       : str
    objective     : str
    ai_draft      : str      # The AI-generated message text
    subject       : Optional[str] = None   # Email subject (only for email channel)
    contact       : str      # Phone (WhatsApp) or email address of the customer
    loan_id       : str
    generated_at  : str


# ─────────────────────────────────────────────
# POST /outreach/send
# ─────────────────────────────────────────────

class SendRequest(BaseModel):
    """
    Request body for sending the (possibly officer-edited) message.
    Both ai_draft and final_message are stored for audit trail.
    """

    customer_id   : str = Field(..., description="Customer ID")
    loan_id       : str = Field(..., description="Loan ID")
    channel       : SUPPORTED_CHANNELS
    contact       : str  = Field(..., description="Phone number or email to send to")
    ai_draft      : str  = Field(..., description="Original AI-generated message (for audit)")
    final_message : str  = Field(..., description="Officer-edited final message to actually send")
    subject       : Optional[str] = Field(None, description="Email subject (required for email channel)")
    objective     : SUPPORTED_OBJECTIVES

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id"   : "CUST001",
                "loan_id"       : "LOAN001",
                "channel"       : "email",
                "contact"       : "customer@example.com",
                "ai_draft"      : "Dear Ramesh, your EMI is overdue...",
                "final_message" : "Dear Mr. Ramesh, we noticed your EMI is pending...",
                "subject"       : "Important: EMI Overdue Notice",
                "objective"     : "overdue",
            }
        }


class SendResponse(BaseModel):
    """Response after attempting to send the message."""

    success        : bool
    channel        : str
    contact        : str
    status         : str          # sent | mock_sent | failed
    message        : str          # human-readable result
    sent_at        : str
    officer_edited : bool         # True if final_message differs from ai_draft
    event_id       : str          # UUID for this outreach event (for history lookup)


# ─────────────────────────────────────────────
# GET /outreach/history/{customer_id}
# ─────────────────────────────────────────────

class OutreachHistoryItem(BaseModel):
    """One outreach event record stored in in-memory history."""

    event_id       : str
    customer_id    : str
    loan_id        : str
    channel        : str
    objective      : str
    contact        : str
    ai_draft       : str
    final_message  : str
    subject        : Optional[str] = None
    status         : str           # sent | mock_sent | failed
    error          : Optional[str] = None
    officer_edited : bool
    sent_at        : str
    sent_by        : str           # officer user_id
