"""Check bounce risk data in database"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import BounceRiskProfile, Loan, Customer

db = SessionLocal()

profiles = db.query(BounceRiskProfile).all()
print(f"Total bounce risk profiles: {len(profiles)}")

high = [p for p in profiles if p.risk_level == 'High']
medium = [p for p in profiles if p.risk_level == 'Medium']
low = [p for p in profiles if p.risk_level == 'Low']

print(f"High risk: {len(high)}")
print(f"Medium risk: {len(medium)}")
print(f"Low risk: {len(low)}")

print("\nHigh risk loans (first 5):")
for p in high[:5]:
    loan = db.query(Loan).filter(Loan.loan_id == p.loan_id).first()
    customer = db.query(Customer).filter(Customer.customer_id == p.customer_id).first()
    print(f"  {p.loan_id}: {customer.customer_name if customer else 'N/A'} - Score: {p.risk_score}")

db.close()
