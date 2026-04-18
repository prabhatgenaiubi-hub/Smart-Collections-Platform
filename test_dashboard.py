"""Debug dashboard endpoint"""
from backend.db.database import SessionLocal
from backend.db.models import BankOfficer, CallSummary
from datetime import datetime, timedelta

db = SessionLocal()

# Check officers
officers = db.query(BankOfficer).all()
print(f"✓ Officers: {len(officers)}")

# Check date range
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")
print(f"✓ Date range: {start_str} to {end_str}")

# Check all summaries
summaries = db.query(CallSummary).all()
print(f"✓ Total call summaries: {len(summaries)}")

if summaries:
    print(f"✓ Sample dates: {summaries[0].call_date}, {summaries[-1].call_date}")
    
    # Check filtering
    filtered = [s for s in summaries if s.call_date >= start_str and s.call_date <= end_str]
    print(f"✓ Filtered summaries: {len(filtered)}")
    
    # Check officer_id
    for s in summaries[:3]:
        print(f"  - Summary {s.summary_id[:8]}: officer={s.officer_id}, date={s.call_date}")
        officer = db.query(BankOfficer).filter(BankOfficer.officer_id == s.officer_id).first()
        if officer:
            print(f"    Officer found: {officer.name}")
        else:
            print(f"    ⚠ Officer NOT FOUND!")

db.close()
