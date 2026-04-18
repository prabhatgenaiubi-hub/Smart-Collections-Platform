"""
Self-Cure Bot Agent  (Feature 3)

A stateless, multilingual guided conversation agent that helps customers
self-serve their repayment options without needing an officer.

Conversation Flow (stage machine):
    greeting
        ↓
    check_outstanding      ← shows DPD, balance, EMI
        ↓
    suggest_options        ← grace / restructure / pay-now / help
        ↓  (based on customer choice)
        ├── grace_request  ← confirms + triggers GraceRequest
        ├── restructure_request ← confirms + triggers RestructureRequest
        ├── pay_intent     ← records payment intent interaction
        └── escalate       ← flag for officer follow-up
        ↓
    closing

At each stage the agent returns:
    {
        reply        : str               ← bot message (already in detected language if LLM)
        stage        : str               ← new stage for client to send back next turn
        quick_replies: list[str]         ← pre-built button options (empty list = free text)
        escalate     : bool              ← True → front-end shows "Connecting to officer…"
        language     : str               ← detected language name
        saved        : bool              ← True when an action was persisted to DB
    }

Language detection reuses the same Unicode-marker map from copilot_agent.
LLM (Ollama) is used for natural reply phrasing; falls back to hardcoded
multilingual templates if Ollama is unavailable.
"""

import json
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.models import (
    Customer, Loan, GraceRequest, RestructureRequest, InteractionHistory
)
from backend.db.database import gen_uuid
from backend.agents.sentiment_agent import calculate_sentiment_score, classify_tonality
from backend.agents.llm_reasoning_agent import call_ollama


# ─────────────────────────────────────────────
# Language Detection  (same as copilot_agent)
# ─────────────────────────────────────────────

_LANG_MARKERS = {
    "Hindi":     ("\u0900", "\u097F"),
    "Tamil":     ("\u0B80", "\u0BFF"),
    "Telugu":    ("\u0C00", "\u0C7F"),
    "Kannada":   ("\u0C80", "\u0CFF"),
    "Malayalam": ("\u0D00", "\u0D7F"),
    "Marathi":   ("\u0900", "\u097F"),   # same block as Hindi — detected together
    "Gujarati":  ("\u0A80", "\u0AFF"),
    "Bengali":   ("\u0980", "\u09FF"),
}

def detect_language(text: str) -> str:
    if not text:
        return "English"
    counts = {}
    for lang, (lo, hi) in _LANG_MARKERS.items():
        counts[lang] = sum(1 for ch in text if lo <= ch <= hi)
    best = max(counts, key=counts.get)
    if counts[best] >= 3:
        return best
    return "English"


# ─────────────────────────────────────────────
# Multilingual Static Templates
# (used when Ollama is unavailable)
# ─────────────────────────────────────────────

