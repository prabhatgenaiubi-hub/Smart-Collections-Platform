"""
Sentiment & Interaction Analysis Agent

Responsibilities:
  - Detect sentiment from conversation text using
    cardiffnlp/twitter-roberta-base-sentiment-latest (HuggingFace)
  - Classify tonality (Positive / Neutral / Negative)
  - Generate interaction summary
  - Store interaction summary in Chroma Vector DB
  - Update interaction record in SQL

The RoBERTa model is loaded once at module level and reused for all
subsequent calls (singleton pattern). Falls back to keyword rules if
the model cannot be loaded (e.g. no internet on first run).
"""

import re
from datetime import datetime
from sqlalchemy.orm import Session
from backend.db.models import InteractionHistory


# ─────────────────────────────────────────────
# RoBERTa Sentiment Model  (singleton)
# ─────────────────────────────────────────────

_sentiment_pipeline = None   # loaded lazily on first call

def _get_pipeline():
    """
    Load cardiffnlp/twitter-roberta-base-sentiment-latest once and cache it.
    Falls back to None if the model cannot be loaded.
    """
    global _sentiment_pipeline
    if _sentiment_pipeline is not None:
        return _sentiment_pipeline
    try:
        from transformers import pipeline
        print("[SentimentAgent] Loading cardiffnlp/twitter-roberta-base-sentiment-latest ...")
        _sentiment_pipeline = pipeline(
            task          = "text-classification",
            model         = "cardiffnlp/twitter-roberta-base-sentiment-latest",
            tokenizer     = "cardiffnlp/twitter-roberta-base-sentiment-latest",
            top_k         = 1,           # return only the best label
            truncation    = True,
            max_length    = 512,
        )
        print("[SentimentAgent] Model loaded successfully.")
    except Exception as e:
        print(f"[SentimentAgent] Could not load RoBERTa model, falling back to keywords: {e}")
        _sentiment_pipeline = None
    return _sentiment_pipeline


# ─────────────────────────────────────────────
# Fallback Keyword Lists  (used when model unavailable)
# ─────────────────────────────────────────────

POSITIVE_KEYWORDS = [
    "thank", "appreciate", "happy", "great", "good", "excellent",
    "satisfied", "pleased", "helpful", "resolved", "paid", "prepay",
    "on time", "confirm", "agreed", "cooperate", "interest", "savings"
]

NEGATIVE_KEYWORDS = [
    "frustrated", "angry", "upset", "cannot", "unable", "missed",
    "delay", "overdue", "problem", "issue", "hardship", "struggling",
    "difficult", "stressed", "distress", "loss", "business down",
    "no money", "cannot pay", "need more time", "emergency", "worried"
]


def _keyword_score(text: str) -> float:
    """Keyword-based fallback scoring."""
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round(max(-1.0, min(1.0, (pos - neg) / total)), 2)


# ─────────────────────────────────────────────
# Sentiment Score Calculation
# ─────────────────────────────────────────────

# RoBERTa label → numeric score mapping
_LABEL_TO_SCORE = {
    "positive": 1.0,
    "neutral":  0.0,
    "negative": -1.0,
}

# Collections-domain keywords that always signal financial distress,
# regardless of surrounding positive phrasing (Whisper hallucinations, etc.)
_DISTRESS_PHRASES = [
    "cannot pay", "can't pay", "not able to pay", "unable to pay",
    "will not pay", "won't pay", "don't want to pay", "not going to pay",
    "lost my job", "no money", "no income", "lost income", "out of work",
    "missed emi", "missed payment", "overdue", "defaulting", "bankruptcy",
    "can't afford", "cannot afford", "no funds", "financial hardship",
    "struggling to pay", "not paying", "refuse to pay",
]


def _score_chunk(pipe, chunk: str) -> float:
    """Score a single text chunk with the RoBERTa pipeline."""
    output = pipe(chunk[:512])
    best = output[0][0] if isinstance(output[0], list) else output[0]
    label = best["label"].lower()
    confidence = best["score"]
    base = _LABEL_TO_SCORE.get(label, 0.0)
    return round(base * confidence, 2)


