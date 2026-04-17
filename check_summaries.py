"""Check call summaries in database"""
from backend.db.database import SessionLocal
from backend.db.models import CallSummary
from datetime import datetime, timedelta

db = SessionLocal()

summaries = db.query(CallSummary).all()
print(f'✓ Total call summaries: {len(summaries)}')

end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

print(f'✓ Date range: {start_str} to {end_str}')

filtered = [s for s in summaries if s.call_date >= start_str and s.call_date <= end_str]
print(f'✓ In last 30 days: {len(filtered)}')

if filtered:
    print(f'\n✓ Sample summaries:')
    for s in filtered[:10]:
        print(f'  {s.call_date} - Officer: {s.officer_id}, Score: {s.overall_score}')
else:
    print('\n⚠ No summaries in date range!')
    if summaries:
        print(f'  Earliest: {min(s.call_date for s in summaries)}')
        print(f'  Latest: {max(s.call_date for s in summaries)}')

db.close()
