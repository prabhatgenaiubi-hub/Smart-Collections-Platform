import { useState, useRef, useEffect } from 'react';
import api from '../../api';

// ── Language display helper ────────────────────────────────────

const LANG_FLAGS = {
  English: '🌐', Hindi: '🇮🇳', Tamil: '🇮🇳', Telugu: '🇮🇳',
  Kannada: '🇮🇳', Malayalam: '🇮🇳', Marathi: '🇮🇳',
  Gujarati: '🇮🇳', Bengali: '🇮🇳',
};

function LangBadge({ lang }) {
  if (!lang || lang === 'auto') return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">
      {LANG_FLAGS[lang] ?? '🌐'} {lang}
    </span>
  );
}

// ── Message bubble ─────────────────────────────────────────────

function Bubble({ role, text, timestamp }) {
  const isBot = role === 'bot';
  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'} mb-3`}>
      {isBot && (
        <div className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center flex-shrink-0 mr-2 mt-1">
          🤖
        </div>
      )}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap shadow-sm ${
          isBot
            ? 'bg-white border border-gray-200 text-gray-800 rounded-tl-none'
            : 'bg-blue-600 text-white rounded-tr-none'
        }`}
      >
        {text}
        <div className={`text-[10px] mt-1 ${isBot ? 'text-gray-400' : 'text-blue-200'}`}>
          {timestamp}
        </div>
      </div>
    </div>
  );
}

// ── Quick-reply buttons ────────────────────────────────────────

function QuickReplies({ options, onSelect, disabled }) {
  if (!options || options.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-2 mb-1 px-2">
      {options.map((opt, i) => (
        <button
          key={i}
          disabled={disabled}
          onClick={() => onSelect(opt)}
          className="text-xs px-3 py-1.5 rounded-full border border-blue-300 text-blue-700 bg-blue-50 hover:bg-blue-100 hover:border-blue-400 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium"
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

// ── Escalation notice ──────────────────────────────────────────

function EscalationNotice() {
  return (
    <div className="mx-4 my-3 flex items-start gap-3 bg-orange-50 border border-orange-200 rounded-xl p-3">
      <span className="text-xl">🔄</span>
      <div>
        <p className="text-sm font-semibold text-orange-800">Connecting you to an officer</p>
        <p className="text-xs text-orange-600 mt-0.5">
          Your account has been flagged for officer follow-up. Someone from our team will contact
          you within 24 hours on your registered mobile or email.
        </p>
      </div>
    </div>
  );
}

// ── Saved-action toast ─────────────────────────────────────────

function SavedToast({ text }) {
  return (
    <div className="mx-4 my-1 flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 rounded-xl px-3 py-2 text-xs font-medium">
      <span>✅</span> {text}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────

export default function SelfCureBot() {
  const bottomRef  = useRef(null);
  const inputRef   = useRef(null);

  const [messages,      setMessages]      = useState([]);
  const [input,         setInput]         = useState('');
  const [sending,       setSending]       = useState(false);
  const [stage,         setStage]         = useState('greeting');
  const [language,      setLanguage]      = useState('auto');
  const [quickReplies,  setQuickReplies]  = useState([]);
  const [escalated,     setEscalated]     = useState(false);
  const [lastSaved,     setLastSaved]     = useState('');
  const [started,       setStarted]       = useState(false);   // greeting sent?

  // ── Scroll to bottom on new messages ─────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, quickReplies]);

  // ── Auto-focus input ──────────────────────────────────────────
  useEffect(() => {
    if (started && !escalated) inputRef.current?.focus();
  }, [started, escalated, sending]);

  // ── Format timestamp ──────────────────────────────────────────
  const now = () =>
    new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  // ── Core send function ────────────────────────────────────────
  const send = async (text) => {
    if (!text.trim() || sending || escalated) return;
    const userText = text.trim();
    setInput('');
    setSending(true);
    setLastSaved('');
    setQuickReplies([]);

    // Add user bubble immediately
    setMessages(m => [...m, { role: 'user', text: userText, timestamp: now() }]);

    try {
      const resp = await api.post('/customer/self-cure/chat', {
        message:  userText,
        stage:    stage,
        language: language,
      });

      const data = resp.data;

      // Sticky language
      if (data.language && data.language !== 'auto') {
        setLanguage(data.language);
      }

      setStage(data.stage ?? 'suggest_options');
      setQuickReplies(data.quick_replies ?? []);

      // Bot reply bubble
      setMessages(m => [...m, { role: 'bot', text: data.reply, timestamp: now() }]);

      if (data.escalate) setEscalated(true);
      if (data.saved)    setLastSaved(_savedLabel(data.stage));

    } catch (err) {
      setMessages(m => [...m, {
        role: 'bot',
        text: '⚠️ Sorry, I encountered an error. Please try again.',
        timestamp: now(),
      }]);
    } finally {
      setSending(false);
    }
  };

  // ── Start the conversation ────────────────────────────────────
  const startChat = async () => {
    setStarted(true);
    setSending(true);
    try {
      const resp = await api.post('/customer/self-cure/chat', {
        message:  'hello',
        stage:    'greeting',
        language: 'auto',
      });
      const data = resp.data;
      if (data.language && data.language !== 'auto') setLanguage(data.language);
      setStage(data.stage ?? 'suggest_options');
      setQuickReplies(data.quick_replies ?? []);
      setMessages([{ role: 'bot', text: data.reply, timestamp: now() }]);
    } catch {
      setMessages([{
        role: 'bot',
        text: '👋 Hello! I\'m your Self-Cure Assistant. How can I help you today?',
        timestamp: now(),
      }]);
      setQuickReplies([
        '📋 Check my loan status',
        '⏱ Request grace period',
        '🔄 Restructure loan',
        '💳 I want to pay now',
        '🆘 I need more help',
      ]);
    } finally {
      setSending(false);
    }
  };

  // ── Restart ───────────────────────────────────────────────────
  const restart = () => {
    setMessages([]);
    setInput('');
    setStage('greeting');
    setLanguage('auto');
    setQuickReplies([]);
    setEscalated(false);
    setLastSaved('');
    setStarted(false);
  };

  // ── Saved-action label ────────────────────────────────────────
  function _savedLabel(stg) {
    if (!stg) return '';
    if (stg.includes('grace'))       return 'Grace period request submitted ✅';
    if (stg.includes('restructure')) return 'Loan restructure request submitted ✅';
    if (stg.includes('pay'))         return 'Payment intent recorded ✅';
    if (stg.includes('escalate') || stg === 'closing') return 'Flagged for officer follow-up ✅';
    return '';
  }

  // ── Key handler ───────────────────────────────────────────────
  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[calc(100vh-112px)] max-w-2xl mx-auto">

      {/* ── Header ── */}
      <div className="bg-white rounded-t-2xl border border-gray-200 shadow-sm px-5 py-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-xl shadow">
            🤖
          </div>
          <div>
            <p className="font-bold text-gray-900 text-sm leading-tight">Self-Cure Assistant</p>
            <p className="text-xs text-gray-400 leading-tight">
              {escalated
                ? '🔄 Escalated to officer'
                : started
                ? <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                    Online · Multilingual
                  </span>
                : 'Ready to help'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <LangBadge lang={language !== 'auto' ? language : null} />
          {started && (
            <button
              onClick={restart}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition"
            >
              🔄 Restart
            </button>
          )}
        </div>
      </div>

      {/* ── Messages area ── */}
      <div className="flex-1 overflow-y-auto bg-gray-50 border-x border-gray-200 px-3 py-4">

        {/* Not started — welcome screen */}
        {!started && (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-6">
            <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center text-4xl shadow-inner">
              🤖
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">Self-Cure Bot</h2>
              <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                I can help you check your loan status, request a grace period,
                explore restructuring options, or connect you to an officer — in your preferred language.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-400">
              {['🌐 English', '🇮🇳 Hindi', '🇮🇳 Tamil', '🇮🇳 Telugu', '🇮🇳 Kannada', '🇮🇳 Malayalam', '🇮🇳 Bengali', '🇮🇳 Gujarati'].map(l => (
                <span key={l} className="px-2 py-0.5 bg-gray-100 rounded-full border border-gray-200">{l}</span>
              ))}
            </div>
            <button
              onClick={startChat}
              className="mt-2 px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition shadow"
            >
              🚀 Start Chat
            </button>
          </div>
        )}

        {/* Messages */}
        {started && messages.map((msg, i) => (
          <Bubble key={i} role={msg.role} text={msg.text} timestamp={msg.timestamp} />
        ))}

        {/* Typing indicator */}
        {sending && (
          <div className="flex justify-start mb-3">
            <div className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center flex-shrink-0 mr-2 mt-1">
              🤖
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center h-4">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {/* Escalation notice */}
        {escalated && <EscalationNotice />}

        {/* Saved confirmation */}
        {lastSaved && <SavedToast text={lastSaved} />}

        {/* Quick replies — shown after last bot message */}
        {!sending && quickReplies.length > 0 && !escalated && (
          <QuickReplies options={quickReplies} onSelect={send} disabled={sending} />
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="bg-white border border-t-0 border-gray-200 rounded-b-2xl px-4 py-3 flex items-end gap-3 flex-shrink-0 shadow-sm">
        {escalated ? (
          <div className="flex-1 text-sm text-gray-400 italic py-1 px-2">
            Your request has been escalated. An officer will contact you soon.
          </div>
        ) : !started ? (
          <div className="flex-1 text-sm text-gray-400 italic py-1 px-2">
            Click "Start Chat" to begin
          </div>
        ) : (
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type your message… (Enter to send)"
            disabled={sending || escalated}
            className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-400 max-h-28 overflow-y-auto"
            style={{ minHeight: '40px' }}
          />
        )}
        <button
          onClick={() => send(input)}
          disabled={!started || !input.trim() || sending || escalated}
          className="flex-shrink-0 w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition shadow-sm"
        >
          {sending
            ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            : <span className="text-base">➤</span>
          }
        </button>
      </div>

    </div>
  );
}
