"""
Bounce Prevention & Payment Assurance Router

Endpoints for:
- Bounce risk calculation
- Auto-pay (e-NACH) enrollment
- Dashboard statistics
- Outreach campaign triggers
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json

from backend.db.database import get_db
from backend.db.models import (
    Loan, Customer, PaymentHistory,
    BounceRiskProfile, AutoPayMandate, BouncePreventionAction
)
from backend.routers.auth import get_current_customer, get_current_officer
from analytics.bounce_predictor import (
    calculate_bounce_risk,
    get_recommended_outreach_channel,
    generate_auto_pay_message,
    predict_bounce_date
)

router = APIRouter(prefix="/bounce-prevention", tags=["Bounce Prevention"])


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class BounceRiskResponse(BaseModel):
    loan_id: str
    customer_id: str
    customer_name: str
    risk_score: float
    risk_level: str
    factors: dict
    next_emi_bounce_probability: float
    predicted_bounce_date: Optional[str]
    recommended_action: str
    auto_pay_enabled: bool
    calculated_at: str


class AutoPayEnrollmentRequest(BaseModel):
    bank_account_number: str
    ifsc_code: str
    max_amount: float
    activation_channel: str = "app"


class OutreachTriggerRequest(BaseModel):
    loan_ids: List[str]
    channel: Optional[str] = None  # Auto-select if None
    message_template: Optional[str] = None


# ─────────────────────────────────────────────
# GET /bounce-prevention/loans/{loan_id}/risk
# ─────────────────────────────────────────────

@router.get("/loans/{loan_id}/risk", response_model=BounceRiskResponse)
def get_loan_bounce_risk(
    loan_id: str,
    recalculate: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_customer)
):
    """
    Get bounce risk for a specific loan.
    
    Query params:
      - recalculate: Force recalculation (default: use cached if < 24hrs old)
    """
    
    # Fetch loan
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Fetch customer
    customer = db.query(Customer).filter(Customer.customer_id == loan.customer_id).first()
    
    # Fetch existing profile
    profile = db.query(BounceRiskProfile).filter(
        BounceRiskProfile.loan_id == loan_id
    ).first()
    
    # Check if recalculation needed
    needs_recalculation = (
        recalculate or
        not profile or
        (datetime.now() - profile.updated_at).total_seconds() > 86400  # 24 hours
    )
    
    if needs_recalculation:
        # Fetch payment history
        payment_history = db.query(PaymentHistory).filter(
            PaymentHistory.loan_id == loan_id
        ).all()
        
        # Calculate risk
        risk_data = calculate_bounce_risk(loan, payment_history, profile)
        
        # Update or create profile
        if profile:
            profile.risk_score = risk_data['score']
            profile.risk_level = risk_data['level']
            profile.risk_factors = json.dumps(risk_data['factors'])
            profile.next_emi_bounce_probability = risk_data['next_emi_bounce_probability']
            profile.predicted_bounce_date = predict_bounce_date(
                loan, risk_data['next_emi_bounce_probability']
            )
            profile.updated_at = datetime.now()
        else:
            profile = BounceRiskProfile(
                loan_id=loan_id,
                customer_id=loan.customer_id,
                risk_score=risk_data['score'],
                risk_level=risk_data['level'],
                risk_factors=json.dumps(risk_data['factors']),
                next_emi_bounce_probability=risk_data['next_emi_bounce_probability'],
                predicted_bounce_date=predict_bounce_date(
                    loan, risk_data['next_emi_bounce_probability']
                ),
                bounce_count_3m=0,  # TODO: Calculate from actual data
                bounce_count_6m=0,
                bounce_count_12m=0
            )
            db.add(profile)
        
        db.commit()
        db.refresh(profile)
    
    # Check auto-pay status
    auto_pay = db.query(AutoPayMandate).filter(
        AutoPayMandate.loan_id == loan_id,
        AutoPayMandate.status == "Active"
    ).first()
    
    return BounceRiskResponse(
        loan_id=loan_id,
        customer_id=loan.customer_id,
        customer_name=customer.customer_name if customer else "Unknown",
        risk_score=profile.risk_score,
        risk_level=profile.risk_level,
        factors=json.loads(profile.risk_factors) if profile.risk_factors else {},
        next_emi_bounce_probability=profile.next_emi_bounce_probability,
        predicted_bounce_date=profile.predicted_bounce_date,
        recommended_action=calculate_bounce_risk(loan, [], profile)['recommended_action'],
        auto_pay_enabled=auto_pay is not None,
        calculated_at=profile.updated_at.isoformat() if profile.updated_at else datetime.now().isoformat()
    )


# ─────────────────────────────────────────────
# POST /bounce-prevention/loans/{loan_id}/enable-autopay
# ─────────────────────────────────────────────

@router.post("/loans/{loan_id}/enable-autopay")
def enable_auto_pay(
    loan_id: str,
    enrollment: AutoPayEnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_customer)
):
    """
    Enable auto-pay (e-NACH) for a loan.
    
    This is a MOCK implementation - in production, this would:
    1. Initiate actual e-NACH registration
    2. Validate bank account
    3. Get customer consent
    4. Submit to NPCI
    """
    
    # Fetch loan
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Check if already enrolled
    existing = db.query(AutoPayMandate).filter(
        AutoPayMandate.loan_id == loan_id,
        AutoPayMandate.status.in_(["Active", "Pending"])
    ).first()
    
    if existing:
        return {
            "success": False,
            "message": "Auto-pay already enabled or pending",
            "mandate_id": existing.mandate_id,
            "status": existing.status
        }
    
    # Create mandate (MOCK)
    mandate = AutoPayMandate(
        loan_id=loan_id,
        customer_id=loan.customer_id,
        status="Active",  # In production: "Pending" until confirmed
        mandate_type="e-NACH",
        bank_account_number=enrollment.bank_account_number[-4:].rjust(12, 'X'),  # Mask
        ifsc_code=enrollment.ifsc_code,
        max_amount=enrollment.max_amount,
        activated_at=datetime.now(),
        activated_by="customer",
        activation_channel=enrollment.activation_channel,
        first_debit_date=(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        expiry_date=(datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    )
    
    db.add(mandate)
    db.commit()
    db.refresh(mandate)
    
    # Log action
    action = BouncePreventionAction(
        loan_id=loan_id,
        customer_id=loan.customer_id,
        action_type="auto_pay_enrollment",
        recommended_by="customer",
        triggered_at=datetime.now(),
        executed_at=datetime.now(),
        status="sent",
        customer_response="enrolled"
    )
    db.add(action)
    db.commit()
    
    return {
        "success": True,
        "message": "Auto-pay enabled successfully!",
        "mandate_id": mandate.mandate_id,
        "status": mandate.status,
        "first_debit_date": mandate.first_debit_date,
        "max_amount": mandate.max_amount
    }


# ─────────────────────────────────────────────
# GET /bounce-prevention/dashboard/stats
# ─────────────────────────────────────────────

@router.get("/dashboard/stats")
def get_bounce_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_officer)
):
    """
    Get bounce risk statistics for officer dashboard.
    
    Returns:
      - Total loans at risk
      - Breakdown by risk level
      - Auto-pay enrollment rate
      - Prevented bounces (mock)
    """
    
    # Get all risk profiles
    profiles = db.query(BounceRiskProfile).all()
    
    total_loans = len(profiles)
    high_risk = sum(1 for p in profiles if p.risk_level == "High")
    medium_risk = sum(1 for p in profiles if p.risk_level == "Medium")
    low_risk = sum(1 for p in profiles if p.risk_level == "Low")
    
    # Auto-pay stats
    active_mandates = db.query(AutoPayMandate).filter(
        AutoPayMandate.status == "Active"
    ).count()
    
    total_loans_with_profiles = db.query(Loan).count()
    auto_pay_rate = (active_mandates / total_loans_with_profiles * 100) if total_loans_with_profiles > 0 else 0
    
    # Prevention actions
    actions = db.query(BouncePreventionAction).filter(
        BouncePreventionAction.bounce_prevented == 1
    ).count()
    
    return {
        "total_loans_monitored": total_loans,
        "risk_breakdown": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk
        },
        "auto_pay_enrollment_rate": round(auto_pay_rate, 1),
        "active_mandates": active_mandates,
        "bounces_prevented_this_month": actions,  # Mock
        "potential_savings": actions * 500  # Mock: ₹500 per prevented bounce
    }


# ─────────────────────────────────────────────
# POST /bounce-prevention/outreach/trigger
# ─────────────────────────────────────────────

@router.post("/outreach/trigger")
def trigger_bounce_prevention_outreach(
    request: OutreachTriggerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_officer)
):
    """
    Trigger bounce prevention outreach campaign.
    
    MOCK implementation - in production:
    1. Send actual WhatsApp/SMS/Email
    2. Make voice calls
    3. Track delivery status
    """
    
    triggered_actions = []
    
    for loan_id in request.loan_ids:
        # Fetch loan and risk profile
        loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
        if not loan:
            continue
        
        profile = db.query(BounceRiskProfile).filter(
            BounceRiskProfile.loan_id == loan_id
        ).first()
        
        customer = db.query(Customer).filter(
            Customer.customer_id == loan.customer_id
        ).first()
        
        # Determine channel
        if request.channel:
            channel = request.channel
        else:
            channel = get_recommended_outreach_channel(
                profile.risk_level if profile else "Low",
                customer.preferred_channel if customer else None
            )
        
        # Generate message
        if request.message_template:
            message = request.message_template
        else:
            message = generate_auto_pay_message(
                customer.customer_name if customer else "Customer",
                loan.loan_type,
                loan.emi_amount
            )
        
        # Create action record
        action = BouncePreventionAction(
            loan_id=loan_id,
            customer_id=loan.customer_id,
            action_type=channel,
            risk_level_at_trigger=profile.risk_level if profile else "Unknown",
            recommended_by="AI",
            message_content=message,
            triggered_at=datetime.now(),
            executed_at=datetime.now(),  # Mock instant execution
            status="sent"  # Mock success
        )
        
        db.add(action)
        triggered_actions.append({
            "loan_id": loan_id,
            "customer_name": customer.customer_name if customer else "Unknown",
            "channel": channel,
            "status": "sent"
        })
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Triggered {len(triggered_actions)} outreach campaigns",
        "actions": triggered_actions
    }


# ─────────────────────────────────────────────
# GET /bounce-prevention/loans/at-risk
# ─────────────────────────────────────────────

@router.get("/loans/at-risk")
def get_high_risk_loans(
    risk_level: str = "High",
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_officer)
):
    """
    Get list of loans at risk of bouncing.
    
    Query params:
      - risk_level: Filter by 'High', 'Medium', or 'Low' (default: High)
      - limit: Max results (default: 50)
    """
    
    profiles = db.query(BounceRiskProfile).filter(
        BounceRiskProfile.risk_level == risk_level
    ).order_by(
        BounceRiskProfile.risk_score.desc()
    ).limit(limit).all()
    
    results = []
    for profile in profiles:
        loan = db.query(Loan).filter(Loan.loan_id == profile.loan_id).first()
        customer = db.query(Customer).filter(Customer.customer_id == profile.customer_id).first()
        
        # Check auto-pay
        auto_pay = db.query(AutoPayMandate).filter(
            AutoPayMandate.loan_id == profile.loan_id,
            AutoPayMandate.status == "Active"
        ).first()
        
        results.append({
            "loan_id": profile.loan_id,
            "customer_id": profile.customer_id,
            "customer_name": customer.customer_name if customer else "Unknown",
            "loan_type": loan.loan_type if loan else "Unknown",
            "emi_amount": loan.emi_amount if loan else 0,
            "days_past_due": loan.days_past_due if loan else 0,
            "risk_score": profile.risk_score,
            "risk_level": profile.risk_level,
            "bounce_probability": profile.next_emi_bounce_probability,
            "predicted_bounce_date": profile.predicted_bounce_date,
            "auto_pay_enabled": auto_pay is not None,
            "recommended_action": calculate_bounce_risk(loan, [], profile)['recommended_action'] if loan else "N/A"
        })
    
    return {
        "risk_level": risk_level,
        "total_count": len(results),
        "loans": results
    }
