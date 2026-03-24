"""
LLM Reasoning Agent

Responsibilities:
  - Generate explainable recovery recommendations (narrative)
  - Generate customer relationship assessment text
  - Summarize borrower conversations
  - Answer customer AI assistant queries with full context
  - Uses Llama-3 via Ollama for local inference

Falls back to rule-based responses if Ollama is unavailable.
"""

import httpx
import json


# ─────────────────────────────────────────────
# Ollama Configuration
# ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1:8b"
OLLAMA_TIMEOUT  = 120  # seconds


# ─────────────────────────────────────────────
# Ollama Availability Check
# ─────────────────────────────────────────────

def is_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────────
# Core LLM Call
# ─────────────────────────────────────────────

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """
    Send a prompt to Ollama Llama-3 and return the response text.

    Falls back to rule-based response if Ollama is unavailable.
    """
    if not is_ollama_available():
        return None  # Signal to use fallback

    try:
        payload = {
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 512,
            }
        }

        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json    = payload,
            timeout = OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except Exception as e:
        print(f"[LLMReasoningAgent] Ollama call failed: {e}")
        return None


# ─────────────────────────────────────────────
# Build Context String for Prompts
# ─────────────────────────────────────────────

def build_context_string(context: dict, include_interactions: bool = True) -> str:
    """
    Convert the context dict into a readable string for LLM prompts.
    """
    profile  = context.get("customer_profile", {})
    loans    = context.get("loans", [])
    payments = context.get("payment_history", [])
    memories = context.get("vector_memories", [])
    interactions = context.get("interactions", [])

    lines = []

    # Customer
    if profile:
        lines.append(f"Customer: {profile.get('customer_name', 'N/A')}")
        lines.append(f"Credit Score: {profile.get('credit_score', 'N/A')}")
        lines.append(f"Monthly Income: ₹{profile.get('monthly_income', 0):,.0f}")
        lines.append(f"Preferred Channel: {profile.get('preferred_channel', 'N/A')}")

    # Loans
    if loans:
        loan = loans[0]
        lines.append(f"\nLoan ID: {loan.get('loan_id')}")
        lines.append(f"Loan Type: {loan.get('loan_type')}")
        lines.append(f"Outstanding Balance: ₹{loan.get('outstanding_balance', 0):,.0f}")
        lines.append(f"EMI Amount: ₹{loan.get('emi_amount', 0):,.0f}")
        lines.append(f"Days Past Due: {loan.get('days_past_due', 0)}")
        lines.append(f"Risk Segment: {loan.get('risk_segment', 'N/A')}")

    # Recent payments
    if payments:
        lines.append(f"\nRecent Payments (last {len(payments)}):")
        for p in payments[:3]:
            lines.append(f"  - {p.get('payment_date')}: ₹{p.get('payment_amount', 0):,.0f} via {p.get('payment_method')}")

    # Interaction summaries — only include if explicitly requested
    if include_interactions and interactions:
        lines.append("\nRecent Interactions:")
        for i in interactions[:3]:
            lines.append(f"  - [{i.get('interaction_type')}] {i.get('interaction_summary', '')}")

    # Vector memories — only include if explicitly requested
    if include_interactions and memories:
        lines.append("\nSemantic Memory:")
        for m in memories:
            lines.append(f"  - {m}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 1. Generate Recovery Recommendation (Narrative)
# ─────────────────────────────────────────────

def generate_recovery_recommendation(
    context: dict,
    analytics: dict
) -> str:
    """
    Generate an explainable recovery recommendation narrative using LLM.
    Falls back to rule-based text if Ollama is unavailable.

    Args:
        context:   Full customer context dict
        analytics: Output from collections_intelligence_agent

    Returns:
        Narrative recommendation string
    """
    strategy      = analytics.get("recovery_strategy", {})
    risk_segment  = analytics.get("risk_segment", "Medium")
    delinquency   = analytics.get("delinquency_score", 0)
    self_cure     = analytics.get("self_cure_probability", 0.5)
    dpd           = analytics.get("days_past_due", 0)

    context_str = build_context_string(context)

    system_prompt = (
        "You are an expert collections intelligence analyst at a bank. "
        "Your role is to provide clear, empathetic, and actionable recovery recommendations "
        "for bank officers. Be concise (3-4 sentences). Do not use bullet points. "
        "Focus on the borrower situation and recommended action."
    )

    prompt = f"""
Based on the following borrower profile and analytics, generate an explainable recovery recommendation.

{context_str}

Analytics:
- Risk Segment: {risk_segment}
- Delinquency Score: {delinquency}/100
- Self Cure Probability: {self_cure * 100:.0f}%
- Days Past Due: {dpd}
- Recommended Strategy: {strategy.get('strategy', 'N/A')}
- Recommended Action: {strategy.get('action', 'N/A')}

Write a clear 3-4 sentence recovery recommendation for the bank officer.
"""

    llm_response = call_ollama(prompt, system_prompt)

    if llm_response:
        return llm_response

    # ── Fallback: Rule-based narrative ────────────────────────────
    return (
        f"Based on the borrower's current profile, the recommended strategy is "
        f"'{strategy.get('strategy', 'Standard Follow-Up')}'. "
        f"The borrower has a delinquency score of {delinquency}/100 with "
        f"a self-cure probability of {self_cure * 100:.0f}%. "
        f"Recommended action: {strategy.get('action', 'Send payment reminder and provide repayment options.')} "
        f"Priority level is {strategy.get('priority', 'Medium')}."
    )


# ─────────────────────────────────────────────
# 2. Generate Customer Relationship Assessment
# ─────────────────────────────────────────────

def generate_relationship_assessment(
    customer_name: str,
    loans: list,
    payment_history: list,
    interactions: list
) -> str:
    """
    Generate a customer-friendly relationship assessment narrative.
    Shown to the customer in the Customer Portal.
    Falls back to rule-based text if Ollama unavailable.
    """
    if not loans:
        return (
            f"Welcome, {customer_name}. Your account is in good standing. "
            "Please contact us if you need any assistance with your loans."
        )

    loan        = loans[0]
    dpd         = loan.get("days_past_due", 0)
    emi_due     = loan.get("emi_due_date", "N/A")
    risk        = loan.get("risk_segment", "Low")
    total_paid  = len([p for p in payment_history if p.get("payment_amount", 0) > 0])

    system_prompt = (
        "You are a helpful and empathetic bank assistant. "
        "Write a short, supportive, customer-friendly relationship assessment (3-4 sentences). "
        "Do not use negative or alarming language. Be encouraging and helpful."
    )

    prompt = f"""
Write a personalized relationship assessment for the customer to display in their portal.

Customer Name: {customer_name}
Days Past Due: {dpd}
Next EMI Due Date: {emi_due}
Risk Segment: {risk}
Total Payments Made: {total_paid}
Recent Interactions: {len(interactions)}

Write a warm, supportive 3-4 sentence assessment.
"""

    llm_response = call_ollama(prompt, system_prompt)

    if llm_response:
        return llm_response

    # ── Fallback ──────────────────────────────────────────────────
    if dpd == 0:
        return (
            f"You have maintained an excellent repayment pattern with the bank. "
            f"Your next EMI is due on {emi_due}. "
            f"Thank you for your consistent and timely payments. "
            f"We value your continued trust in us."
        )
    elif dpd < 15:
        return (
            f"You have maintained a generally stable repayment pattern with the bank. "
            f"There have been a few short-term delays recently, but your overall repayment behavior remains positive. "
            f"Your next EMI is due on {emi_due}. "
            f"Based on your recent activity, you may receive reminders or support options if needed."
        )
    else:
        return (
            f"We have noticed some recent delays in your repayment schedule. "
            f"Your next EMI was due on {emi_due}. "
            f"We encourage you to contact the bank to discuss available support options "
            f"such as grace period or loan restructuring. We are here to help."
        )


# ─────────────────────────────────────────────
# 3. Answer Customer Query (AI Assistant)
# ─────────────────────────────────────────────

def answer_customer_query(
    user_message: str,
    context: dict,
    chat_history: list,
    is_officer: bool = False
) -> str:
    """
    Answer a customer's (or officer's) query using LLM with full context.
    Used by the Customer AI Assistant chat interface and Officer Loan Chat.

    Args:
        user_message: Current message
        context:      Full customer context dict
        chat_history: List of {role, message_text} dicts
        is_officer:   If True, respond as if addressing a bank officer (third-person customer refs)

    Returns:
        AI assistant response string
    """
    # Build conversation history string (only current session messages)
    history_lines = []
    for msg in chat_history[-6:]:  # Last 6 messages for context window
        role = "Customer" if msg.get("role") == "user" else "Assistant"
        history_lines.append(f"{role}: {msg.get('message_text', '')}")
    history_str = "\n".join(history_lines)

    profile = context.get("customer_profile", {})
    customer_name = profile.get("customer_name", "the customer")

    # If this is a new session (no prior messages), omit old interaction/vector history
    # to prevent the LLM from "recalling" content from previous sessions
    is_new_session = len(chat_history) == 0
    context_str = build_context_string(context, include_interactions=not is_new_session)

    if is_officer:
        system_prompt = (
            "You are an AI collections intelligence assistant for a BANK OFFICER. "
            "You are helping the officer analyze and manage a specific customer's loan account. "
            "Always refer to the customer in the THIRD PERSON (e.g., 'The customer', "
            f"'{customer_name}', 'they'). "
            "NEVER address the customer directly. NEVER say 'Hello' to the customer. "
            "Provide factual, analytical, and actionable information for the officer. "
            "Be concise (2-4 sentences). Use ₹ for Indian Rupee amounts. "
            "Focus on collections strategy, risk, payment behavior, and loan status."
        )

        prompt = f"""
Customer Account Context (for officer review):
{context_str}

Recent Conversation:
{history_str if history_str else "(No prior messages in this session)"}

Officer Query: {user_message}

Respond as a bank collections AI assistant addressing the OFFICER. Refer to the customer in third person.
"""
    else:
        system_prompt = (
            "You are a concise AI assistant for a bank's loan collections platform. "
            "Rules you MUST follow:\n"
            "1. Give SHORT, DIRECT answers — 1 to 2 sentences maximum.\n"
            "2. NEVER greet the customer by name (no 'Hello Rahul!' etc.) except on the very first message of a session.\n"
            "3. NEVER say things like 'as we discussed', 'you already know', 'we've discussed previously'.\n"
            "4. NEVER add unsolicited suggestions (e.g., 'Would you like to discuss a restructuring plan?') unless the customer asks.\n"
            "5. Answer ONLY the question asked — nothing more.\n"
            "6. Use ₹ for Indian Rupee amounts.\n"
            "7. Answer ONLY from the customer profile and loan context provided below.\n"
            "8. Do NOT fabricate or assume any information not present in the context."
        )

        is_first_message = len(chat_history) == 0
        greeting_note = (
            "This is the customer's first message — you may greet them briefly by first name."
            if is_first_message
            else "This is NOT the first message — do NOT greet or address by name."
        )

        prompt = f"""
Customer Profile & Loan Context:
{context_str}

Current Session Conversation:
{history_str if history_str else "(No prior messages)"}

Note: {greeting_note}

Customer asks: {user_message}

Answer in 1-2 sentences only. Be direct and factual.
"""

    llm_response = call_ollama(prompt, system_prompt)

    if llm_response:
        return llm_response

    # ── Fallback: Rule-based responses ────────────────────────────
    msg_lower = user_message.lower()
    loans     = context.get("loans", [])

    if any(kw in msg_lower for kw in ["loan id", "loan number", "my loan", "which loan", "give my loan", "what is my loan", "tell me my loan", "loan detail"]):
        if loans:
            loan_lines = "\n".join(
                f"• {l.get('loan_id')} ({l.get('loan_type')}) — ₹{l.get('outstanding_balance', 0):,.0f} outstanding"
                for l in loans
            )
            return f"Your active loans:\n{loan_lines}"
        return "You currently have no active loans on file."

    if any(kw in msg_lower for kw in ["emi", "payment", "due", "next"]):
        if loans:
            loan = loans[0]
            return (
                f"{loan.get('loan_id')} EMI: ₹{loan.get('emi_amount', 0):,.0f} due {loan.get('emi_due_date', 'N/A')}. "
                f"Outstanding: ₹{loan.get('outstanding_balance', 0):,.0f}."
            )

    if any(kw in msg_lower for kw in ["grace", "extension", "delay"]):
        if loans:
            dpd = loans[0].get("days_past_due", 0)
            if dpd < 30:
                return "You may be eligible for a grace period of up to 7 days. Submit a request from 'Your Loans'."
            return "Your overdue period may affect grace eligibility. Please contact the bank to discuss options."

    if any(kw in msg_lower for kw in ["restructur", "restructure"]):
        return "Loan restructuring is available — submit a request from 'Your Loans' and an officer will review within 2 business days."

    if any(kw in msg_lower for kw in ["balance", "outstanding"]):
        if loans:
            loan = loans[0]
            return f"Outstanding balance for {loan.get('loan_id')}: ₹{loan.get('outstanding_balance', 0):,.0f}."

    if any(kw in msg_lower for kw in ["hello", "hi", "hey"]):
        profile = context.get("customer_profile", {})
        first_name = profile.get("customer_name", "").split()[0] if profile.get("customer_name") else ""
        return (
            f"Hello{', ' + first_name if first_name else ''}! "
            "What would you like to know about your loan today?"
        )

    # Generic fallback
    if loans:
        loan = loans[0]
        return (
            f"{loan.get('loan_id')} ({loan.get('loan_type')}): "
            f"₹{loan.get('outstanding_balance', 0):,.0f} outstanding, "
            f"EMI ₹{loan.get('emi_amount', 0):,.0f} due {loan.get('emi_due_date', 'N/A')}."
        )

    return "How can I help you? Ask me about your loan, EMI, balance, or payment history."


# ─────────────────────────────────────────────
# 4. Summarize Interaction (for Vector Storage)
# ─────────────────────────────────────────────

def summarize_interaction(
    conversation_text: str,
    customer_name: str = "Customer"
) -> str:
    """
    Generate a concise summary of an interaction for vector storage.
    """
    system_prompt = (
        "You are a bank collections analyst. "
        "Summarize the following customer interaction in 1-2 sentences. "
        "Be factual and concise."
    )

    prompt = f"""
Summarize this customer interaction in 1-2 sentences:

Customer: {customer_name}
Interaction: {conversation_text}
"""

    llm_response = call_ollama(prompt, system_prompt)
    if llm_response:
        return llm_response

    # Fallback: return truncated text
    return conversation_text[:200] + "..." if len(conversation_text) > 200 else conversation_text


# ─────────────────────────────────────────────
# LangGraph-Compatible Node
# ─────────────────────────────────────────────

def run_llm_reasoning_agent(state: dict) -> dict:
    """
    LangGraph-compatible agent node.

    Expects state keys:
        - context (dict)          ← from context_memory_agent
        - analytics (dict)        ← from collections_intelligence_agent
        - user_query (str)        ← current user message
        - recent_messages (list)  ← chat history

    Adds to state:
        - llm_recommendation (str)
        - llm_response (str)       ← for chat assistant
    """
    context          = state.get("context", {})
    user_query       = state.get("user_query", "")
    recent_messages  = state.get("recent_messages", [])

    # Build analytics dict from state
    analytics = {
        "recovery_strategy":     state.get("recovery_strategy", {}),
        "risk_segment":          state.get("risk_segment", "Low"),
        "delinquency_score":     state.get("delinquency_score", 0),
        "self_cure_probability": state.get("self_cure_probability", 0.5),
        "days_past_due":         state.get("days_past_due", 0),
    }

    # Generate recovery recommendation narrative
    llm_recommendation = generate_recovery_recommendation(context, analytics)

    # Generate chat response if user query provided
    llm_response = ""
    if user_query:
        is_officer = state.get("is_officer", False)
        llm_response = answer_customer_query(
            user_message = user_query,
            context      = context,
            chat_history = recent_messages,
            is_officer   = is_officer,
        )

    state.update({
        "llm_recommendation": llm_recommendation,
        "llm_response":       llm_response,
    })

    return state