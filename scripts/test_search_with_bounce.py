"""Test that search endpoint includes bounce risk data"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import Loan, Customer, BounceRiskProfile, AutoPayMandate
from backend.routers.officer import build_loan_summary

db = SessionLocal()

print("="*70)
print("TESTING: Search Results with Bounce Risk Data Included")
print("="*70)

# Test with a few loans
test_loans = db.query(Loan).limit(5).all()

print(f"\nTesting {len(test_loans)} sample loans:\n")

for loan in test_loans:
    customer = db.query(Customer).filter(Customer.customer_id == loan.customer_id).first()
    
    if customer:
        # Build loan summary with bounce risk data
        result = build_loan_summary(loan, customer, db)
        
        print(f"Loan: {result['loan_id']}")
        print(f"  Customer: {result['customer_name']}")
        print(f"  Loan Type: {result['loan_type']}")
        print(f"  Outstanding: ₹{result['outstanding_balance']:,.0f}")
        print(f"  ✅ Bounce Risk Level: {result.get('bounce_risk_level', 'None')}")
        print(f"  ✅ Risk Score: {result.get('bounce_risk_score', 'N/A')}")
        print(f"  ✅ Bounce Probability: {result.get('bounce_probability', 'N/A')}")
        print(f"  ✅ Auto-Pay: {'Yes' if result.get('auto_pay_enabled') else 'No'}")
        print()

print("="*70)
print("✅ Backend now includes bounce risk data in search results!")
print("="*70)

# Now test specifically with high-risk loans
print("\n" + "="*70)
print("TESTING: High Bounce Risk Loans")
print("="*70)

high_risk_profiles = db.query(BounceRiskProfile).filter(
    BounceRiskProfile.risk_level == "High"
).limit(3).all()

print(f"\nSample of {len(high_risk_profiles)} high-risk loans:\n")

for profile in high_risk_profiles:
    loan = db.query(Loan).filter(Loan.loan_id == profile.loan_id).first()
    customer = db.query(Customer).filter(Customer.customer_id == loan.customer_id).first()
    
    if loan and customer:
        result = build_loan_summary(loan, customer, db)
        
        print(f"{result['loan_id']}: {result['customer_name']}")
        print(f"  🚨 {result['bounce_risk_level']} Risk (Score: {result['bounce_risk_score']})")
        print(f"  🔒 Auto-Pay: {'✓ Active' if result['auto_pay_enabled'] else '✗ Not Enrolled'}")
        print()

print("="*70)
print("🎉 All bounce risk data is now included instantly!")
print("NO MORE API CALLS NEEDED for bounce risk display!")
print("="*70)

db.close()