_TEMPLATES = {
    "greeting": {
        "English":   "Hello! 👋 I'm your Self-Cure Assistant. I can help you check your loan status, request a grace period, or explore repayment options. How can I help you today?",
        "Hindi":     "नमस्ते! 👋 मैं आपका सेल्फ-क्योर असिस्टेंट हूँ। मैं आपके लोन की स्थिति, ग्रेस पीरियड, या पुनर्भुगतान विकल्पों में मदद कर सकता हूँ।",
        "Tamil":     "வணக்கம்! 👋 நான் உங்கள் செல்ஃப்-க்யூர் உதவியாளர். கடன் நிலை, கிரேஸ் பீரியட் அல்லது மீண்டும் கட்டண விருப்பங்களில் உதவ முடியும்.",
        "Telugu":    "నమస్కారం! 👋 నేను మీ సెల్ఫ్-క్యూర్ అసిస్టెంట్. రుణ స్థితి, గ్రేస్ పీరియడ్ లేదా చెల్లింపు ఎంపికలలో సహాయం చేయగలను.",
        "Kannada":   "ನಮಸ್ಕಾರ! 👋 ನಾನು ನಿಮ್ಮ ಸ್ವಯಂ-ಚಿಕಿತ್ಸೆ ಸಹಾಯಕ. ಸಾಲದ ಸ್ಥಿತಿ, ಗ್ರೇಸ್ ಪೀರಿಯಡ್ ಅಥವಾ ಮರುಪಾವತಿ ಆಯ್ಕೆಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ.",
        "Malayalam": "ഹലോ! 👋 ഞാൻ നിങ്ങളുടെ സ്വയം-ചികിത്സ സഹായി. വായ്പ നില, ഗ്രേസ് പീരിയഡ് അല്ലെങ്കിൽ തിരിച്ചടവ് ഓപ്ഷനുകളിൽ സഹായിക്കാം.",
        "Gujarati":  "હેલો! 👋 હું તમારો સ્વ-ઉપચાર સહાયક છું. લોન સ્થિતિ, ગ્રેસ પીરિયડ અથવા ચુકવણી વિકલ્પોમાં મદદ કરી શકું છું.",
        "Bengali":   "হ্যালো! 👋 আমি আপনার সেলফ-কিউর সহকারী। ঋণের অবস্থা, গ্রেস পিরিয়ড বা পুনঃপরিশোধের বিকল্পে সাহায্য করতে পারি।",
    },
    "outstanding": {
        "English":   "📋 Here's your current loan summary:\n\n{summary}\n\nWhat would you like to do?",
        "Hindi":     "📋 आपके लोन की वर्तमान स्थिति:\n\n{summary}\n\nआप क्या करना चाहेंगे?",
        "Tamil":     "📋 உங்கள் தற்போதைய கடன் சுருக்கம்:\n\n{summary}\n\nநீங்கள் என்ன செய்ய விரும்புகிறீர்கள்?",
        "Telugu":    "📋 మీ ప్రస్తుత రుణ సారాంశం:\n\n{summary}\n\nమీరు ఏమి చేయాలనుకుంటున్నారు?",
        "Kannada":   "📋 ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸಾಲದ ಸಾರಾಂಶ:\n\n{summary}\n\nನೀವು ಏನು ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?",
        "Malayalam": "📋 നിങ്ങളുടെ നിലവിലെ വായ്പ സംഗ്രഹം:\n\n{summary}\n\nനിങ്ങൾ എന്ത് ചെയ്യാൻ ആഗ്രഹിക്കുന്നു?",
        "Gujarati":  "📋 તમારો વર્તમાન લોન સારાંશ:\n\n{summary}\n\nતમે શું કરવા ઇચ્છો છો?",
        "Bengali":   "📋 আপনার বর্তমান ঋণের সারসংক্ষেপ:\n\n{summary}\n\nআপনি কী করতে চান?",
    },
    "grace_confirm": {
        "English":   "✅ Your grace period request has been submitted successfully. An officer will review it within 1–2 business days and you'll be notified. Is there anything else I can help with?",
        "Hindi":     "✅ आपका ग्रेस पीरियड अनुरोध सफलतापूर्वक जमा हो गया है। एक अधिकारी 1-2 कार्यदिवसों में समीक्षा करेगा। क्या और कुछ सहायता चाहिए?",
        "Tamil":     "✅ உங்கள் கிரேஸ் பீரியட் கோரிக்கை வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது. 1-2 நாட்களில் அதிகாரி மதிப்பீடு செய்வார். வேறு ஏதாவது உதவி வேண்டுமா?",
        "Telugu":    "✅ మీ గ్రేస్ పీరియడ్ అభ్యర్థన విజయవంతంగా సమర్పించబడింది. 1-2 రోజులలో అధికారి సమీక్షిస్తారు. మరింత సహాయం కావాలా?",
        "Kannada":   "✅ ನಿಮ್ಮ ಗ್ರೇಸ್ ಪೀರಿಯಡ್ ವಿನಂತಿ ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ. 1-2 ದಿನಗಳಲ್ಲಿ ಅಧಿಕಾರಿ ಪರಿಶೀಲಿಸುತ್ತಾರೆ. ಇನ್ನೇನಾದರೂ ಸಹಾಯ ಬೇಕೇ?",
        "Malayalam": "✅ നിങ്ങളുടെ ഗ്രേസ് പീരിയഡ് അഭ്യർത്ഥന വിജയകരമായി സമർപ്പിച്ചു. 1-2 ദിവസത്തിനുള്ളിൽ ഒരു ഉദ്യോഗസ്ഥൻ പരിശോധിക്കും. മറ്റേതെങ്കിലും സഹായം വേണോ?",
        "Gujarati":  "✅ તમારી ગ્રેસ પીરિયડ વિનંતી સફળતાપૂર્વક સબમિટ થઈ. 1-2 દિવસમાં અધિકારી સમીક્ષા કરશે. બીજી કોઈ મદદ જોઈએ?",
        "Bengali":   "✅ আপনার গ্রেস পিরিয়ড অনুরোধ সফলভাবে জমা হয়েছে। 1-2 কার্যদিবসে একজন কর্মকর্তা পর্যালোচনা করবেন। আর কোনো সাহায্য দরকার?",
    },
    "restructure_confirm": {
        "English":   "✅ Your loan restructure request has been submitted. An officer will contact you within 2 business days to discuss new EMI options. Is there anything else?",
        "Hindi":     "✅ आपका लोन पुनर्गठन अनुरोध जमा हो गया। एक अधिकारी 2 कार्यदिवसों में आपसे संपर्क करेगा। क्या और कुछ चाहिए?",
        "Tamil":     "✅ உங்கள் கடன் மறுசீரமைப்பு கோரிக்கை சமர்ப்பிக்கப்பட்டது. 2 நாட்களில் அதிகாரி தொடர்பு கொள்வார். வேறு ஏதாவது?",
        "Telugu":    "✅ మీ రుణ పునర్నిర్మాణ అభ్యర్థన సమర్పించబడింది. 2 రోజులలో అధికారి సంప్రదిస్తారు. మరింత సహాయం?",
        "Kannada":   "✅ ನಿಮ್ಮ ಸಾಲ ಪುನರ್ರಚನೆ ವಿನಂತಿ ಸಲ್ಲಿಸಲಾಗಿದೆ. 2 ದಿನಗಳಲ್ಲಿ ಅಧಿಕಾರಿ ಸಂಪರ್ಕಿಸುತ್ತಾರೆ. ಬೇರೇನಾದರೂ ಸಹಾಯ?",
        "Malayalam": "✅ നിങ്ങളുടെ ലോൺ റീസ്ട്രക്ചർ അഭ്യർത്ഥന സമർപ്പിച്ചു. 2 ദിവസത്തിനുള്ളിൽ ഉദ്യോഗസ്ഥൻ ബന്ധപ്പെടും. മറ്റൊന്ന്?",
        "Gujarati":  "✅ તમારી ઋણ પુનર્ગઠન વિનંતી સ\u0aadm\u0abft \u0aa5઎. 2 \u0aa6\u0abf\u0ab5\u0ab8\u0aae\u0abe\u0a82 \u0a85\u0aa7\u0abf\u0a95\u0abe\u0ab0\u0ac0 \u0ab8\u0a82\u0aaa\u0ab0\u0acd\u0a95 \u0a95\u0ab0\u0ab6\u0ac7. \u0aac\u0ac0\u0a9c\u0ac1\u0a82 \u0a95\u0a82\u0a87 \u0a9c\u0acb\u0a88\u0a8f?",
        "Bengali":   "✅ আপনার ঋণ পুনর্গঠন অনুরোধ জমা হয়েছে। 2 কার্যদিবসে একজন কর্মকর্তা যোগাযোগ করবেন। আর কিছু?",
    },
    "pay_intent": {
        "English":   "💳 Great! Your intention to make a payment has been recorded. You can proceed through your bank's official payment portal. Would you also like to know about EMI options or need further help?",
        "Hindi":     "💳 बढ़िया! आपका भुगतान इरादा दर्ज कर लिया गया है। आप अपने बैंक के आधिकारिक पोर्टल से भुगतान कर सकते हैं। क्या EMI विकल्पों के बारे में जानना चाहेंगे?",
        "Tamil":     "💳 சிறப்பு! உங்கள் கட்டண எண்ணம் பதிவு செய்யப்பட்டது. வங்கி போர்ட்டல் மூலம் கட்டணம் செலுத்தலாம். EMI விருப்பங்கள் தேவையா?",
        "Telugu":    "💳 చాలా బాగుంది! మీ చెల్లింపు ఉద్దేశం నమోదు చేయబడింది. బ్యాంక్ పోర్టల్ ద్వారా చెల్లించవచ్చు. EMI ఎంపికలు కావాలా?",
        "Kannada":   "💳 ಉತ್ತಮ! ನಿಮ್ಮ ಪಾವತಿ ಉದ್ದೇಶ ದಾಖಲಾಗಿದೆ. ಬ್ಯಾಂಕ್ ಪೋರ್ಟಲ್ ಮೂಲಕ ಪಾವತಿ ಮಾಡಬಹುದು. EMI ಆಯ್ಕೆಗಳು ಬೇಕೇ?",
        "Malayalam": "💳 വളരെ നല്ലത്! നിങ്ങളുടെ പേയ്‌മെന്റ് ഉദ്ദേശം രേഖപ്പെടുത്തി. ബാങ്ക് പോർട്ടൽ വഴി പണം അടയ്ക്കാം. EMI ഓപ്ഷനുകൾ വേണോ?",
        "Gujarati":  "💳 સરસ! તમારો ચુકવણી ઇરાદો નોંધ\u0acdO \u0aa5uo. \u0aac\u0ac7\u0a82\u0a95 \u0aaa\u0acb\u0ab0\u0acd\u0a9f\u0ab2 \u0aa6\u0acd\u0ab5\u0abe\u0ab0\u0abe \u0a9a\u0ac1\u0a95\u0ab5\u0aa3\u0ac0 \u0a95\u0ab0\u0ac0 \u0ab6\u0a95\u0abe\u0a8f. EMI \u0ab5\u0abf\u0a95\u0ab2\u0acd\u0aaa\u0acb \u0a9c\u0acb\u0a88\u0a8f?",
        "Bengali":   "💳 চমৎকার! আপনার পেমেন্টের ইচ্ছা নথিভুক্ত হয়েছে। ব্যাংক পোর্টালের মাধ্যমে পেমেন্ট করুন। EMI বিকল্প জানতে চান?",
    },
    "escalate": {
        "English":   "🔄 I understand you need more help than I can provide right now. I'm flagging your account for an officer follow-up. Someone from our team will contact you within 24 hours. Thank you for your patience. 🙏",
        "Hindi":     "🔄 मैं समझता हूँ कि आपको अधिक सहायता की जरूरत है। मैं आपके खाते को अधिकारी फॉलो-अप के लिए चिह्नित कर रहा हूँ। हमारी टीम 24 घंटों में संपर्क करेगी। 🙏",
        "Tamil":     "🔄 உங்களுக்கு அதிக உதவி தேவை என்று புரிகிறது. அதிகாரி தொடர்புக்காக உங்கள் கணக்கை குறிக்கிறேன். 24 மணி நேரத்தில் தொடர்பு கொள்வோம். 🙏",
        "Telugu":    "🔄 మీకు ఎక్కువ సహాయం అవసరమని అర్థమైంది. అధికారి ఫాలో-అప్ కోసం మీ ఖాతాను గుర్తించాను. 24 గంటలలో సంప్రదిస్తాం. 🙏",
        "Kannada":   "🔄 ನಿಮಗೆ ಹೆಚ್ಚಿನ ಸಹಾಯ ಬೇಕೆಂದು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ಅಧಿಕಾರಿ ಅನುಸರಣೆಗಾಗಿ ಖಾತೆ ಗುರುತಿಸಲಾಗಿದೆ. 24 ಗಂಟೆಗಳಲ್ಲಿ ಸಂಪರ್ಕಿಸಲಾಗುವುದು. 🙏",
        "Malayalam": "🔄 നിങ്ങൾക്ക് കൂടുതൽ സഹായം ആവശ്യമെന്ന് മനസ്സിലായി. ഒരു ഉദ്യോഗസ്ഥൻ ഫോളോ-അപ്പ് ചെയ്യും. 24 മണിക്കൂറിനുള്ളിൽ ബന്ധപ്പെടും. 🙏",
        "Gujarati":  "🔄 \u0aa4\u0aae\u0aa8\u0ac7 \u0ab5\u0aa7\u0ac1 \u0aae\u0aa6\u0aa6 \u0a9c\u0acb\u0a88\u0a8f \u0a9b\u0ac7 \u0aa4\u0ac7 \u0ab8\u0aae\u0a9c\u0abe\u0aaf\u0ac1\u0a82. \u0a85\u0aa7\u0abf\u0a95\u0abe\u0ab0\u0ac0 \u0aab\u0acb\u0ab2\u0acb-\u0a85\u0aaa \u0aae\u0abe\u0a9f\u0ac7 \u0aac\u0acd\u0ab2\u0ac7\u0a97 \u0a95\u0ab0\u0ac7\u0ab2. 24 \u0a95\u0ab2\u0abe\u0a95\u0aae\u0abe\u0a82 \u0ab8\u0a82\u0aaa\u0ab0\u0acd\u0a95 \u0a95\u0ab0\u0ab6\u0ac7. 🙏",
        "Bengali":   "🔄 আমি বুঝতে পারছি আপনার আরো সাহায্য দরকার। একজন কর্মকর্তা 24 ঘন্টার মধ্যে যোগাযোগ করবেন। 🙏",
    },
    "closing": {
        "English":   "😊 Is there anything else I can help you with today?",
        "Hindi":     "😊 क्या आज और कुछ सहायता चाहिए?",
        "Tamil":     "😊 இன்று வேறு ஏதாவது உதவி வேண்டுமா?",
        "Telugu":    "😊 ఇంకేమైనా సహాయం కావాలా?",
        "Kannada":   "😊 ಇಂದು ಬೇರೆ ಏನಾದರೂ ಸಹಾಯ ಬೇಕೇ?",
        "Malayalam": "😊 ഇന്ന് മറ്റൊന്ന് ആവശ്യമുണ്ടോ?",
        "Gujarati":  "😊 \u0a86\u0a9c\u0ac7 \u0aac\u0ac0\u0a9c\u0ac1\u0a82 \u0a95\u0a82\u0a87 \u0a9c\u0acb\u0a88\u0a8f?",
        "Bengali":   "😊 আজ আর কোনো সাহায্য দরকার?",
    },
    "no_loan": {
        "English":   "ℹ️ I couldn't find any active loans on your account. If you think this is an error, please contact the bank directly.",
        "Hindi":     "ℹ️ आपके खाते में कोई सक्रिय लोन नहीं मिला। यदि यह गलती लगे तो बैंक से सीधे संपर्क करें।",
        "Tamil":     "ℹ️ உங்கள் கணக்கில் எந்த கடனும் கிடைக்கவில்லை. தவறு என்று நினைத்தால் நேரடியாக வங்கியை தொடர்பு கொள்ளுங்கள்.",
        "Telugu":    "ℹ️ మీ ఖాతాలో సక్రియ రుణాలు కనుగొనబడలేదు. తప్పు అని భావిస్తే నేరుగా బ్యాంక్‌ని సంప్రదించండి.",
        "Kannada":   "ℹ️ ನಿಮ್ಮ ಖಾತೆಯಲ್ಲಿ ಯಾವುದೇ ಸಕ್ರಿಯ ಸಾಲ ಕಂಡುಬಂದಿಲ್ಲ. ತಪ್ಪು ಎನ್ನಿಸಿದರೆ ನೇರವಾಗಿ ಬ್ಯಾಂಕ್ ಸಂಪರ್ಕಿಸಿ.",
        "Malayalam": "ℹ️ നിങ്ങളുടെ അക്കൗണ്ടിൽ ഒരു സജീവ വായ്പയും കണ്ടെത്തിയില്ല. തെറ്റ് എന്ന് തോന്നിയാൽ ബാങ്കുമായി ബന്ധപ്പെടുക.",
        "Gujarati":  "ℹ️ \u0aa4\u0aae\u0abe\u0ab0\u0abe \u0a96\u0abe\u0aa4\u0abe\u0aae\u0abe\u0a82 \u0a95\u0acb\u0a88 \u0ab8\u0a95\u0acd\u0ab0\u0abf\u0aaf \u0ab2\u0acb\u0aa8 \u0aae\u0ab3\u0acd\u0aaf\u0ac1\u0a82 \u0aa8\u0aa5\u0ac0. \u0a95\u0ac1\u0aa6\u0ab0\u0aa4\u0ac0 \u0ab2\u0abe\u0a97\u0ac7 \u0aa4\u0acb \u0ac2\u0ab8\u0ac0\u0aa7\u0ac0 \u0aac\u0ac7\u0a82\u0a95\u0aa8\u0ac7 \u0ab8\u0a82\u0aaa\u0ab0\u0acd\u0a95 \u0a95\u0ab0\u0acb.",
        "Bengali":   "ℹ️ আপনার অ্যাকাউন্টে কোনো সক্রিয় ঋণ পাওয়া যায়নি। ভুল মনে হলে সরাসরি ব্যাংকের সাথে যোগাযোগ করুন।",
    },
}

