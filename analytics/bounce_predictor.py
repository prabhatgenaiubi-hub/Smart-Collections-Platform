"""
Bounce Risk Prediction Module

Calculates bounce risk for EMI payments based on:
- Payment history patterns
- Current delinquency status
- Historical bounce data
- Balance behavior
- Risk segment
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.db.models import Loan, PaymentHistory, BounceRiskProfile


def calculate_bounce_risk(
    loan: Loan,
    payment_history: List[PaymentHistory],
    bounce_profile: Optional[BounceRiskProfile] = None
) -> Dict:
    """
    Calculate bounce risk score (0-100) and level (Low/Medium/High).
    
    Args:
        loan: Loan object with current status
        payment_history: List of payment records
        bounce_profile: Existing bounce profile (if any)
    
    Returns:
        {
            'score': float (0-100),
            'level': str ('Low'/'Medium'/'High'),
            'factors': dict with detailed breakdown,
            'next_emi_bounce_probability': float (0-1),
            'recommended_action': str
        }
    """
    
    score = 0.0
    factors = {}
    
    # ─────────────────────────────────────────────
    # Factor 1: Current Delinquency Status (40% weight)
    # ─────────────────────────────────────────────
    dpd = loan.days_past_due or 0
    
    if dpd > 90:
        delinquency_score = 40
        factors['delinquency'] = 'Critical (90+ days)'
    elif dpd > 30:
        delinquency_score = 35
        factors['delinquency'] = 'Severe (30-90 days)'
    elif dpd > 15:
        delinquency_score = 25
        factors['delinquency'] = 'High (15-30 days)'
    elif dpd > 7:
        delinquency_score = 15
        factors['delinquency'] = 'Moderate (7-15 days)'
    elif dpd > 0:
        delinquency_score = 5
        factors['delinquency'] = 'Minor (1-7 days)'
    else:
        delinquency_score = 0
        factors['delinquency'] = 'Current'
    
    score += delinquency_score
    factors['days_past_due'] = dpd
    
    # ─────────────────────────────────────────────
    # Factor 2: Payment Pattern Analysis (30% weight)
    # ─────────────────────────────────────────────
    if payment_history:
        total_payments = len(payment_history)
        # PaymentHistory doesn't have days_late or payment_status fields
        # We'll use a simpler heuristic based on payment amount vs EMI
        late_payments = 0
        missed_payments = 0
        
        # Consider a payment late if amount < EMI or if it's significantly less
        for p in payment_history:
            if hasattr(p, 'payment_amount') and hasattr(loan, 'emi_amount'):
                if p.payment_amount == 0:
                    missed_payments += 1
                elif p.payment_amount < loan.emi_amount * 0.9:  # Less than 90% of EMI
                    late_payments += 1
        
        late_payment_rate = late_payments / total_payments if total_payments > 0 else 0
        
        if late_payment_rate > 0.5 or missed_payments > 2:
            pattern_score = 30
            factors['payment_pattern'] = 'Poor (>50% late)'
        elif late_payment_rate > 0.3 or missed_payments > 1:
            pattern_score = 20
            factors['payment_pattern'] = 'Below Average (30-50% late)'
        elif late_payment_rate > 0.1:
            pattern_score = 10
            factors['payment_pattern'] = 'Fair (10-30% late)'
        else:
            pattern_score = 0
            factors['payment_pattern'] = 'Good (<10% late)'
        
        score += pattern_score
        factors['late_payment_count'] = late_payments
        factors['missed_payment_count'] = missed_payments
    else:
        factors['payment_pattern'] = 'No history available'
        factors['late_payment_count'] = 0
        factors['missed_payment_count'] = 0
    
    # ─────────────────────────────────────────────
    # Factor 3: Historical Bounce Data (20% weight)
    # ─────────────────────────────────────────────
    if bounce_profile:
        bounce_6m = bounce_profile.bounce_count_6m or 0
        
        if bounce_6m >= 3:
            bounce_score = 20
            factors['bounce_history'] = f'High ({bounce_6m} bounces in 6 months)'
        elif bounce_6m == 2:
            bounce_score = 15
            factors['bounce_history'] = 'Moderate (2 bounces in 6 months)'
        elif bounce_6m == 1:
            bounce_score = 10
            factors['bounce_history'] = 'Low (1 bounce in 6 months)'
        else:
            bounce_score = 0
            factors['bounce_history'] = 'No recent bounces'
        
        score += bounce_score
        factors['bounce_count_6m'] = bounce_6m
    else:
        factors['bounce_history'] = 'No data available'
        factors['bounce_count_6m'] = 0
    
    # ─────────────────────────────────────────────
    # Factor 4: Risk Segment (10% weight)
    # ─────────────────────────────────────────────
    risk_segment = loan.risk_segment or 'Low'
    
    if risk_segment == 'High':
        segment_score = 10
    elif risk_segment == 'Medium':
        segment_score = 5
    else:
        segment_score = 0
    
    score += segment_score
    factors['risk_segment'] = risk_segment
    
    # ─────────────────────────────────────────────
    # Determine Risk Level
    # ─────────────────────────────────────────────
    # Adjusted thresholds for more realistic distribution:
    # High: 55+ (was 70+)
    # Medium: 30-54 (was 40-69)
    # Low: 0-29 (was 0-39)
    if score >= 55:
        risk_level = 'High'
        recommended_action = 'Enable e-NACH immediately + Officer call'
    elif score >= 30:
        risk_level = 'Medium'
        recommended_action = 'Send auto-pay enrollment link + WhatsApp reminder'
    else:
        risk_level = 'Low'
        recommended_action = 'Monitor payment behavior'
    
    # ─────────────────────────────────────────────
    # Calculate Next EMI Bounce Probability
    # ─────────────────────────────────────────────
    # Simple model: score/100 gives probability
    next_emi_bounce_probability = min(score / 100.0, 0.95)  # Cap at 95%
    
    return {
        'score': round(score, 2),
        'level': risk_level,
        'factors': factors,
        'next_emi_bounce_probability': round(next_emi_bounce_probability, 3),
        'recommended_action': recommended_action,
        'calculation_timestamp': datetime.now().isoformat()
    }


def get_recommended_outreach_channel(risk_level: str, customer_preferred_channel: str = None) -> str:
    """
    Recommend outreach channel based on bounce risk level.
    
    Args:
        risk_level: 'Low', 'Medium', or 'High'
        customer_preferred_channel: Customer's preferred channel (optional)
    
    Returns:
        Recommended channel: 'whatsapp', 'voice_call', 'email', 'sms'
    """
    
    if risk_level == 'High':
        return 'voice_call'  # Immediate personal touch
    elif risk_level == 'Medium':
        return customer_preferred_channel.lower() if customer_preferred_channel else 'whatsapp'
    else:
        return 'email'  # Low priority, informational


def generate_auto_pay_message(customer_name: str, loan_type: str, emi_amount: float) -> str:
    """
    Generate personalized auto-pay enrollment message.
    
    Args:
        customer_name: Customer's name
        loan_type: Type of loan
        emi_amount: Monthly EMI amount
    
    Returns:
        Personalized message text
    """
    
    return f"""
