"""
Performance & Coaching Management Router
Endpoints for agent performance tracking, call analysis, and coaching features
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import (
    CallSession, CopilotSuggestion, CallSummary, AgentPerformance,
    CoachingFeedback, CoachingSession, SuccessPattern, BankOfficer,
    Customer, gen_uuid
)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import json
import requests
import os

router = APIRouter(prefix="/performance", tags=["performance"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# ─────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────
class AnalyzeCallRequest(BaseModel):
    call_session_id: str


class CallSummaryResponse(BaseModel):
    summary_id: str
    call_session_id: str
    customer_id: str
    officer_id: str
    call_date: str
    call_duration: float
    outcome: Optional[str]
    sentiment_start: float
    sentiment_end: float
    sentiment_trend: str
    tonality: str
    key_moments: List[dict]
    strengths: List[str]
    improvements: List[str]
    coaching_tips: List[str]
    overall_score: float


class PerformanceMetricsResponse(BaseModel):
    officer_id: str
    officer_name: str
    period_start: str
    period_end: str
    total_calls: int
    success_rate: float
    avg_sentiment: float
    escalation_rate: float
    overall_score: float


class LeaderboardEntry(BaseModel):
    rank: int
    officer_id: str
    officer_name: str
    overall_score: float
    success_rate: float
    total_calls: int


class AnalyzeBatchRequest(BaseModel):
    limit: int = 10  # Maximum number of calls to analyze


class ScheduleCoachingRequest(BaseModel):
    officer_id: str
    session_type: str  # "1-on-1", "group", "workshop"
    topic: str
    scheduled_date: str  # ISO format: "2026-04-20T10:00:00"
    notes: Optional[str] = None


class ScheduleCoachingResponse(BaseModel):
    session_id: str
    officer_id: str
    officer_name: str
    session_type: str
    topic: str
    scheduled_date: str
    status: str
    message: str


class GenerateReportRequest(BaseModel):
    officer_id: Optional[str] = None  # If None, generate team report
    period_days: int = 30
    format: str = "json"  # "json", "summary"


class AgentPerformanceItem(BaseModel):
    agent_id: str
    name: str
    performance_score: float
    recovery_rate: float
    total_calls: int
    avatar_color: str


class AgentDetailedInsights(BaseModel):
    last_interactions: List[dict]
    strengths: List[str]
    improvements: List[str]
    coaching_recommendation: str


class TeamPerformanceResponse(BaseModel):
    agents: List[AgentPerformanceItem]
    period_days: int
    generated_at: str


class GenerateReportResponse(BaseModel):
    report_type: str
    period: dict
    officer_data: Optional[dict] = None
    team_summary: Optional[dict] = None
    recommendations: List[str]
    generated_at: str


# ─────────────────────────────────────────────
# Helper: Call LLM for Analysis
# ─────────────────────────────────────────────
def _analyze_call_with_llm(transcript: str, sentiment_data: dict) -> dict:
    """
    Use Ollama Llama3.1 to analyze call transcript and generate coaching insights
    """
    prompt = f"""You are an expert call quality analyst for a loan collections team. Analyze this customer service call transcript and provide detailed coaching insights.

CALL TRANSCRIPT:
{transcript}

SENTIMENT DATA:
- Sentiment Score: {sentiment_data.get('sentiment_score', 0.0)}
- Tonality: {sentiment_data.get('tonality', 'Neutral')}

Please analyze the call and provide:

1. STRENGTHS (2-4 bullet points):
   - What did the agent do well?
   - Specific phrases or techniques that were effective

2. IMPROVEMENTS (2-4 bullet points):
   - What could be improved?
   - Missed opportunities or mistakes

3. COACHING TIPS (2-4 actionable recommendations):
   - Specific techniques the agent should practice
   - Alternative approaches they could try

4. OVERALL SCORE (0-10):
   - Rate the overall quality of the call

5. SENTIMENT TREND:
   - Did customer sentiment improve, decline, or stay stable during the call?
   - Respond with ONLY ONE WORD: "Improved", "Declined", or "Stable"

6. KEY MOMENTS (1-3 critical turning points):
   - Specific moments that impacted the call outcome
   - Format: [DICT with time and event keys]

Format your response as JSON:
{{
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "coaching_tips": ["...", "..."],
  "overall_score": 7.5,
  "sentiment_trend": "Improved",
  "key_moments": [{{"time": "early", "event": "customer became frustrated"}}, {{"time": "mid", "event": "agent offered solution"}}]
}}