def _t(key: str, language: str, **kwargs) -> str:
    """Get template in detected language (fall back to English)."""
    lang_map = _TEMPLATES.get(key, {})
    text = lang_map.get(language) or lang_map.get("English", "")
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


# ─────────────────────────────────────────────
# Quick-Reply Button Sets per stage
# ─────────────────────────────────────────────

_QUICK_REPLIES = {
    "greeting": ["📋 Check my loan status", "⏱ Request grace period", "🔄 Restructure loan", "💳 I want to pay now", "🆘 I need more help"],
    "suggest_options": ["⏱ Request grace period", "🔄 Restructure loan", "💳 I want to pay now", "🆘 Connect to officer"],
    "closing": ["📋 Check my loan status", "⏱ Request grace period", "🔄 Restructure loan", "💳 I want to pay now", "✅ I'm done, thank you"],
    "grace_confirm": ["📋 Check my loan status", "🔄 Restructure loan", "✅ I'm done, thank you"],
    "restructure_confirm": ["📋 Check my loan status", "⏱ Request grace period", "✅ I'm done, thank you"],
    "pay_intent": ["📋 Check my loan status", "⏱ Request grace period", "🔄 Restructure loan", "✅ I'm done, thank you"],
}


# ─────────────────────────────────────────────
# Loan Summary Helper
# ─────────────────────────────────────────────

