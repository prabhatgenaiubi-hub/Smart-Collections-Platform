"""
One-time script to seed bounce prevention data
"""
from backend.db.database import SessionLocal
from backend.db.models import Loan, PaymentHistory, BounceRiskProfile, AutoPayMandate, BouncePreventionAction
from analytics.bounce_predictor import calculate_bounce_risk, predict_bounce_date
from datetime import datetime, timedelta
import json

def seed_bounce_prevention():
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing_count = db.query(BounceRiskProfile).count()
        if existing_count > 0:
            print(f"⚠️  Already have {existing_count} bounce risk profiles. Skipping...")
            return
        
        print("🚀 Starting bounce prevention data seeding...")
        
        # Generate risk profiles for ALL 53 loans
        all_loans = db.query(Loan).all()
        bounce_profiles = []
        
        for loan in all_loans:
            payments = db.query(PaymentHistory).filter(PaymentHistory.loan_id == loan.loan_id).all()
            risk_data = calculate_bounce_risk(loan, payments, None)
            
            # Mock bounce counts based on risk level
            if risk_data['level'] == 'High':
                bounce_6m, bounce_12m = 3, 5
            elif risk_data['level'] == 'Medium':
                bounce_6m, bounce_12m = 1, 2
            else:
                bounce_6m, bounce_12m = 0, 0
            
            profile = BounceRiskProfile(
                loan_id=loan.loan_id,
                customer_id=loan.customer_id,
                risk_score=risk_data['score'],
                risk_level=risk_data['level'],
                risk_factors=json.dumps(risk_data['factors']),
                bounce_count_3m=bounce_6m,
                bounce_count_6m=bounce_6m,
                bounce_count_12m=bounce_12m,
                next_emi_bounce_probability=risk_data['next_emi_bounce_probability'],
                predicted_bounce_date=predict_bounce_date(loan, risk_data['next_emi_bounce_probability'])
            )
            bounce_profiles.append(profile)
        
        db.add_all(bounce_profiles)
        print(f"✅ Created {len(bounce_profiles)} bounce risk profiles")
        
        # 5 Auto-pay mandates
        auto_pay_mandates = [
            AutoPayMandate(
                loan_id="LOAN002",
                customer_id="CUST002",
                status="Active",
                mandate_type="e-NACH",
                bank_account_number="XXXX1234",
                ifsc_code="SBIN0001234",
                max_amount=15000.0,
                activated_at=datetime.now() - timedelta(days=30),
                activated_by="customer",
                activation_channel="app",
                first_debit_date="2026-05-05",
                expiry_date="2027-05-05"
            ),
            AutoPayMandate(
                loan_id="LOAN006",
                customer_id="CUST006",
                status="Active",
                mandate_type="e-NACH",
                bank_account_number="XXXX5678",
                ifsc_code="HDFC0002345",
                max_amount=5500.0,
                activated_at=datetime.now() - timedelta(days=20),
                activated_by="customer",
                activation_channel="web",
                first_debit_date="2026-05-10",
                expiry_date="2027-05-10"
            ),
            AutoPayMandate(
                loan_id="LOAN009",
                customer_id="CUST009",
                status="Active",
                mandate_type="e-NACH",
                bank_account_number="XXXX9012",
                ifsc_code="ICIC0003456",
                max_amount=6000.0,
                activated_at=datetime.now() - timedelta(days=15),
                activated_by="customer",
                activation_channel="app",
                first_debit_date="2026-05-15",
                expiry_date="2027-05-15"
            ),
            AutoPayMandate(
                loan_id="LOAN013",
                customer_id="CUST013",
                status="Active",
                mandate_type="e-NACH",
                bank_account_number="XXXX3456",
                ifsc_code="AXIS0004567",
                max_amount=4500.0,
                activated_at=datetime.now() - timedelta(days=10),
                activated_by="customer",
                activation_channel="branch",
                first_debit_date="2026-05-20",
                expiry_date="2027-05-20"
            ),
            AutoPayMandate(
                loan_id="LOAN025",
                customer_id="CUST005",
                status="Pending",
                mandate_type="e-NACH",
                bank_account_number="XXXX7890",
                ifsc_code="SBIN0005678",
                max_amount=10000.0,
                activation_channel="whatsapp",
                first_debit_date="2026-05-25",
                expiry_date="2027-05-25"
            ),
        ]
        db.add_all(auto_pay_mandates)
        print(f"✅ Created {len(auto_pay_mandates)} auto-pay mandates")
        
        # 5 Prevention actions
        prevention_actions = [
            BouncePreventionAction(
                loan_id="LOAN003",
                customer_id="CUST003",
                action_type="whatsapp",
                risk_level_at_trigger="High",
                message_content="Enable Auto-Pay to avoid missing EMI payments",
                triggered_at=datetime.now() - timedelta(days=5),
                executed_at=datetime.now() - timedelta(days=5),
                status="sent"
            ),
            BouncePreventionAction(
                loan_id="LOAN005",
                customer_id="CUST005",
                action_type="voice_call",
                risk_level_at_trigger="High",
                message_content="Officer called customer about auto-pay",
                triggered_at=datetime.now() - timedelta(days=10),
                executed_at=datetime.now() - timedelta(days=10),
                status="delivered",
                customer_response="enrolled",
                bounce_prevented=1
            ),
            BouncePreventionAction(
                loan_id="LOAN012",
                customer_id="CUST012",
                action_type="auto_pay_link",
                risk_level_at_trigger="Medium",
                message_content="Auto-pay enrollment link sent via SMS",
                triggered_at=datetime.now() - timedelta(days=3),
                executed_at=datetime.now() - timedelta(days=3),
                status="sent"
            ),
            BouncePreventionAction(
                loan_id="LOAN018",
                customer_id="CUST018",
                action_type="sms",
                risk_level_at_trigger="Medium",
                message_content="Reminder: Enable Auto-Pay to avoid late fees",
                triggered_at=datetime.now() - timedelta(days=7),
                executed_at=datetime.now() - timedelta(days=7),
                status="delivered"
            ),
            BouncePreventionAction(
                loan_id="LOAN027",
                customer_id="CUST007",
                action_type="whatsapp",
                risk_level_at_trigger="High",
                message_content="Auto-pay benefits and enrollment link",
                triggered_at=datetime.now() - timedelta(days=12),
                executed_at=datetime.now() - timedelta(days=12),
                status="delivered",
                customer_response="enrolled",
                bounce_prevented=1
            ),
        ]
        db.add_all(prevention_actions)
        print(f"✅ Created {len(prevention_actions)} prevention actions")
        
        db.commit()
        print("\n🎉 Bounce prevention data seeded successfully!")
        print(f"   - {len(bounce_profiles)} risk profiles")
        print(f"   - {len(auto_pay_mandates)} auto-pay mandates")
        print(f"   - {len(prevention_actions)} prevention actions")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_bounce_prevention()
