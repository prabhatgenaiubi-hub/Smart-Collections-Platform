"""Check bounce risk scores distribution"""
import sys
sys.path.append('d:/Prabhat/GenAI Prabhat/Smart-Collections-Platform')

from backend.db.database import SessionLocal
from backend.db.models import BounceRiskProfile

db = SessionLocal()

profiles = db.query(BounceRiskProfile).all()
print(f"Total profiles: {len(profiles)}\n")

# Group by score ranges
ranges = {
    '70-100 (High)': 0,
    '50-69': 0,
    '40-49 (Medium)': 0,
    '30-39': 0,
    '20-29': 0,
    '10-19': 0,
    '0-9 (Low)': 0
}

for p in profiles:
    score = p.risk_score
    if score >= 70:
        ranges['70-100 (High)'] += 1
    elif score >= 50:
        ranges['50-69'] += 1
    elif score >= 40:
        ranges['40-49 (Medium)'] += 1
    elif score >= 30:
        ranges['30-39'] += 1
    elif score >= 20:
        ranges['20-29'] += 1
    elif score >= 10:
        ranges['10-19'] += 1
    else:
        ranges['0-9 (Low)'] += 1

print("Score distribution:")
for range_name, count in ranges.items():
    print(f"  {range_name}: {count}")

# Show top 10 highest scores
print("\nTop 10 highest risk scores:")
sorted_profiles = sorted(profiles, key=lambda p: p.risk_score, reverse=True)
for p in sorted_profiles[:10]:
    print(f"  {p.loan_id}: {p.risk_score} ({p.risk_level})")

db.close()