def _loan_summary(loans: list) -> str:
    if not loans:
        return "No active loans found."
    lines = []
    for loan in loans[:3]:  # show up to 3 loans
        dpd     = loan.days_past_due
        dpd_str = f"🔴 {dpd} days overdue" if dpd > 0 else "✅ On time"
        lines.append(
            f"• {loan.loan_id} ({loan.loan_type})\n"
            f"  Outstanding: ₹{loan.outstanding_balance:,.0f} | EMI: ₹{loan.emi_amount:,.0f}\n"
            f"  Due date: {loan.emi_due_date} | {dpd_str}"
        )
    return "\n\n".join(lines)


# ─────────────────────────────────────────────
# LLM-Powered Natural Reply
# ─────────────────────────────────────────────

def _llm_reply(user_message: str, context_summary: str, language: str, stage: str) -> str | None:
    """
    Ask Ollama to rephrase/reply naturally in the detected language.
    Returns None if Ollama is unavailable.
    """
    lang_note = "" if language == "English" else f"IMPORTANT: Reply in {language} only."
    system = (
        "You are a helpful, empathetic bank self-cure assistant. "
        "Your job is to guide customers through repayment options. "
        "Be concise (2-3 sentences max). Be warm and non-judgmental. "
        "Never promise anything beyond what is stated. "
        f"{lang_note}"
    )
    prompt = (
        f"Customer loan context:\n{context_summary}\n\n"
        f"Current stage: {stage}\n"
        f"Customer message: {user_message}\n\n"
        "Respond naturally and helpfully."
    )
    return call_ollama(prompt, system)


