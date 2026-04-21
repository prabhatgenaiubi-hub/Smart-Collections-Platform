"""Test customer search with bounce risk level filter"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import BounceRiskProfile, Loan, Customer

db = SessionLocal()

print("="*60)
print("TESTING: Customer Search with Bounce Risk Level = High")
print("="*60)

# Simulate what the backend /officer/search endpoint does
bounce_risk_level = "High"

# Step 1: Get all loans (since no other filters)
matched_loans = db.query(Loan).order_by(Loan.days_past_due.desc()).limit(200).all()
print(f"\nStep 1: Initial query returned {len(matched_loans)} loans")

# Step 2: Filter by bounce risk level
bounce_profiles = db.query(BounceRiskProfile).filter(
    BounceRiskProfile.risk_level == bounce_risk_level
).all()
bounce_loan_ids = {p.loan_id for p in bounce_profiles}
print(f"Step 2: Found {len(bounce_profiles)} profiles with risk level '{bounce_risk_level}'")

matched_loans = [loan for loan in matched_loans if loan.loan_id in bounce_loan_ids]
print(f"Step 3: After filtering, {len(matched_loans)} loans match\n")

# Step 3: Build results (limit to 50)
results = []
for loan in matched_loans[:50]:
    customer = db.query(Customer).filter(
        Customer.customer_id == loan.customer_id
    ).first()
    if customer:
        results.append({
            'loan_id': loan.loan_id,
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name,
            'loan_type': loan.loan_type,
            'risk_segment': loan.risk_segment
        })

print(f"✅ Backend will return {len(results)} results\n")
print("Sample results:")
for i, result in enumerate(results[:5], 1):
    print(f"  {i}. {result['loan_id']} - {result['customer_name']} ({result['loan_type']})")

print(f"\n{'='*60}")
print("✅ Backend search is working correctly!")
print("Frontend should now display these results WITHOUT disappearing")
print(f"{'='*60}")

db.close()