Dear {customer_name},

We noticed you have a {loan_type} with monthly EMI of ₹{emi_amount:,.2f}.

To avoid missing any payments and penalties, we recommend enabling Auto-Pay (e-NACH):

✅ Never miss an EMI
✅ No late payment charges
✅ Maintain good credit score
✅ Peace of mind

Click here to enable auto-pay in 2 minutes: [AUTO_PAY_LINK]

Need help? Reply to this message.

Regards,
Collections Team
""".strip()


def predict_bounce_date(loan: Loan, bounce_probability: float) -> Optional[str]:
    """
    Predict when next bounce is likely to occur.
    
    Args:
        loan: Loan object
        bounce_probability: Probability of bounce (0-1)
    
    Returns:
        Predicted date (YYYY-MM-DD) or None
    """
    
    if bounce_probability < 0.3:
        return None  # Low risk, no specific prediction
    
    # Assume next EMI date is the risk point
    try:
        # Parse EMI due date (format: "DD/MM/YYYY" or "YYYY-MM-DD")
        emi_date_str = loan.emi_due_date
        
        if '/' in emi_date_str:
            # DD/MM/YYYY format
            day, month, year = map(int, emi_date_str.split('/'))
            next_emi_date = datetime(year, month, day)
        else:
            # YYYY-MM-DD format
            next_emi_date = datetime.strptime(emi_date_str, '%Y-%m-%d')
        
        # If date is in past, move to next month
        today = datetime.now()
        while next_emi_date < today:
            # Move to next month (simple approximation)
            if next_emi_date.month == 12:
                next_emi_date = next_emi_date.replace(year=next_emi_date.year + 1, month=1)
            else:
                next_emi_date = next_emi_date.replace(month=next_emi_date.month + 1)
        
        return next_emi_date.strftime('%Y-%m-%d')
    
    except Exception:
        # If parsing fails, return None
        return None
