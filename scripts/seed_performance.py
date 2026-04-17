"""
Seed Performance Data Script
Creates sample call sessions and analyzes them to populate performance dashboard
Run: python -m scripts.seed_performance
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import SessionLocal
from backend.db.models import (
    gen_uuid, Customer, BankOfficer, CallSession, CopilotSuggestion
)


def create_sample_call_sessions():
    """Create sample call sessions with different scenarios"""
    
    db = SessionLocal()
    
    try:
        # Get all customers and officers
        customers = db.query(Customer).limit(10).all()
        officers = db.query(BankOfficer).all()
        
        if not customers:
            print("❌ No customers found. Run seed_data.py first.")
            return
        
        if not officers:
            print("❌ No officers found. Run seed_data.py first.")
            return
        
        print(f"📊 Found {len(customers)} customers and {len(officers)} officers")
        
        # Sample transcripts with different quality levels
        sample_transcripts = [
            # High quality (8-9/10)
            {
                "transcript": "Officer: Good afternoon, this is Sarah from ABC Bank. I'm calling regarding your loan payment. How are you today?\n\nCustomer: I'm okay, just a bit stressed about the payment.\n\nOfficer: I completely understand. Financial situations can be challenging. Let me help you explore your options. I see you have a payment due soon. Can you tell me about your current situation?\n\nCustomer: I lost my job last month, so I'm struggling.\n\nOfficer: I'm really sorry to hear that. That must be very difficult. The good thing is we have several options to support you during this time. Would you be interested in a grace period while you get back on your feet?\n\nCustomer: Yes, that would be really helpful.\n\nOfficer: Perfect. I can set up a 2-month grace period for you. You'll also have access to job placement resources through our partner organizations. Does that sound good?\n\nCustomer: That sounds amazing, thank you so much!\n\nOfficer: You're welcome. We're here to help. I'll send you the details via email today.",
                "sentiment": 0.7,
                "tonality": "Empathetic"
            },
            # Medium quality (6-7/10)
            {
                "transcript": "Officer: Hello, this is John from ABC Bank. You have a payment due.\n\nCustomer: Yes, I know. I'm having some trouble.\n\nOfficer: Okay, what kind of trouble?\n\nCustomer: I lost my job.\n\nOfficer: I see. Well, you still need to pay. Can you make a partial payment?\n\nCustomer: I don't have much money right now.\n\nOfficer: Maybe you can borrow from family? We need at least half payment.\n\nCustomer: I'll try.\n\nOfficer: Okay, please pay by next week. Thanks.",
                "sentiment": 0.0,
                "tonality": "Neutral"
            },
            # Low quality (3-5/10)
            {
                "transcript": "Officer: This is ABC Bank. You missed payment. Why?\n\nCustomer: I'm having financial problems.\n\nOfficer: That's not our problem. You took the loan, you have to pay.\n\nCustomer: I understand, but I need some time.\n\nOfficer: You already had enough time. Pay now or we'll take action.\n\nCustomer: This is ridiculous! I want to speak to your manager!\n\nOfficer: Manager won't help you. Just pay the loan.\n\nCustomer: I'm filing a complaint!\n\nOfficer: Fine. You still need to pay though.",
                "sentiment": -0.8,
                "tonality": "Aggressive"
            },
            # Excellent quality (9-10/10)
            {
                "transcript": "Officer: Good morning! This is Priya from ABC Bank. I hope you're doing well today.\n\nCustomer: Hi, yes, I'm okay.\n\nOfficer: That's great to hear. I'm reaching out because I noticed you might benefit from our new flexible payment plan. I wanted to share some options that could make your loan management easier.\n\nCustomer: Oh, that's interesting. What kind of options?\n\nOfficer: Based on your excellent payment history, we can offer you a reduced interest rate and the option to extend your loan term if that helps with monthly cash flow. Also, you're eligible for our financial wellness program.\n\nCustomer: Wow, I didn't know about these programs!\n\nOfficer: Yes! We want to support customers like you who are doing well. Would you like me to email you the details, or would you prefer to discuss now?\n\nCustomer: Email would be great. Thank you so much for calling!\n\nOfficer: My pleasure! You'll receive the email within 30 minutes. If you have any questions, feel free to call me directly. Have a wonderful day!",
                "sentiment": 0.9,
                "tonality": "Professional & Warm"
            }
        ]
        
        # Create call sessions for the past 30 days
        calls_created = 0
        
        for i in range(30):
            # Create 2-5 calls per day
            num_calls = random.randint(2, 5)
            
            for j in range(num_calls):
                # Random date in past 30 days
                days_ago = random.randint(0, 29)
                call_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
                
                # Random customer and officer
                customer = random.choice(customers)
                officer = random.choice(officers)
                
                # Random transcript
                transcript_data = random.choice(sample_transcripts)
                
                # Create call session
                call = CallSession(
                    call_session_id=gen_uuid(),
                    customer_id=customer.customer_id,
                    officer_id=officer.officer_id,
                    transcript=transcript_data["transcript"],
                    language_detected="English",
                    status="completed",
                    upload_time=call_date
                )
                
                db.add(call)
                db.flush()
                
                # Create copilot suggestion
                suggestion = CopilotSuggestion(
                    suggestion_id=gen_uuid(),
                    call_session_id=call.call_session_id,
                    customer_id=customer.customer_id,
                    sentiment_score=transcript_data["sentiment"],
                    tonality=transcript_data["tonality"],
                    suggested_responses='["Show empathy", "Offer payment plan", "Thank customer"]',
                    questions_to_ask='["What is your current employment status?", "Can you make a partial payment?"]',
                    nudges='["Remember to stay calm", "Use customer name"]',
                    created_at=call_date
                )
                
                db.add(suggestion)
                calls_created += 1
        
        db.commit()
        print(f"✅ Created {calls_created} sample call sessions")
        
        # Now analyze all calls
        print("\n📊 Analyzing calls to generate performance data...")
        
        from backend.routers.performance import analyze_call, AnalyzeCallRequest
        
        all_calls = db.query(CallSession).all()
        analyzed_count = 0
        
        for call in all_calls[:20]:  # Analyze first 20 calls
            try:
                # Create request
                request = AnalyzeCallRequest(call_session_id=call.call_session_id)
                
                # Import asyncio to run async function
                import asyncio
                
                # Analyze call
                asyncio.run(analyze_call(request, db))
                analyzed_count += 1
                print(f"  ✓ Analyzed call {analyzed_count}/20")
                
            except Exception as e:
                print(f"  ⚠ Warning: Failed to analyze call {call.call_session_id}: {e}")
                continue
        
        print(f"\n✅ Successfully analyzed {analyzed_count} calls")
        print("\n🎉 Performance data seeding complete!")
        print("\n📈 You can now view the dashboard at: http://localhost:5174/officer/performance")
        
    except Exception as e:
        print(f"❌ Error seeding performance data: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_call_sessions()