def calculate_sentiment_score(text: str) -> float:
    """
    Calculate sentiment score from conversation text.

    Score range: -1.0 (very negative) to +1.0 (very positive)
    0.0 = Neutral

    Method:
      1. Domain override: if the text contains explicit financial-distress
         phrases (e.g. "cannot pay", "lost my job") apply a strong negative
         anchor BEFORE the model runs. This prevents Whisper transcription
         artefacts (e.g. a hallucinated "I am very excited") from masking
         clear negative intent.

      2. Chunk scoring: split the transcript into sentences (~2-3 per chunk)
         and score each chunk independently with
         cardiffnlp/twitter-roberta-base-sentiment-latest.  The final score
         is a weighted blend:
           - mean of all chunk scores   (weight 0.4)
           - most negative chunk score  (weight 0.6)
         This prevents a single positive sentence from cancelling out several
         negative ones (a common problem with long call transcripts).

      3. Blend the distress anchor (if triggered) with the model score:
           final = 0.5 * anchor + 0.5 * model_score

      4. Fall back to keyword counting if the model is unavailable.
    """
    if not text or not text.strip():
        return 0.0

    text_lower = text.lower()

    # ── Step 1: distress anchor ───────────────────────────────────
    distress_hit = any(phrase in text_lower for phrase in _DISTRESS_PHRASES)
    distress_anchor = -0.7 if distress_hit else None   # strong negative prior

    pipe = _get_pipeline()

    if pipe is not None:
        try:
            # ── Step 2: chunk the text into sentences ─────────────
            # Split on sentence-ending punctuation; keep chunks ~80 chars
            raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())

            # Group into chunks of 2 sentences to give the model enough context
            chunks: list[str] = []
            for i in range(0, len(raw_sentences), 2):
                chunk = " ".join(raw_sentences[i:i + 2]).strip()
                if chunk:
                    chunks.append(chunk)

            if not chunks:
                chunks = [text[:512]]

            # Score each chunk
            chunk_scores = [_score_chunk(pipe, c) for c in chunks]

            mean_score = sum(chunk_scores) / len(chunk_scores)
            min_score  = min(chunk_scores)   # most negative segment

            # Weighted blend: negative segments pull harder (60 %)
            model_score = round(0.4 * mean_score + 0.6 * min_score, 2)

            # ── Step 3: blend with distress anchor if triggered ───
            if distress_anchor is not None:
                final = round(0.5 * distress_anchor + 0.5 * model_score, 2)
                print(
                    f"[SentimentAgent] Distress anchor triggered. "
                    f"anchor={distress_anchor}, model={model_score}, final={final}"
                )
            else:
                final = model_score

            return final

        except Exception as e:
            print(f"[SentimentAgent] Inference error, falling back to keywords: {e}")

    # ── Step 4: keyword fallback ──────────────────────────────────
    kw_score = _keyword_score(text)
    if distress_anchor is not None:
        return round(0.5 * distress_anchor + 0.5 * kw_score, 2)
    return kw_score


# ─────────────────────────────────────────────
# Tonality Classification
# ─────────────────────────────────────────────

def classify_tonality(sentiment_score: float) -> str:
    """
    Classify tonality based on sentiment score.

    Returns:
        "Positive"  → score > 0.2
        "Negative"  → score < -0.2
        "Neutral"   → -0.2 <= score <= 0.2
    """
    if sentiment_score > 0.2:
        return "Positive"
    elif sentiment_score < -0.2:
        return "Negative"
    else:
        return "Neutral"


# ─────────────────────────────────────────────
# Interaction Summary Generator
# ─────────────────────────────────────────────

def generate_interaction_summary(
    conversation_text: str,
    interaction_type: str,
    tonality: str,
    customer_name: str = "Customer"
) -> str:
    """
    Generate a concise summary of the interaction.

    For the prototype this uses rule-based template generation.
    In production, this would call the LLM Reasoning Agent.
    """
    if not conversation_text:
        return f"{customer_name} had a {interaction_type.lower()} interaction with the bank."

    text_lower = conversation_text.lower()

    # Detect key topics
    topics = []

    if any(kw in text_lower for kw in ["grace", "grace period"]):
        topics.append("grace period request")

    if any(kw in text_lower for kw in ["restructur", "restructure", "restructuring"]):
        topics.append("loan restructuring inquiry")

    if any(kw in text_lower for kw in ["emi", "payment", "pay"]):
        topics.append("EMI payment discussion")

    if any(kw in text_lower for kw in ["prepay", "prepayment", "foreclose"]):
        topics.append("prepayment/foreclosure inquiry")

    if any(kw in text_lower for kw in ["outstanding", "balance", "amount"]):
        topics.append("outstanding balance query")

    if any(kw in text_lower for kw in ["salary", "income", "job", "business"]):
        topics.append("financial hardship mention")

    if any(kw in text_lower for kw in ["interest", "rate"]):
        topics.append("interest rate inquiry")

    # Build summary
    topic_text = ", ".join(topics) if topics else "general loan query"
    sentiment_text = {
        "Positive": "Customer appeared cooperative and satisfied.",
        "Negative": "Customer expressed distress or frustration.",
        "Neutral":  "Customer tone was neutral and informational."
    }.get(tonality, "")

    summary = (
        f"{customer_name} contacted the bank via {interaction_type} regarding {topic_text}. "
        f"{sentiment_text}"
    )

    return summary


