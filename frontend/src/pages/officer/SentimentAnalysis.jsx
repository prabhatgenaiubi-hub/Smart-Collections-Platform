import { useEffect, useRef, useState, useCallback } from 'react';
import api from '../../api';

// ── Helpers ────────────────────────────────────────────────────────────────────────────

function tonalityBg(t) {
  return t === 'Positive'
    ? 'bg-green-100 text-green-700'
    : t === 'Negative'
    ? 'bg-red-100 text-red-700'
    : 'bg-yellow-100 text-yellow-700';
}
function tonalityEmoji(t) { return t === 'Positive' ? '😊' : t === 'Negative' ? '😟' : '😐'; }
function trendIcon(t)     { return t === 'Improving' ? '📈' : t === 'Deteriorating' ? '📉' : '➡️'; }
function typeIcon(t)      { return t === 'Chat' ? '💬' : t === 'Call' ? '📞' : '❓'; }

function scoreBar(score) {
  const s   = score ?? 0;
  const pct   = Math.round(((s + 1) / 2) * 100);
  const color = s > 0.2 ? 'bg-green-500' : s < -0.2 ? 'bg-red-500' : 'bg-yellow-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-10 text-right">
        {s > 0 ? '+' : ''}{s.toFixed(2)}
      </span>
    </div>
  );
}

// ── Inline Negative Detail Panel ────────────────────────────────────────────────────────────