# ─────────────────────────────────────────────
# Escalation Detector
# ─────────────────────────────────────────────

_ESCALATION_KEYWORDS = [
    "not able", "cannot pay", "lost job", "no money", "medical emergency",
    "family issue", "too much", "stressed", "depressed", "please help",
    "urgent", "can't afford", "not paying", "refuse", "legal", "court",
    "नहीं दे सकता", "पैसे नहीं", "नौकरी गई", "परेशान",
    "பணம் இல்லை", "சேலையில்லை",
]

def _should_escalate(message: str, sentiment_score: float) -> bool:
    msg_lower = message.lower()
    keyword_hit = any(kw in msg_lower for kw in _ESCALATION_KEYWORDS)
    return keyword_hit or sentiment_score < -0.5


# ─────────────────────────────────────────────
# Intent Router
# ─────────────────────────────────────────────

def _detect_intent(message: str) -> str:
    """Map a free-text or button message to an internal intent."""
    m = message.lower()
    if any(k in m for k in ["grace", "extension", "delay", "⏱", "more time"]):
        return "grace"
    if any(k in m for k in ["restructure", "restructuring", "emi reduce", "lower emi", "🔄"]):
        return "restructure"
    if any(k in m for k in ["pay", "payment", "💳", "pay now", "make payment"]):
        return "pay"
    if any(k in m for k in ["outstanding", "balance", "loan status", "how much", "📋", "check"]):
        return "outstanding"
    if any(k in m for k in ["officer", "agent", "human", "connect", "🆘", "help"]):
        return "escalate"
    if any(k in m for k in ["done", "thank", "bye", "goodbye", "✅"]):
        return "done"
    return "unknown"