# ─────────────────────────────────────────────
# Analyze & Store Interaction
# ─────────────────────────────────────────────

def analyze_and_store_interaction(
    db: Session,
    customer_id: str,
    interaction_type: str,
    conversation_text: str,
    customer_name: str = "Customer"
) -> dict:
    """
    Full pipeline:
      1. Calculate sentiment score
      2. Classify tonality
      3. Generate interaction summary
      4. Store in SQL (InteractionHistory)
      5. Store summary in Chroma Vector DB

    Returns:
        dict with sentiment_score, tonality_score, interaction_summary, interaction_id
    """
    # ── Step 1 & 2: Sentiment & Tonality ──────────────────────────
    sentiment_score = calculate_sentiment_score(conversation_text)
    tonality        = classify_tonality(sentiment_score)

    # ── Step 3: Summary ───────────────────────────────────────────
    summary = generate_interaction_summary(
        conversation_text = conversation_text,
        interaction_type  = interaction_type,
        tonality          = tonality,
        customer_name     = customer_name
    )

    # ── Step 4: Store in SQL ──────────────────────────────────────
    interaction = InteractionHistory(
        customer_id         = customer_id,
        interaction_type    = interaction_type,
        interaction_time    = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        conversation_text   = conversation_text,
        sentiment_score     = sentiment_score,
        tonality_score      = tonality,
        interaction_summary = summary
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # ── Step 5: Store in Chroma Vector DB ─────────────────────────
    try:
        from backend.vector.chroma_store import store_memory
        store_memory(
            customer_id = customer_id,
            summary     = summary,
            metadata    = {
                "interaction_id":   interaction.interaction_id,
                "interaction_type": interaction_type,
                "sentiment_score":  str(sentiment_score),
                "tonality":         tonality,
                "timestamp":        interaction.interaction_time,
            }
        )
    except Exception as e:
        print(f"[SentimentAgent] Chroma store failed (non-critical): {e}")

    return {
        "interaction_id":      interaction.interaction_id,
        "sentiment_score":     sentiment_score,
        "tonality_score":      tonality,
        "interaction_summary": summary,
    }


# ─────────────────────────────────────────────
# Aggregate Sentiment (across interactions)
# ─────────────────────────────────────────────

def aggregate_sentiment(interactions: list[dict]) -> dict:
    """
    Aggregate sentiment scores across multiple interactions.

    Args:
        interactions: List of dicts with sentiment_score and tonality_score

    Returns:
        dict with:
            - average_sentiment (float)
            - dominant_tonality (str)
            - sentiment_trend (str): "Improving" | "Stable" | "Deteriorating"
    """
    if not interactions:
        return {
            "average_sentiment": 0.0,
            "dominant_tonality": "Neutral",
            "sentiment_trend":   "Stable"
        }

    scores   = [i.get("sentiment_score", 0.0) for i in interactions]
    avg      = round(sum(scores) / len(scores), 2)
    dominant = classify_tonality(avg)

    # Trend: compare first half vs second half
    mid    = len(scores) // 2
    first  = sum(scores[:mid]) / max(len(scores[:mid]), 1)
    second = sum(scores[mid:]) / max(len(scores[mid:]), 1)

    if second > first + 0.1:
        trend = "Improving"
    elif second < first - 0.1:
        trend = "Deteriorating"
    else:
        trend = "Stable"

    return {
        "average_sentiment": avg,
        "dominant_tonality": dominant,
        "sentiment_trend":   trend
    }


# ─────────────────────────────────────────────
# LangGraph-Compatible Node
# ─────────────────────────────────────────────

def run_sentiment_agent(state: dict) -> dict:
    """
    LangGraph-compatible agent node.

    Expects state keys:
        - interactions (list[dict])  ← from context_memory_agent

    Adds to state:
        - sentiment_summary (dict)
            - average_sentiment (float)
            - dominant_tonality (str)
            - sentiment_trend (str)
    """
    interactions     = state.get("interactions", [])
    sentiment_summary = aggregate_sentiment(interactions)

    state.update({
        "sentiment_summary": sentiment_summary
    })

    return state