Respond ONLY with valid JSON, no additional text."""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")
        
        result_text = response.json().get("response", "").strip()
        
        # Try to extract JSON if wrapped in markdown
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(result_text)
        return analysis
        
    except Exception as e:
        print(f"[Performance] LLM analysis failed: {e}")
        # Fallback to basic analysis
        return {
            "strengths": ["Professional tone maintained throughout call"],
            "improvements": ["Could provide more specific payment solutions"],
            "coaching_tips": ["Practice active listening techniques", "Use empathy statements more frequently"],
            "overall_score": 6.0,
            "sentiment_trend": "Stable",
            "key_moments": [{"time": "mid", "event": "Customer expressed willingness to pay"}]
        }


async def _generate_coaching_recommendation(
    officer_name: str,
    summaries: list,
    strengths: list,
    improvements: list
) -> str:
    """
    Generate comprehensive coaching recommendation using LLM
    Based on officer's performance across multiple calls
    """
    
    if not summaries:
        return "Insufficient data to generate coaching recommendations."
    
    # Calculate aggregate metrics
    total_calls = len(summaries)
    avg_score = sum(s.overall_score for s in summaries) / total_calls
    avg_sentiment = sum(s.sentiment_end for s in summaries) / total_calls
    
    # Count outcomes
    outcomes = {}
    for s in summaries:
        outcome = s.outcome or "Unknown"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    prompt = f"""You are an expert performance coach for loan collection officers. Generate a comprehensive coaching recommendation for {officer_name}.

PERFORMANCE DATA (Last {total_calls} calls):
- Average Call Quality Score: {avg_score:.1f}/10
- Average Customer Sentiment: {avg_sentiment:.2f} (-1 to +1 scale)
- Call Outcomes: {json.dumps(outcomes)}

IDENTIFIED STRENGTHS:
{chr(10).join(f"- {s}" for s in strengths[:4])}

AREAS FOR IMPROVEMENT:
{chr(10).join(f"- {i}" for i in improvements[:4])}

Please generate a detailed coaching recommendation (100-200 words) that includes:
1. Recognition of specific strengths
2. 2-3 actionable improvement strategies with concrete steps
3. Suggested training, mentorship, or development activities
4. Measurable goals for next 30-60 days

Write in a professional, encouraging, and actionable tone. Focus on specific techniques and outcomes.