function InlineNegativeDetail({ customerId, interaction }) {
  const [detail,  setDetail]  = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/officer/customer/${customerId}/interactions`)
      .then(r => setDetail(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) {
    return (
      <div className="flex justify-center py-3">
        <div className="animate-spin rounded-full h-5 w-5 border-2 border-red-400 border-t-transparent" />
      </div>
    );
  }
  if (!detail) return null;

  const isoTime = interaction.interaction_time;

  if (interaction.interaction_type === 'Chat') {
    // ── Step 1: try to find session by timestamp match (real chat sessions) ──
    let target = null;
    for (const s of detail.chat_sessions) {
      if (s.messages.some(m => m.timestamp?.slice(0, 16) === isoTime?.slice(0, 16))) {
        target = s; break;
      }
    }

    // ── Step 2: collect ALL negative messages across ALL sessions ──
    const allNegs = [];
    for (const s of detail.chat_sessions) {
      const neg = s.messages.filter(m => m.role === 'user' && m.sentiment_label === 'Negative');
      neg.forEach(m => allNegs.push({ ...m, _session_title: s.session_title }));
    }

    // ── Step 3: if a target session was found, prefer its negs; else use allNegs ──
    const sessionNegs = target
      ? target.messages.filter(m => m.role === 'user' && m.sentiment_label === 'Negative')
      : [];

    const displayNegs   = sessionNegs.length > 0 ? sessionNegs : allNegs;
    const displayTitle  = target ? target.session_title : 'All Chat Sessions';
    const hasRealChats  = detail.chat_sessions.length > 0;

    // ── Step 4: fallback — use conversation_text from InteractionHistory ──
    if (!hasRealChats || displayNegs.length === 0) {
      const convText = interaction.interaction_summary || interaction.conversation_text;
      if (!convText) return <p className="text-xs text-gray-400 py-2">No chat records found.</p>;
      return (
        <div className="mt-2 border-t border-red-100 pt-2 space-y-1.5">
          <p className="text-[10px] font-semibold text-red-500 uppercase tracking-wide mb-1">
            🚨 Interaction Record – {isoTime?.slice(0, 10)}
          </p>
          <div className="flex justify-end">
            <div className="max-w-[90%] bg-red-600 text-white rounded-2xl rounded-br-none px-3 py-2 text-xs ring-2 ring-red-200">
              {convText}
              <div className="text-[9px] text-red-200 mt-0.5">{isoTime?.slice(11, 16)}</div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="mt-2 border-t border-red-100 pt-2 space-y-1.5">
        <p className="text-[10px] font-semibold text-red-500 uppercase tracking-wide mb-1">
          🚨 Flagged Messages in &quot;{displayTitle}&quot;
        </p>
        {displayNegs.map((msg, i) => (
          <div key={i} className="flex justify-end">
            <div className="max-w-[90%] bg-red-600 text-white rounded-2xl rounded-br-none px-3 py-2 text-xs ring-2 ring-red-200">
              {msg.message_text}
              <div className="text-[9px] text-red-200 mt-0.5 flex items-center gap-1">
                <span>{msg.timestamp?.slice(11, 16)}</span>
                {msg._session_title && <span>· {msg._session_title}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (interaction.interaction_type === 'Call') {
    // Try exact timestamp match first
    const call = detail.calls.find(c => c.interaction_time?.slice(0, 16) === isoTime?.slice(0, 16))
                 || detail.calls.find(c => c.tonality_score === 'Negative')
                 || detail.calls[0];
    if (!call) {
      // Fallback: show conversation_text from the interaction itself
      const convText = interaction.interaction_summary || interaction.conversation_text;
      if (!convText) return <p className="text-xs text-gray-400 py-2">No call record found.</p>;
      return (
        <div className="mt-2 border-t border-red-100 pt-2">
          <p className="text-[10px] font-semibold text-red-500 uppercase tracking-wide mb-0.5">🚨 AI Summary</p>
          <p className="text-xs text-gray-700 leading-relaxed">{convText}</p>
        </div>
      );
    }
    return (
      <div className="mt-2 border-t border-red-100 pt-2 space-y-2">
        {(call.interaction_summary || interaction.interaction_summary) && (
          <div>
            <p className="text-[10px] font-semibold text-red-500 uppercase tracking-wide mb-0.5">🚨 AI Summary</p>
            <p className="text-xs text-gray-700 leading-relaxed">
              {call.interaction_summary || interaction.interaction_summary}
            </p>
          </div>
        )}
        {(call.conversation_text || interaction.conversation_text) && (
          <div>
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-0.5">📝 Transcript</p>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap max-h-36 overflow-y-auto">
              {call.conversation_text || interaction.conversation_text}
            </p>
          </div>
        )}
      </div>
    );
  }

  // SMS / Email fallback
  if (interaction.interaction_summary || interaction.conversation_text) {
    return (
      <div className="mt-2 border-t border-red-100 pt-2 space-y-2">
        {interaction.interaction_summary && (
          <div>
            <p className="text-[10px] font-semibold text-red-500 uppercase tracking-wide mb-0.5">🚨 Summary</p>
            <p className="text-xs text-gray-700 leading-relaxed">{interaction.interaction_summary}</p>
          </div>
        )}
        {interaction.conversation_text && (
          <div>
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-0.5">📝 Content</p>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap max-h-28 overflow-y-auto">
              {interaction.conversation_text}
            </p>
          </div>
        )}
      </div>
    );
  }
  return null;
}

// ── Interaction Detail Modal ───────────────────────────────────────────────────────────────

function InteractionDetailModal({ customerId, customerName, onClose }) {
  const [data,        setData]        = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [tab,         setTab]         = useState('chat');
  const [openSession, setOpenSession] = useState(null);

  useEffect(() => {
    api.get(`/officer/customer/${customerId}/interactions`)
      .then(r => {
        setData(r.data);
        if (r.data.chat_sessions.length === 0 && r.data.calls.length > 0) setTab('calls');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [customerId]);

  const handleBackdrop = e => { if (e.target === e.currentTarget) onClose(); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4" onClick={handleBackdrop}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">

        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-800">{customerName}</h2>
            <p className="text-xs text-gray-400">{customerId} · Full Interaction History</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none font-light">×</button>
        </div>

        <div className="flex bg-gray-50 border-b border-gray-100 px-6 gap-4">
          {['chat', 'calls'].map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`py-3 text-sm font-semibold border-b-2 transition-colors ${
                tab === t ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'chat'
                ? `💬 Chat Sessions ${data ? `(${data.chat_sessions.length})` : ''}`
                : `📞 Call Recordings ${data ? `(${data.calls.length})` : ''}`}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent" />
            </div>
          )}

          {!loading && tab === 'chat' && (
            <div className="space-y-3">
              {data.chat_sessions.length === 0
                ? <p className="text-sm text-gray-400 text-center py-8">No chat sessions found.</p>
                : data.chat_sessions.map(session => (
                  <div key={session.session_id} className="border border-gray-200 rounded-xl overflow-hidden">
                    <button
                      className="w-full text-left px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                      onClick={() => setOpenSession(openSession === session.session_id ? null : session.session_id)}
                    >
                      <div>
                        <p className="text-sm font-semibold text-gray-700">📋 {session.session_title}</p>
                        <p className="text-xs text-gray-400">
                          Started {session.created_at?.slice(0, 16)} · {session.messages.filter(m => m.role === 'user').length} user message(s)
                          {session.messages.some(m => m.sentiment_label === 'Negative') && (
                            <span className="text-red-500 ml-2">· has negative messages</span>
                          )}
                        </p>
                      </div>
                      <span className="text-gray-400 text-sm">{openSession === session.session_id ? '▲' : '▼'}</span>
                    </button>
                    {openSession === session.session_id && (
                      <div className="px-4 py-3 space-y-2 bg-white max-h-72 overflow-y-auto">
                        {session.messages.map((msg, idx) => {
                          const isNeg = msg.sentiment_label === 'Negative';
                          return (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                              <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                                msg.role === 'user'
                                  ? isNeg ? 'bg-red-600 text-white rounded-br-none ring-2 ring-red-300' : 'bg-blue-600 text-white rounded-br-none'
                                  : msg.role === 'assistant' ? 'bg-gray-100 text-gray-800 rounded-bl-none'
                                  : 'bg-yellow-50 text-gray-500 text-xs italic w-full text-center rounded-xl'
              }`}>
                                {msg.role === 'system' && <span className="font-medium">System: </span>}
                                {msg.message_text}
                                <div className={`text-[10px] mt-1 flex items-center gap-1 ${
                                  msg.role === 'user' ? (isNeg ? 'text-red-200' : 'text-blue-200') : 'text-gray-400'
                                }`}>
                                  <span>{msg.timestamp?.slice(11, 16)}</span>
                                  {isNeg && <span>· 🚨 Negative</span>}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))
              }
            </div>
          )}

          {!loading && tab === 'calls' && (
            <div className="space-y-3">
              {data.calls.length === 0
                ? <p className="text-sm text-gray-400 text-center py-8">No call recordings analyzed.</p>
                : data.calls.map(call => (
                  <div key={call.interaction_id} className="border border-gray-200 rounded-xl overflow-hidden">
                    <div className={`px-4 py-3 flex items-center justify-between ${tonalityBg(call.tonality_score)}`}>
                      <div>
                        <p className="text-sm font-semibold">
                          {tonalityEmoji(call.tonality_score)} {call.tonality_score} · Score: {call.sentiment_score > 0 ? '+' : ''}{call.sentiment_score?.toFixed(2)}
                        </p>
                        <p className="text-xs opacity-75">{call.interaction_time?.slice(0, 16)}</p>
                      </div>
                    </div>
                    {call.interaction_summary && (
                      <div className="px-4 py-2 bg-white border-b border-gray-100">
                        <p className="text-xs text-gray-500 font-medium mb-0.5">AI Summary</p>
                        <p className="text-sm text-gray-700">{call.interaction_summary}</p>
                      </div>
                    )}
                    {call.conversation_text && (
                      <div className="px-4 py-3 bg-gray-50">
                        <p className="text-xs text-gray-500 font-medium mb-1">📝 Full Transcript</p>
                        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{call.conversation_text}</p>
                      </div>
                    )}
                  </div>
                ))
              }
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Customer Sentiment Card ────────────────────────────────────────────────────────────────

function CustomerSentimentCard({ data }) {
  const [expanded,   setExpanded]   = useState(false);
  const [showModal,  setShowModal]  = useState(false);
  const [inlineOpen, setInlineOpen] = useState(null);

  const headerTonality = data.last3_tonality || data.dominant_tonality || 'Neutral';
  const headerTrend    = data.last3_trend    || data.sentiment_trend   || 'Stable';
  const headerScore    = data.last3_sentiment ?? data.average_sentiment ?? 0;
  const recentList     = data.recent_interactions || data.interactions || [];

  return (
    <div className="bg-white rounded-xl shadow border border-gray-100 overflow-hidden">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full text-left px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-2xl">{tonalityEmoji(headerTonality)}</span>
          <div className="min-w-0">
            <p className="font-semibold text-gray-800 text-sm truncate">{data.customer_name}</p>
            <p className="text-xs text-gray-400">{data.customer_id} · {data.total_interactions} total interactions</p>
          </div>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0 ml-4">
          <div className="text-right">
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${tonalityBg(headerTonality)}`}>{headerTonality}</span>
            <p className="text-[10px] text-gray-400 mt-0.5">last 3</p>
          </div>
          <span className="text-sm" title={`Trend (last 3): ${headerTrend}`}>{trendIcon(headerTrend)}</span>
          <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      <div className="px-5 pb-1">
        <p className="text-[10px] text-gray-400 mb-0.5">Last 3 interactions sentiment</p>
        {scoreBar(headerScore)}
      </div>
      <div className="px-5 pb-3">
        <p className="text-[10px] text-gray-400 mb-0.5">All-time average</p>
        {scoreBar(data.average_sentiment ?? data.avg_sentiment_score ?? 0)}
      </div>

      {expanded && (
        <div className="border-t border-gray-100 px-5 py-3 space-y-2 bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Last 3 Interactions</p>
            <button
              onClick={() => setShowModal(true)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors"
            >
              🔍 View Full History
            </button>
          </div>

          {recentList.length === 0 && (
            <p className="text-xs text-gray-400">No interaction history (Chat or Call).</p>
          )}

          {recentList.map((i, idx) => {
            const isNeg        = i.tonality_score === 'Negative';
            const isInlineOpen = inlineOpen === i.interaction_time;
            return (
              <div key={idx} className={`bg-white rounded-lg px-4 py-2.5 border text-xs ${isNeg ? 'border-red-200' : 'border-gray-100'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-700">
                    {typeIcon(i.interaction_type)} {i.interaction_type} · {i.interaction_time?.slice(0, 16)}
                  </span>
                  {isNeg ? (
                    <button
                      onClick={() => setInlineOpen(isInlineOpen ? null : i.interaction_time)}
                      className={`flex items-center gap-1 px-2 py-0.5 rounded-full font-medium transition-colors hover:opacity-80 cursor-pointer ${tonalityBg(i.tonality_score)}`}
                      title="Click to see flagged messages"
                    >
                      {tonalityEmoji(i.tonality_score)} {i.tonality_score}
                      <span className="ml-0.5 text-[9px]">{isInlineOpen ? '▲' : '▼'}</span>
                    </button>
                  ) : (
                    <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full font-medium select-none ${tonalityBg(i.tonality_score)}`}>
                      {tonalityEmoji(i.tonality_score)} {i.tonality_score}
                    </span>
                  )}
                </div>
                <p className="text-gray-500 leading-relaxed">{i.interaction_summary}</p>
                {scoreBar(i.sentiment_score)}
                {isNeg && isInlineOpen && (
                  <InlineNegativeDetail customerId={data.customer_id} interaction={i} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <InteractionDetailModal
          customerId={data.customer_id}
          customerName={data.customer_name}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}

// ── Voice Call Analyzer Card ───────────────────────────────────────────────────────────────

function CallAnalyzerCard({ customers, onAnalyzed }) {
  const fileRef          = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);
  const timerRef         = useRef(null);

  const [tab,          setTab]          = useState('upload');
  const [customerId,   setCustomerId]   = useState('');
  const [file,         setFile]         = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [result,       setResult]       = useState(null);
  const [error,        setError]        = useState('');
  const [recording,    setRecording]    = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedUrl,  setRecordedUrl]  = useState('');
  const [recSeconds,   setRecSeconds]   = useState(0);
  const [micSupported, setMicSupported] = useState(true);

  const switchTab = t => {
    setTab(t); setResult(null); setError(''); setFile(null);
    setRecordedBlob(null); setRecordedUrl(''); setRecSeconds(0);
  };

  const startRecording = useCallback(async () => {
    setError(''); setRecordedBlob(null); setRecordedUrl(''); setRecSeconds(0);
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mr;
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setRecordedBlob(blob);
        setRecordedUrl(URL.createObjectURL(blob));
      };
      mr.start(250);
      setRecording(true);
      timerRef.current = setInterval(() => setRecSeconds(s => s + 1), 1000);
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied.');
      } else {
        setMicSupported(false);
        setError('Microphone not available.');
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  }, []);

  const fmtTime = s => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const handleSubmit = async e => {
    e.preventDefault();
    const src = tab === 'upload' ? file : recordedBlob;
    if (!customerId || !src) {
      setError(tab === 'upload' ? 'Please select a customer and upload an audio file.' : 'Please select a customer and record a call first.');
      return;
    }
    setError(''); setResult(null); setLoading(true);
    const fd = new FormData();
    fd.append('customer_id', customerId);
    fd.append('audio_file', tab === 'upload' ? file : new File([recordedBlob], 'recording.webm', { type: 'audio/webm' }));
    try {
      const r = await api.post('/officer/sentiment/analyze-call', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setResult(r.data);
      if (onAnalyzed) onAnalyzed();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze call.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow p-6 border border-gray-100">
      <h2 className="text-lg font-bold text-gray-800 mb-1">🎤 Call Recording Analyzer</h2>
      <p className="text-sm text-gray-500 mb-4">Transcribed locally with Whisper · Sentiment analysis applied automatically</p>

      <div className="flex bg-gray-100 rounded-xl p-1 mb-5 gap-1">
        {[['upload', '📁 Upload File'], ['record', '🎤 Record Live']].map(([t, label]) => (
          <button key={t} onClick={() => switchTab(t)}
            className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${
              tab === t ? `bg-white shadow ${t === 'upload' ? 'text-blue-600' : 'text-red-600'}` : 'text-gray-500 hover:text-gray-700'
            }`}
          >{label}</button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Select Customer</label>
          <select value={customerId} onChange={e => setCustomerId(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— Choose a customer —</option>
            {customers.map(c => (
              <option key={c.customer_id} value={c.customer_id}>{c.customer_name} ({c.customer_id})</option>
            ))}
          </select>
        </div>

        {tab === 'upload' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Audio File</label>
            <div onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-300 hover:border-blue-400 rounded-xl p-6 text-center cursor-pointer transition-colors"
            >
              {file ? (
                <div>
                  <p className="text-sm font-medium text-blue-600">🎵 {file.name}</p>
                  <p className="text-xs text-gray-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-3xl mb-2">📂</p>
                  <p className="text-sm text-gray-500">Click to upload or drag &amp; drop</p>
                  <p className="text-xs text-gray-400 mt-1">MP3, WAV, M4A, OGG, FLAC</p>
                </div>
              )}
            </div>
            <input ref={fileRef} type="file" accept=".mp3,.wav,.m4a,.ogg,.flac" className="hidden"
              onChange={e => setFile(e.target.files[0] || null)} />
          </div>
        )}

        {tab === 'record' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Microphone Recording</label>
            {!micSupported ? (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 text-sm rounded-xl px-4 py-3">
                ⚠️ Browser does not support recording. Use Chrome or Edge.
              </div>
            ) : (
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-5 text-center">
                {!recording && !recordedBlob && (
                  <div>
                    <p className="text-4xl mb-3">🎤</p>
                    <p className="text-sm text-gray-500 mb-4">Click to start recording</p>
                    <button type="button" onClick={startRecording}
                      className="bg-red-500 hover:bg-red-600 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors"
                    >⏺ Start Recording</button>
                  </div>
                )}
                {recording && (
                  <div>
                    <div className="flex items-center justify-center gap-3 mb-3">
                      <span className="animate-pulse text-red-500 text-2xl">⏺</span>
                      <span className="font-mono text-xl font-bold text-red-600">{fmtTime(recSeconds)}</span>
                    </div>
                    <p className="text-sm text-gray-500 mb-4">Recording in progress…</p>
                    <button type="button" onClick={stopRecording}
                      className="bg-gray-700 hover:bg-gray-800 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors"
                    >⏹ Stop Recording</button>
                  </div>
                )}
                {!recording && recordedBlob && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-center gap-2 text-green-600">
                      <span className="text-xl">✅</span>
                      <span className="text-sm font-semibold">Recorded · {fmtTime(recSeconds)}</span>
                    </div>
                    <audio src={recordedUrl} controls className="w-full rounded-lg" />
                    <button type="button" onClick={startRecording} className="text-xs text-gray-400 hover:text-red-500 underline">
                      🔄 Re-record
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">⚠️ {error}</div>
        )}

        <button type="submit" disabled={loading || recording}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl text-sm transition-colors"
        >
          {loading ? '⏳ Transcribing & Analyzing…' : '🔍 Analyze Call'}
        </button>
      </form>

      {result && (
        <div className="mt-6 space-y-4">
          <div className={`rounded-xl p-4 ${tonalityBg(result.tonality)}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-base">{tonalityEmoji(result.tonality)} {result.tonality} Sentiment</span>
              <span className="text-sm font-mono">Score: {result.sentiment_score > 0 ? '+' : ''}{result.sentiment_score.toFixed(2)}</span>
            </div>
            <p className="text-sm">{result.interaction_summary}</p>
            {scoreBar(result.sentiment_score)}
          </div>
          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">📝 Transcript</p>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{result.transcript}</p>
          </div>
          <p className="text-xs text-gray-400 text-right">Saved to interaction history · Customer: {result.customer_name}</p>
        </div>
      )}
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────────────────────

export default function SentimentAnalysis() {
  const [data,        setData]        = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);
  const [error,       setError]       = useState('');
  const [search,      setSearch]      = useState('');
  const [filter,      setFilter]      = useState('Negative');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [secAgo,      setSecAgo]      = useState(0);

  const fetchSentiment = useCallback(() => {
    setRefreshing(true);
    api.get('/officer/sentiment')
      .then(r => { setData(r.data); setLastUpdated(Date.now()); setSecAgo(0); })
      .catch(() => {})
      .finally(() => setRefreshing(false));
  }, []);

  useEffect(() => {
    api.get('/officer/sentiment')
      .then(r => { setData(r.data); setLastUpdated(Date.now()); })
      .catch(() => setError('Failed to load sentiment data.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const poll = setInterval(fetchSentiment, 30_000);
    return () => clearInterval(poll);
  }, [fetchSentiment]);

  useEffect(() => {
    const tick = setInterval(() => {
      if (lastUpdated) setSecAgo(Math.floor((Date.now() - lastUpdated) / 1000));
    }, 1000);
    return () => clearInterval(tick);
  }, [lastUpdated]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }
  if (error) return <div className="text-red-500 p-6">{error}</div>;

  const customers    = data?.customers    || [];
  const allCustomers = data?.all_customers || [];

  const filtered = customers.filter(c => {
    const matchFilter = filter === 'All' || (c.last3_tonality || c.dominant_tonality) === filter;
    const matchSearch = !search
      || c.customer_name.toLowerCase().includes(search.toLowerCase())
      || c.customer_id.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  return (
    <div className="space-y-6">

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">🧠 Customer Sentiment Analysis</h1>
          <p className="text-sm text-gray-500 mt-0.5">Real-time sentiment tracking across calls and chats</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-gray-400">Updated {secAgo}s ago · auto-refreshes every 30s</span>
          )}
          <button onClick={fetchSentiment} disabled={refreshing}
            className="text-xs bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors"
          >
            {refreshing
              ? <span className="animate-spin inline-block h-3 w-3 border-2 border-blue-400 border-t-transparent rounded-full" />
              : '🔄'
            }
            Refresh
          </button>
        </div>
      </div>

      {data?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Customers', value: data.summary.total_customers, color: 'text-gray-800'   },
            { label: '😊 Positive',     value: data.summary.positive_count,  color: 'text-green-600' },
            { label: '😐 Neutral',      value: data.summary.neutral_count,   color: 'text-yellow-600'},
            { label: '😟 Negative',     value: data.summary.negative_count,  color: 'text-red-500'   },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl shadow p-4 border border-gray-100">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-2xl shadow p-4 border border-gray-100">
            <div className="flex flex-wrap gap-2 mb-4">
              <input
                type="text"
                placeholder="Search customers…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="flex-1 min-w-[160px] border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {['All', 'Negative', 'Neutral', 'Positive'].map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                    filter === f
                      ? f === 'Negative' ? 'bg-red-500 text-white border-red-500'
                        : f === 'Positive' ? 'bg-green-500 text-white border-green-500'
                        : f === 'Neutral'  ? 'bg-yellow-400 text-white border-yellow-400'
                        : 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                  }`}
                >{f}</button>
              ))}
            </div>

            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-600">
                👥 Customer Sentiment
                <span className="ml-2 text-xs font-normal text-gray-400">({filtered.length} shown)</span>
              </p>
              {refreshing && (
                <span className="flex items-center gap-1 text-xs text-blue-500">
                  <span className="animate-spin inline-block h-3 w-3 border-2 border-blue-400 border-t-transparent rounded-full" />
                  Updating…
                </span>
              )}
            </div>

            {filtered.length === 0
              ? <p className="text-sm text-gray-400 text-center py-8">No customers match the current filter.</p>
              : <div className="space-y-3">{filtered.map(c => <CustomerSentimentCard key={c.customer_id} data={c} />)}</div>
            }
          </div>
        </div>

        <div className="lg:col-span-1">
          <CallAnalyzerCard customers={allCustomers} onAnalyzed={fetchSentiment} />
        </div>
      </div>
    </div>
  );
}
