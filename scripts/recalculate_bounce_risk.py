"""Recalculate bounce risk profiles with new thresholds"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import BounceRiskProfile, Loan, PaymentHistory
from analytics.bounce_predictor import calculate_bounce_risk
import json

db = SessionLocal()

# Get all existing profiles
profiles = db.query(BounceRiskProfile).all()
print(f"Found {len(profiles)} existing bounce risk profiles")

updated_count = 0
for profile in profiles:
    # Get the loan and payment history
    loan = db.query(Loan).filter(Loan.loan_id == profile.loan_id).first()
    if not loan:
        print(f"⚠️  Loan {profile.loan_id} not found, skipping...")
        continue
    
    # Get payment history
    payment_history = db.query(PaymentHistory).filter(
        PaymentHistory.loan_id == profile.loan_id
    ).order_by(PaymentHistory.payment_date.desc()).limit(12).all()
    
    # Recalculate with new thresholds
    risk_data = calculate_bounce_risk(loan, payment_history, profile)
    
    # Update the profile
    old_level = profile.risk_level
    profile.risk_score = risk_data['score']
    profile.risk_level = risk_data['level']
    profile.risk_factors = json.dumps(risk_data['factors'])
    profile.next_emi_bounce_probability = risk_data['next_emi_bounce_probability']
    
    if old_level != risk_data['level']:
        print(f"  {profile.loan_id}: {old_level} → {risk_data['level']} (score: {risk_data['score']})")
        updated_count += 1

db.commit()
print(f"\n✅ Recalculated all profiles. {updated_count} changed risk levels.")

# Show new distribution
high = db.query(BounceRiskProfile).filter(BounceRiskProfile.risk_level == 'High').count()
medium = db.query(BounceRiskProfile).filter(BounceRiskProfile.risk_level == 'Medium').count()
low = db.query(BounceRiskProfile).filter(BounceRiskProfile.risk_level == 'Low').count()

print(f"\nNew distribution:")
print(f"  High: {high}")
print(f"  Medium: {medium}")
print(f"  Low: {low}")

db.close()