COACHING RECOMMENDATION:"""

    try:
        print(f"[Performance] Generating coaching for {officer_name} using Ollama at {OLLAMA_URL}")
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3.1:8b",  # Changed from llama3.1 to llama3.1:8b
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 300}
            },
            timeout=30
        )
        
        print(f"[Performance] Ollama response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json().get("response", "").strip()
            print(f"[Performance] Ollama generated {len(result)} characters")
            # Clean up any markdown or formatting
            result = result.replace("**", "").replace("##", "").strip()
            if result:
                print(f"[Performance] ✅ Coaching generated successfully")
                return result
            else:
                print(f"[Performance] ⚠️ Empty response from Ollama, using fallback")
                return f"{officer_name} shows consistent performance with room for growth. Focus on strengthening customer engagement and exploring flexible payment solutions proactively."
        else:
            print(f"[Performance] ⚠️ Ollama returned status {response.status_code}, using fallback")
            print(f"[Performance] Response: {response.text[:200]}")
            return f"{officer_name} shows consistent performance with room for growth. Focus on strengthening customer engagement and exploring flexible payment solutions proactively."
            
    except Exception as e:
        print(f"[Performance] ❌ LLM coaching generation failed: {e}")
        import traceback
        traceback.print_exc()
        return f"{officer_name} demonstrates solid performance. Continue building on identified strengths while addressing improvement areas through targeted practice and mentorship."


# ─────────────────────────────────────────────
# Endpoint: Analyze Single Call
# ─────────────────────────────────────────────
@router.post("/analyze-call", response_model=CallSummaryResponse)
async def analyze_call(request: AnalyzeCallRequest, db: Session = Depends(get_db)):
    """
    Analyze a call session using LLM to generate coaching insights
    Creates a CallSummary record with strengths, improvements, coaching tips
    """
    
    # 1. Fetch call session
    call = db.query(CallSession).filter(CallSession.call_session_id == request.call_session_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call session not found")
    
    # 2. Fetch copilot suggestion for sentiment data
    suggestion = db.query(CopilotSuggestion).filter(
        CopilotSuggestion.call_session_id == request.call_session_id
    ).first()
    
    sentiment_data = {
        "sentiment_score": suggestion.sentiment_score if suggestion else 0.0,
        "tonality": suggestion.tonality if suggestion else "Neutral"
    }
    
    # 3. Use LLM to analyze call
    transcript = call.transcript or "No transcript available"
    analysis = _analyze_call_with_llm(transcript, sentiment_data)
    
    # 4. Calculate sentiment start/end (simplified - you could parse transcript for this)
    sentiment_start = sentiment_data["sentiment_score"]
    sentiment_end = sentiment_start + 0.5 if analysis["sentiment_trend"] == "Improved" else sentiment_start
    
    # 5. Determine call duration (simplified - assume 5 minutes if not available)
    call_duration = 300.0  # You could parse this from call metadata
    
    # 6. Determine outcome (could be inferred from transcript or set manually)
    outcome = "Analyzed"  # Could be: 'Payment Promise', 'Grace Request', 'Escalated', etc.
    
    # 7. Create CallSummary record
    from backend.db.models import gen_uuid
    summary = CallSummary(
        summary_id=gen_uuid(),
        call_session_id=request.call_session_id,
        customer_id=call.customer_id,
        officer_id=call.officer_id or "unknown",
        call_date=call.upload_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        call_duration=call_duration,
        outcome=outcome,
        sentiment_start=sentiment_start,
        sentiment_end=sentiment_end,
        sentiment_trend=analysis.get("sentiment_trend", "Stable"),
        tonality=sentiment_data["tonality"],
        key_moments=json.dumps(analysis.get("key_moments", [])),
        strengths=json.dumps(analysis.get("strengths", [])),
        improvements=json.dumps(analysis.get("improvements", [])),
        coaching_tips=json.dumps(analysis.get("coaching_tips", [])),
        overall_score=analysis.get("overall_score", 0.0)
    )
    
    db.add(summary)
    db.commit()
    db.refresh(summary)
    
    # 8. Return response
    return CallSummaryResponse(
        summary_id=summary.summary_id,
        call_session_id=summary.call_session_id,
        customer_id=summary.customer_id,
        officer_id=summary.officer_id,
        call_date=summary.call_date,
        call_duration=summary.call_duration,
        outcome=summary.outcome,
        sentiment_start=summary.sentiment_start,
        sentiment_end=summary.sentiment_end,
        sentiment_trend=summary.sentiment_trend,
        tonality=summary.tonality,
        key_moments=json.loads(summary.key_moments),
        strengths=json.loads(summary.strengths),
        improvements=json.loads(summary.improvements),
        coaching_tips=json.loads(summary.coaching_tips),
        overall_score=summary.overall_score
    )


# ─────────────────────────────────────────────
# Endpoint: Get Team Performance Dashboard
# ─────────────────────────────────────────────
@router.get("/team-dashboard")
async def get_team_dashboard(
    period_days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get aggregated performance metrics for all officers
    Returns: Key metrics, leaderboard, recent coaching alerts
    """
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Get all officers
    officers = db.query(BankOfficer).all()
    
    leaderboard = []
    total_calls_all = 0
    total_success_all = 0
    avg_sentiment_all = []
    
    for officer in officers:
        # Get all call summaries for this officer in period
        summaries = db.query(CallSummary).filter(
            CallSummary.officer_id == officer.officer_id,
            CallSummary.call_date >= start_str,
            CallSummary.call_date <= end_str
        ).all()
        
        if not summaries:
            continue
        
        total_calls = len(summaries)
        avg_score = sum(s.overall_score for s in summaries) / total_calls if total_calls > 0 else 0.0
        avg_sent = sum(s.sentiment_end for s in summaries) / total_calls if total_calls > 0 else 0.0
        
        # Count successful calls (score >= 7.0)
        successful = sum(1 for s in summaries if s.overall_score >= 7.0)
        success_rate = (successful / total_calls * 100) if total_calls > 0 else 0.0
        
        leaderboard.append({
            "officer_id": officer.officer_id,
            "officer_name": officer.officer_name,
            "total_calls": total_calls,
            "overall_score": round(avg_score, 2),
            "success_rate": round(success_rate, 1),
            "avg_sentiment": round(avg_sent, 2)
        })
        
        total_calls_all += total_calls
        total_success_all += successful
        avg_sentiment_all.append(avg_sent)
    
    # Sort leaderboard by overall score
    leaderboard.sort(key=lambda x: x["overall_score"], reverse=True)
    
    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    # Calculate team-wide metrics
    team_success_rate = (total_success_all / total_calls_all * 100) if total_calls_all > 0 else 0.0
    team_avg_sentiment = sum(avg_sentiment_all) / len(avg_sentiment_all) if avg_sentiment_all else 0.0
    
    # Get recent coaching alerts (high priority feedback)
    try:
        coaching_alerts = db.query(CoachingFeedback).filter(
            CoachingFeedback.priority == "High",
            CoachingFeedback.status == "Pending"
        ).limit(5).all()
    except Exception as e:
        print(f"[Performance] Warning: Could not fetch coaching alerts: {e}")
        coaching_alerts = []
    
    return {
        "period": {
            "start_date": start_str,
            "end_date": end_str,
            "days": period_days
        },
        "team_metrics": {
            "total_calls": total_calls_all,
            "success_rate": round(team_success_rate, 1),
            "avg_sentiment": round(team_avg_sentiment, 2),
            "total_officers": len(leaderboard)
        },
        "leaderboard": leaderboard[:10],  # Top 10
        "coaching_alerts": [
            {
                "feedback_id": alert.feedback_id,
                "officer_id": alert.officer_id,
                "issue_category": alert.issue_category or "General",
                "feedback_text": alert.feedback_text[:100] + "..." if len(alert.feedback_text) > 100 else alert.feedback_text,
                "created_at": alert.created_at
            }
            for alert in coaching_alerts
        ]
    }