# ─────────────────────────────────────────────
# Main Agent Entry Point
# ─────────────────────────────────────────────

def run_self_cure_agent(
    db:           Session,
    customer_id:  str,
    message:      str,
    stage:        str = "greeting",        # current stage sent by client
    language:     str = "auto",            # "auto" = detect from message
) -> dict:
    """
    Process one turn of the self-cure conversation.

    Args:
        db:           SQLAlchemy session
        customer_id:  logged-in customer ID
        message:      customer's text input
        stage:        current conversation stage (client tracks this)
        language:     detected language (or "auto")

    Returns dict:
        reply         : str  — bot's response text
        stage         : str  — next stage the client should send next turn
        quick_replies : list — pre-built button labels
        escalate      : bool — True if officer follow-up needed
        language      : str  — language name
        saved         : bool — True if DB was written this turn
    """

    # ── Detect language ───────────────────────────────────────────
    detected = detect_language(message)
    if language == "auto" or language == "English":
        language = detected if detected != "English" else "English"
    # Keep language sticky across turns (client sends it back each turn)

    # ── Load customer + loans ─────────────────────────────────────
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {
            "reply":         "Customer not found.",
            "stage":         "closing",
            "quick_replies": [],
            "escalate":      False,
            "language":      language,
            "saved":         False,
        }

    loans = (
        db.query(Loan)
        .filter(Loan.customer_id == customer_id)
        .order_by(Loan.days_past_due.desc())
        .all()
    )

    # ── Sentiment check for escalation ────────────────────────────
    try:
        sentiment_score = calculate_sentiment_score(message)
    except Exception:
        sentiment_score = 0.0

    # ── Stage: greeting ───────────────────────────────────────────
    if stage == "greeting":
        reply = _t("greeting", language)
        return {
            "reply":         reply,
            "stage":         "suggest_options",
            "quick_replies": _QUICK_REPLIES["greeting"],
            "escalate":      False,
            "language":      language,
            "saved":         False,
        }

    # ── Escalation check ──────────────────────────────────────────
    if _should_escalate(message, sentiment_score):
        _save_interaction(db, customer_id, message, sentiment_score,
                          "Self-Cure Bot: Customer flagged for officer escalation.")
        return {
            "reply":         _t("escalate", language),
            "stage":         "closing",
            "quick_replies": [],
            "escalate":      True,
            "language":      language,
            "saved":         True,
        }

    # ── Route by intent ───────────────────────────────────────────
    intent = _detect_intent(message)
    context_summary = _loan_summary(loans)

    # ─ Outstanding / check loan status ────────────────────────────
    if intent == "outstanding" or stage in ("suggest_options",) and intent == "unknown":
        if not loans:
            reply = _t("no_loan", language)
            return {"reply": reply, "stage": "closing", "quick_replies": _QUICK_REPLIES["closing"],
                    "escalate": False, "language": language, "saved": False}

        llm = _llm_reply(message, context_summary, language, "outstanding")
        summary_text = _loan_summary(loans)
        reply = llm if llm else _t("outstanding", language, summary=summary_text)
        return {
            "reply":         reply,
            "stage":         "suggest_options",
            "quick_replies": _QUICK_REPLIES["suggest_options"],
            "escalate":      False,
            "language":      language,
            "saved":         False,
        }

    # ─ Grace request ──────────────────────────────────────────────
    if intent == "grace":
        saved = False
        if loans:
            # Create grace request for most overdue loan
            primary_loan = loans[0]
            existing = db.query(GraceRequest).filter(
                GraceRequest.loan_id        == primary_loan.loan_id,
                GraceRequest.request_status == "Pending",
            ).first()
            if not existing:
                req = GraceRequest(
                    request_id    = gen_uuid(),
                    loan_id       = primary_loan.loan_id,
                    customer_id   = customer_id,
                    request_status= "Pending",
                    request_date  = datetime.now().strftime("%Y-%m-%d"),
                )
                db.add(req)
                _save_interaction(db, customer_id, message, sentiment_score,
                                  "Self-Cure Bot: Customer requested grace period via bot.")
                db.commit()
                saved = True
        llm = _llm_reply(message, context_summary, language, "grace_request")
        reply = llm if llm else _t("grace_confirm", language)
        return {
            "reply":         reply,
            "stage":         "closing",
            "quick_replies": _QUICK_REPLIES["grace_confirm"],
            "escalate":      False,
            "language":      language,
            "saved":         saved,
        }

    # ─ Restructure request ────────────────────────────────────────
    if intent == "restructure":
        saved = False
        if loans:
            primary_loan = loans[0]
            existing = db.query(RestructureRequest).filter(
                RestructureRequest.loan_id        == primary_loan.loan_id,
                RestructureRequest.request_status == "Pending",
            ).first()
            if not existing:
                req = RestructureRequest(
                    request_id    = gen_uuid(),
                    loan_id       = primary_loan.loan_id,
                    customer_id   = customer_id,
                    request_status= "Pending",
                    request_date  = datetime.now().strftime("%Y-%m-%d"),
                )
                db.add(req)
                _save_interaction(db, customer_id, message, sentiment_score,
                                  "Self-Cure Bot: Customer requested loan restructure via bot.")
                db.commit()
                saved = True
        llm = _llm_reply(message, context_summary, language, "restructure_request")
        reply = llm if llm else _t("restructure_confirm", language)
        return {
            "reply":         reply,
            "stage":         "closing",
            "quick_replies": _QUICK_REPLIES["restructure_confirm"],
            "escalate":      False,
            "language":      language,
            "saved":         saved,
        }

    # ─ Pay intent ─────────────────────────────────────────────────
    if intent == "pay":
        _save_interaction(db, customer_id, message, sentiment_score,
                          "Self-Cure Bot: Customer expressed payment intent via bot.")
        db.commit()
        llm = _llm_reply(message, context_summary, language, "pay_intent")
        reply = llm if llm else _t("pay_intent", language)
        return {
            "reply":         reply,
            "stage":         "closing",
            "quick_replies": _QUICK_REPLIES["pay_intent"],
            "escalate":      False,
            "language":      language,
            "saved":         True,
        }

    # ─ Done / closing ─────────────────────────────────────────────
    if intent == "done":
        return {
            "reply":         _t("closing", language),
            "stage":         "closing",
            "quick_replies": [],
            "escalate":      False,
            "language":      language,
            "saved":         False,
        }

    # ─ Explicit escalate ──────────────────────────────────────────
    if intent == "escalate":
        _save_interaction(db, customer_id, message, sentiment_score,
                          "Self-Cure Bot: Customer requested officer connection.")
        db.commit()
        return {
            "reply":         _t("escalate", language),
            "stage":         "closing",
            "quick_replies": [],
            "escalate":      True,
            "language":      language,
            "saved":         True,
        }

    # ─ Unknown / free-text — try LLM, fall back to re-prompt ──────
    llm = _llm_reply(message, context_summary, language, stage)
    if llm:
        return {
            "reply":         llm,
            "stage":         "suggest_options",
            "quick_replies": _QUICK_REPLIES["suggest_options"],
            "escalate":      False,
            "language":      language,
            "saved":         False,
        }

    # Hard fallback — show options again
    reply = _t("closing", language)
    return {
        "reply":         reply,
        "stage":         "suggest_options",
        "quick_replies": _QUICK_REPLIES["suggest_options"],
        "escalate":      False,
        "language":      language,
        "saved":         False,
    }


# ─────────────────────────────────────────────
# Helper: save interaction record
# ─────────────────────────────────────────────

def _save_interaction(
    db:              Session,
    customer_id:     str,
    conversation_text: str,
    sentiment_score: float,
    summary:         str,
) -> None:
    try:
        tonality = classify_tonality(sentiment_score)
    except Exception:
        tonality = "Neutral"

    interaction = InteractionHistory(
        interaction_id      = gen_uuid(),
        customer_id         = customer_id,
        interaction_type    = "Chat",
        interaction_time    = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        conversation_text   = conversation_text,
        sentiment_score     = sentiment_score,
        tonality_score      = tonality,
        interaction_summary = summary,
    )
    db.add(interaction)
