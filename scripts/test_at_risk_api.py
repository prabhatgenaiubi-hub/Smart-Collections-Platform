"""Test the at-risk loans API endpoint"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import BounceRiskProfile, Loan, Customer, AutoPayMandate

db = SessionLocal()

# Simulate what the API endpoint does
profiles = db.query(BounceRiskProfile).filter(
    BounceRiskProfile.risk_level == "High"
).order_by(
    BounceRiskProfile.risk_score.desc()
).limit(50).all()

print(f"Found {len(profiles)} high-risk profiles\n")

results = []
for profile in profiles[:5]:  # Show first 5
    loan = db.query(Loan).filter(Loan.loan_id == profile.loan_id).first()
    customer = db.query(Customer).filter(Customer.customer_id == profile.customer_id).first()
    
    # Check auto-pay
    auto_pay = db.query(AutoPayMandate).filter(
        AutoPayMandate.loan_id == profile.loan_id,
        AutoPayMandate.status == "Active"
    ).first()
    
    print(f"{profile.loan_id}:")
    print(f"  Customer: {customer.customer_name if customer else 'Unknown'}")
    print(f"  Risk Score: {profile.risk_score}")
    print(f"  Auto-Pay: {'Yes' if auto_pay else 'No'}")
    print()

db.close()