# ─────────────────────────────────────────────
# Endpoint: Get Team Performance (All Officers)
# ─────────────────────────────────────────────
@router.get("/team", response_model=TeamPerformanceResponse)
async def get_team_performance(
    period_days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for all officers
    Returns aggregated data from CallSummary table
    """
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Get all officers
    officers = db.query(BankOfficer).all()
    
    agents = []
    avatar_colors = ["bg-blue-500", "bg-green-500", "bg-purple-500", "bg-orange-500", 
                     "bg-pink-500", "bg-red-500", "bg-indigo-500", "bg-yellow-500"]
    
    for idx, officer in enumerate(officers):
        # Get call summaries for this officer in the period
        summaries = db.query(CallSummary).filter(
            CallSummary.officer_id == officer.officer_id,
            CallSummary.call_date >= start_str,
            CallSummary.call_date <= end_str
        ).all()
        
        if not summaries:
            # Skip officers with no calls in this period
            continue
        
        total_calls = len(summaries)
        
        # Calculate recovery rate (successful outcomes)
        successful_outcomes = ["Payment Received", "Payment Scheduled", "Grace Period Approved", 
                              "Restructure Approved", "Settlement Agreed"]
        successful = sum(1 for s in summaries if s.outcome in successful_outcomes)
        recovery_rate = round((successful / total_calls * 100), 1) if total_calls > 0 else 0.0
        
        # Calculate performance score (average overall_score)
        performance_score = round(sum(s.overall_score for s in summaries) / total_calls, 1) if total_calls > 0 else 0.0
        
        agents.append(AgentPerformanceItem(
            agent_id=officer.officer_id,
            name=officer.officer_name,
            performance_score=performance_score,
            recovery_rate=recovery_rate,
            total_calls=total_calls,
            avatar_color=avatar_colors[idx % len(avatar_colors)]
        ))
    
    # Sort by performance score descending
    agents.sort(key=lambda x: x.performance_score, reverse=True)
    
    return TeamPerformanceResponse(
        agents=agents,
        period_days=period_days,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


# ─────────────────────────────────────────────
# Endpoint: Get Individual Officer Performance
# ─────────────────────────────────────────────
@router.get("/officer/{officer_id}", response_model=PerformanceMetricsResponse)
async def get_officer_performance(
    officer_id: str,
    period_days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get detailed performance metrics for a specific officer
    """
    
    # Get officer details
    officer = db.query(BankOfficer).filter(BankOfficer.officer_id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Get all call summaries for this officer
    summaries = db.query(CallSummary).filter(
        CallSummary.officer_id == officer_id,
        CallSummary.call_date >= start_str,
        CallSummary.call_date <= end_str
    ).all()
    
    if not summaries:
        return PerformanceMetricsResponse(
            officer_id=officer_id,
            officer_name=officer.officer_name,
            period_start=start_str,
            period_end=end_str,
            total_calls=0,
            success_rate=0.0,
            avg_sentiment=0.0,
            escalation_rate=0.0,
            overall_score=0.0
        )
    
    total_calls = len(summaries)
    successful = sum(1 for s in summaries if s.overall_score >= 7.0)
    success_rate = (successful / total_calls * 100) if total_calls > 0 else 0.0
    
    avg_sentiment = sum(s.sentiment_end for s in summaries) / total_calls if total_calls > 0 else 0.0
    overall_score = sum(s.overall_score for s in summaries) / total_calls if total_calls > 0 else 0.0
    
    # Count escalated calls (low sentiment or specific outcome)
    escalated = sum(1 for s in summaries if s.outcome == "Escalated" or s.sentiment_end < -0.5)
    escalation_rate = (escalated / total_calls * 100) if total_calls > 0 else 0.0
    
    return PerformanceMetricsResponse(
        officer_id=officer_id,
        officer_name=officer.officer_name,
        period_start=start_str,
        period_end=end_str,
        total_calls=total_calls,
        success_rate=round(success_rate, 1),
        avg_sentiment=round(avg_sentiment, 2),
        escalation_rate=round(escalation_rate, 1),
        overall_score=round(overall_score, 2)
    )


# ─────────────────────────────────────────────
# Endpoint: Get Officer Detailed Insights
# ─────────────────────────────────────────────
@router.get("/officer/{officer_id}/insights", response_model=AgentDetailedInsights)
async def get_officer_insights(
    officer_id: str,
    period_days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get detailed coaching insights for a specific officer:
    - Last 3 interactions
    - Strengths (from AI analysis)
    - Improvements needed
    - AI-generated coaching recommendations
    """
    
    # Get officer details
    officer = db.query(BankOfficer).filter(BankOfficer.officer_id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Get call summaries for this officer, sorted by date (most recent first)
    summaries = db.query(CallSummary).filter(
        CallSummary.officer_id == officer_id,
        CallSummary.call_date >= start_str,
        CallSummary.call_date <= end_str
    ).order_by(CallSummary.call_date.desc()).limit(3).all()
    
    if not summaries:
        # Return empty insights if no calls
        return AgentDetailedInsights(
            last_interactions=[],
            strengths=["No call data available for this period"],
            improvements=["Insufficient data to provide recommendations"],
            coaching_recommendation="No calls recorded in the selected period. Encourage the officer to engage with more customers."
        )
    
    # Build last interactions
    last_interactions = []
    for summary in summaries:
        customer = db.query(Customer).filter(Customer.customer_id == summary.customer_id).first()
        last_interactions.append({
            "id": summary.summary_id,
            "customer_name": customer.customer_name if customer else "Unknown Customer",
            "date": summary.call_date,
            "outcome": summary.outcome or "No outcome recorded",
            "sentiment": "Positive" if summary.sentiment_end > 0.3 else ("Negative" if summary.sentiment_end < -0.3 else "Neutral"),
            "duration": f"{int(summary.call_duration // 60):02d}:{int(summary.call_duration % 60):02d} min"
        })
    
    # Aggregate strengths and improvements from LAST 3 CALLS ONLY (not all calls in period)
    # Use the same 'summaries' list that was already fetched for last_interactions
    recent_summaries = summaries  # These are already the last 3 calls, ordered by date desc
    
    # Parse strengths and improvements from JSON
    all_strengths = []
    all_improvements = []
    for s in recent_summaries:
        if s.strengths:
            try:
                strengths_list = json.loads(s.strengths) if isinstance(s.strengths, str) else s.strengths
                all_strengths.extend(strengths_list)
            except:
                pass
        if s.improvements:
            try:
                improvements_list = json.loads(s.improvements) if isinstance(s.improvements, str) else s.improvements
                all_improvements.extend(improvements_list)
            except:
                pass
    
    # Get unique strengths and improvements (preserve order, remove duplicates)
    seen_strengths = set()
    top_strengths = []
    for s in all_strengths:
        if s not in seen_strengths:
            seen_strengths.add(s)
            top_strengths.append(s)
    
    seen_improvements = set()
    top_improvements = []
    for i in all_improvements:
        if i not in seen_improvements:
            seen_improvements.add(i)
            top_improvements.append(i)
    
    # Limit to reasonable number
    top_strengths = top_strengths[:6]
    top_improvements = top_improvements[:5]
    
    if not top_strengths:
        top_strengths = ["Consistent call handling", "Follows standard procedures"]
    if not top_improvements:
        top_improvements = ["Continue current performance trajectory"]
    
    # Generate comprehensive coaching recommendation using LLM
    # Pass ALL summaries in period for comprehensive analysis
    all_summaries_for_coaching = db.query(CallSummary).filter(
        CallSummary.officer_id == officer_id,
        CallSummary.call_date >= start_str,
        CallSummary.call_date <= end_str
    ).all()
    
    coaching_recommendation = await _generate_coaching_recommendation(
        officer.officer_name,
        all_summaries_for_coaching,  # Use all summaries for coaching context
        top_strengths,
        top_improvements
    )
    
    return AgentDetailedInsights(
        last_interactions=last_interactions,
        strengths=top_strengths,
        improvements=top_improvements,
        coaching_recommendation=coaching_recommendation
    )


# ─────────────────────────────────────────────
# Endpoint: Batch Analyze Unanalyzed Calls
# ─────────────────────────────────────────────
@router.post("/analyze-batch")
async def analyze_batch_calls(request: AnalyzeBatchRequest, db: Session = Depends(get_db)):
    """
    Find unanalyzed call sessions and run AI analysis on them
    Returns: Count of analyzed calls and total unanalyzed
    """
    
    # Get all call sessions
    all_calls = db.query(CallSession).filter(
        CallSession.status == "completed"
    ).all()
    
    # Get all call session IDs that have been analyzed
    analyzed_ids = set(
        summary.call_session_id 
        for summary in db.query(CallSummary).all()
    )
    
    # Find unanalyzed calls
    unanalyzed_calls = [
        call for call in all_calls 
        if call.call_session_id not in analyzed_ids
    ]
    
    total_unanalyzed = len(unanalyzed_calls)
    
    # Limit to requested number
    calls_to_analyze = unanalyzed_calls[:request.limit]
    analyzed_count = 0
    
    for call in calls_to_analyze:
        try:
            # Check if copilot suggestion exists
            suggestion = db.query(CopilotSuggestion).filter(
                CopilotSuggestion.call_session_id == call.call_session_id
            ).first()
            
            if not suggestion:
                # Create a basic suggestion if it doesn't exist
                suggestion = CopilotSuggestion(
                    suggestion_id=call.call_session_id + "_sug",
                    call_session_id=call.call_session_id,
                    customer_id=call.customer_id,
                    sentiment_score=0.0,
                    tonality="Neutral"
                )
                db.add(suggestion)
                db.commit()
            
            # Analyze the call
            analyze_request = AnalyzeCallRequest(call_session_id=call.call_session_id)
            await analyze_call(analyze_request, db)
            analyzed_count += 1
            
        except Exception as e:
            print(f"[Performance] Warning: Failed to analyze call {call.call_session_id}: {e}")
            continue
    
    return {
        "analyzed_count": analyzed_count,
        "total_unanalyzed": total_unanalyzed,
        "remaining_unanalyzed": total_unanalyzed - analyzed_count,
        "message": f"Successfully analyzed {analyzed_count} out of {total_unanalyzed} unanalyzed calls"
    }


# ─────────────────────────────────────────────
# Endpoint: Analyze All Unanalyzed Calls (Simple GET)
# ─────────────────────────────────────────────
@router.get("/analyze-all")
async def analyze_all_calls(limit: int = 50, db: Session = Depends(get_db)):
    """
    Simple GET endpoint to analyze all unanalyzed calls
    Useful for quick triggers without POST body
    """
    request = AnalyzeBatchRequest(limit=limit)
    return await analyze_batch_calls(request, db)


# ─────────────────────────────────────────────
# Endpoint: Get Call Details with Coaching Insights
# ─────────────────────────────────────────────
@router.get("/call/{call_session_id}")
async def get_call_details(call_session_id: str, db: Session = Depends(get_db)):
    """
    Get full call details including transcript, analysis, and coaching insights
    """
    
    # Get call summary
    summary = db.query(CallSummary).filter(
        CallSummary.call_session_id == call_session_id
    ).first()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Call summary not found")
    
    # Get original call session for transcript
    call = db.query(CallSession).filter(
        CallSession.call_session_id == call_session_id
    ).first()
    
    # Get customer details
    customer = db.query(Customer).filter(
        Customer.customer_id == summary.customer_id
    ).first()
    
    return {
        "call_session_id": call_session_id,
        "customer_name": customer.name if customer else "Unknown",
        "officer_id": summary.officer_id,
        "call_date": summary.call_date,
        "call_duration": summary.call_duration,
        "transcript": call.transcript if call else "No transcript available",
        "analysis": {
            "sentiment_start": summary.sentiment_start,
            "sentiment_end": summary.sentiment_end,
            "sentiment_trend": summary.sentiment_trend,
            "tonality": summary.tonality,
            "overall_score": summary.overall_score,
            "outcome": summary.outcome
        },
        "coaching": {
            "key_moments": json.loads(summary.key_moments),
            "strengths": json.loads(summary.strengths),
            "improvements": json.loads(summary.improvements),
            "coaching_tips": json.loads(summary.coaching_tips)
        }
    }


# ─────────────────────────────────────────────
# Endpoint: Schedule Coaching Session
# ─────────────────────────────────────────────
@router.post("/schedule-coaching", response_model=ScheduleCoachingResponse)
async def schedule_coaching(request: ScheduleCoachingRequest, db: Session = Depends(get_db)):
    """
    Schedule a coaching session for a specific officer
    """
    
    # Validate officer exists
    officer = db.query(BankOfficer).filter(
        BankOfficer.officer_id == request.officer_id
    ).first()
    
    if not officer:
        raise HTTPException(status_code=404, detail=f"Officer {request.officer_id} not found")
    
    # Validate session type
    valid_types = ["1-on-1", "group", "workshop", "training"]
    if request.session_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid session_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Parse and validate date
    try:
        scheduled_datetime = datetime.fromisoformat(request.scheduled_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid scheduled_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
        )
    
    # Check if date is in the future
    if scheduled_datetime < datetime.now():
        raise HTTPException(
            status_code=400, 
            detail="Scheduled date must be in the future"
        )
    
    # Create coaching session (note: model uses string for dates, not datetime)
    coaching_session = CoachingSession(
        session_id=gen_uuid(),
        officer_id=request.officer_id,
        session_type=request.session_type,
        topic=request.topic,
        scheduled_date=scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        notes=request.notes or ""
    )
    
    db.add(coaching_session)
    db.commit()
    db.refresh(coaching_session)
    
    return ScheduleCoachingResponse(
        session_id=coaching_session.session_id,
        officer_id=coaching_session.officer_id,
        officer_name=officer.officer_name,
        session_type=coaching_session.session_type,
        topic=coaching_session.topic,
        scheduled_date=coaching_session.scheduled_date,
        status="scheduled",
        message=f"Coaching session scheduled successfully for {officer.officer_name}"
    )


# ─────────────────────────────────────────────
# Endpoint: Get Scheduled Coaching Sessions
# ─────────────────────────────────────────────
@router.get("/coaching-sessions")
async def get_coaching_sessions(
    officer_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all coaching sessions, optionally filtered by officer
    """
    
    query = db.query(CoachingSession)
    
    if officer_id:
        query = query.filter(CoachingSession.officer_id == officer_id)
    
    sessions = query.order_by(CoachingSession.scheduled_date.desc()).all()
    
    # Join with officer data
    result = []
    for session in sessions:
        officer = db.query(BankOfficer).filter(
            BankOfficer.officer_id == session.officer_id
        ).first()
        
        # Determine status based on scheduled_date vs current time
        status = "scheduled"
        if session.completed_date:
            status = "completed"
        elif session.scheduled_date:
            try:
                sched_dt = datetime.strptime(session.scheduled_date, "%Y-%m-%d %H:%M:%S")
                if sched_dt < datetime.now():
                    status = "past"
            except:
                status = "scheduled"
        
        result.append({
            "session_id": session.session_id,
            "officer_id": session.officer_id,
            "officer_name": officer.officer_name if officer else "Unknown",
            "session_type": session.session_type,
            "topic": session.topic,
            "scheduled_date": session.scheduled_date,
            "completed_date": session.completed_date,
            "status": status,
            "notes": session.notes,
            "created_at": session.created_at
        })
    
    return {
        "total_sessions": len(result),
        "sessions": result
    }


# ─────────────────────────────────────────────
# Endpoint: Generate Performance Report
# ─────────────────────────────────────────────
@router.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest, db: Session = Depends(get_db)):
    """
    Generate comprehensive performance report for officer or team
    """
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=request.period_days)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    recommendations = []
    
    # Individual Officer Report
    if request.officer_id:
        officer = db.query(BankOfficer).filter(
            BankOfficer.officer_id == request.officer_id
        ).first()
        
        if not officer:
            raise HTTPException(status_code=404, detail=f"Officer {request.officer_id} not found")
        
        # Get call summaries for this officer
        summaries = db.query(CallSummary).filter(
            CallSummary.officer_id == request.officer_id,
            CallSummary.call_date >= start_str,
            CallSummary.call_date <= end_str
        ).all()
        
        if not summaries:
            return GenerateReportResponse(
                report_type="individual",
                period={"start": start_str, "end": end_str, "days": request.period_days},
                officer_data={
                    "officer_id": request.officer_id,
                    "officer_name": officer.officer_name,
                    "total_calls": 0,
                    "message": "No call data available for this period"
                },
                recommendations=["Start logging customer interactions"],
                generated_at=datetime.now().isoformat()
            )
        
        # Calculate metrics
        total_calls = len(summaries)
        avg_score = sum(s.overall_score for s in summaries) / total_calls
        successful = sum(1 for s in summaries if s.overall_score >= 7.0)
        success_rate = (successful / total_calls * 100) if total_calls > 0 else 0
        
        sentiment_scores = [s.sentiment_end for s in summaries if s.sentiment_end is not None]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Collect all strengths and improvements
        all_strengths = []
        all_improvements = []
        for s in summaries:
            if s.strengths:
                all_strengths.extend(json.loads(s.strengths))
            if s.improvements:
                all_improvements.extend(json.loads(s.improvements))
        
        # Generate recommendations
        if avg_score < 6.0:
            recommendations.append("⚠️ PRIORITY: Schedule immediate coaching session - performance below target")
        if success_rate < 70:
            recommendations.append("📉 Success rate needs improvement - review call handling techniques")
        if avg_sentiment < 0:
            recommendations.append("😟 Customer sentiment is negative - focus on empathy and active listening")
        if avg_score >= 8.0:
            recommendations.append("⭐ Excellent performance! Consider this officer as a peer mentor")
        
        if not recommendations:
            recommendations.append("✅ Performance is good - continue current practices")
        
        officer_data = {
            "officer_id": request.officer_id,
            "officer_name": officer.officer_name,
            "total_calls": total_calls,
            "overall_score": round(avg_score, 2),
            "success_rate": round(success_rate, 1),
            "avg_sentiment": round(avg_sentiment, 2),
            "top_strengths": list(set(all_strengths))[:5],
            "key_improvements": list(set(all_improvements))[:5],
            "performance_trend": "improving" if avg_score >= 7.0 else "needs_attention"
        }
        
        return GenerateReportResponse(
            report_type="individual",
            period={"start": start_str, "end": end_str, "days": request.period_days},
            officer_data=officer_data,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
    
    # Team Report
    else:
        officers = db.query(BankOfficer).all()
        
        team_stats = {
            "total_officers": len(officers),
            "total_calls": 0,
            "avg_team_score": 0,
            "top_performers": [],
            "needs_coaching": []
        }
        
        officer_performances = []
        
        for officer in officers:
            summaries = db.query(CallSummary).filter(
                CallSummary.officer_id == officer.officer_id,
                CallSummary.call_date >= start_str,
                CallSummary.call_date <= end_str
            ).all()
            
            if summaries:
                total_calls = len(summaries)
                avg_score = sum(s.overall_score for s in summaries) / total_calls
                
                officer_performances.append({
                    "officer_id": officer.officer_id,
                    "officer_name": officer.officer_name,
                    "total_calls": total_calls,
                    "avg_score": round(avg_score, 2)
                })
                
                team_stats["total_calls"] += total_calls
        
        # Calculate team average
        if officer_performances:
            team_stats["avg_team_score"] = round(
                sum(op["avg_score"] for op in officer_performances) / len(officer_performances), 2
            )
            
            # Sort by score
            officer_performances.sort(key=lambda x: x["avg_score"], reverse=True)
            
            # Top performers (score >= 8.0)
            team_stats["top_performers"] = [
                op for op in officer_performances if op["avg_score"] >= 8.0
            ][:5]
            
            # Needs coaching (score < 6.0)
            team_stats["needs_coaching"] = [
                op for op in officer_performances if op["avg_score"] < 6.0
            ]
        
        # Team recommendations
        if len(team_stats["needs_coaching"]) > 0:
            recommendations.append(f"⚠️ {len(team_stats['needs_coaching'])} officers need immediate coaching")
        if len(team_stats["top_performers"]) > 0:
            recommendations.append(f"⭐ {len(team_stats['top_performers'])} top performers - consider peer mentoring program")
        if team_stats["avg_team_score"] >= 7.5:
            recommendations.append("✅ Team performance is excellent!")
        elif team_stats["avg_team_score"] < 6.0:
            recommendations.append("📉 Team-wide training recommended")
        
        if not recommendations:
            recommendations.append("Continue monitoring performance metrics")
        
        return GenerateReportResponse(
            report_type="team",
            period={"start": start_str, "end": end_str, "days": request.period_days},
            team_summary=team_stats,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
