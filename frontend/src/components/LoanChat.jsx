import { useEffect, useRef, useState, useCallback } from 'react';
import api from '../api';

// ── Language badge shown in header when a non-English language is detected ──
const LANG_FLAGS = {
  English: '🌐', Hindi: '🇮🇳', Tamil: '🇮🇳', Telugu: '🇮🇳',
  Kannada: '🇮🇳', Malayalam: '🇮🇳', Marathi: '🇮🇳',
  Gujarati: '🇮🇳', Bengali: '🇮🇳',
};

function LangBadge({ lang }) {
  if (!lang || lang === 'auto') return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-white/20 text-white border border-white/30">
      {LANG_FLAGS[lang] ?? '🌐'} {lang}
    </span>
  );
}

export default function LoanChat({ loan, onClose }) {
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);
  const chunksRef = useRef([]);
  const mrRef     = useRef(null);

  const [view,         setView]         = useState('list');
  const [sessions,     setSessions]     = useState([]);
  const [loadingList,  setLoadingList]  = useState(true);
  const [sessionId,    setSessionId]    = useState(null);
  const [sessionTitle, setSessionTitle] = useState('');
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState('');
  const [sending,      setSending]      = useState(false);
  const [loadingChat,  setLoadingChat]  = useState(false);
  const [creating,     setCreating]     = useState(false);
  const [error,        setError]        = useState('');

  // Multilingual + voice state
  const [language,   setLanguage]   = useState('Hindi');  // Default to Hindi for better STT accuracy
  const [recording,  setRecording]  = useState(false);
  const [micLoading, setMicLoading] = useState(false);
  const [micError,   setMicError]   = useState('');
  const micSupported = !!(navigator.mediaDevices?.getUserMedia);

  const loadSessions = useCallback(() => {
    setLoadingList(true);
    api.get('/chat/sessions')
      .then(r => {
        const all = r.data.sessions || [];
        setSessions(all.filter(s => s.session_title?.includes(loan.loan_id)));
      })
      .catch(() => setError('Could not load chat history.'))
      .finally(() => setLoadingList(false));
  }, [loan.loan_id]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  const openSession = (sid, title) => {
    setError(''); setSessionId(sid); setSessionTitle(title);
    setMessages([]); setLoadingChat(true); setView('chat');
    api.get(`/chat/sessions/${sid}`)
      .then(r => setMessages(r.data.messages || []))
      .catch(() => setError('Could not load messages.'))
      .finally(() => setLoadingChat(false));
  };

  const createSession = async () => {
    setCreating(true); setError('');
    try {
      const r      = await api.post('/chat/sessions', {
        session_title: `Loan ${loan.loan_id} – ${loan.loan_type || 'Query'}`,
      });
      const sid    = r.data.session_id;
      const detail = await api.get(`/chat/sessions/${sid}`);
      setSessionId(sid);
      setSessionTitle(r.data.session?.session_title || `Loan ${loan.loan_id}`);
      setMessages(detail.data.messages || []);
      setView('chat');
    } catch {
      setError('Could not start a new chat. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const deleteSession = async (e, sid) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/sessions/${sid}`);
      setSessions(s => s.filter(x => x.session_id !== sid));
    } catch { setError('Could not delete session.'); }
  };

  const backToList = () => {
    setView('list'); setSessionId(null); setMessages([]);
    setInput(''); setError(''); setLanguage('auto'); setMicError('');
    loadSessions();
  };

  // sendMessage(text, _unused, lang)
  // - text: English text (from transcribe or typed)
  // - lang: detected language name e.g. 'Hindi' (for response translation)
  const sendMessage = useCallback(async (textArg, _unused, langArg) => {
    const text = (textArg ?? input).trim();
    const lang = langArg ?? language;
    if (!text || !sessionId || sending) return;
    setInput(''); setSending(true); setError('');
    // Show the English text in the chat bubble with metadata
    const userMsg = {
      role: 'user',
      message_text: text,
      timestamp: new Date().toISOString(),
      isEnglishTranscript: lang !== 'auto' && lang !== 'English', // flag if it's from voice
      originalLanguage: lang,
    };
    setMessages(m => [...m, userMsg]);
    try {
      const r = await api.post(`/chat/sessions/${sessionId}/message`, {
        message:           text,                                   // English text
        loan_id:           loan.loan_id,
        ...(lang !== 'auto' && { language: lang }),                // detected language for response translation
      });
      // Response includes: ai_response, detected_language, analysis
      const aiMsg = { ...r.data.ai_response };
      if (r.data.analysis) {
        aiMsg.analysis = r.data.analysis;  // Attach analysis to the message
      }
      setMessages(m => [...m, aiMsg]);
      // DO NOT auto-update language - respect user's manual selection
      // if (r.data.detected_language) setLanguage(r.data.detected_language);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message.');
      setMessages(m => [...m, {
        role: 'assistant',
        message_text: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally { setSending(false); }
  }, [input, sessionId, sending, loan.loan_id, language]);

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  // ── Voice recording ────────────────────────────────────────────
  // Pick the best supported MIME for the browser (opus is best for Saaras)
  const _getBestMime = () => {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    return candidates.find(m => MediaRecorder.isTypeSupported(m)) || '';
  };

  // BCP-47 hint map — tells Saaras which language to expect
  const _LANG_TO_BCP47 = {
    Hindi: 'hi-IN', Tamil: 'ta-IN', Telugu: 'te-IN',
    Kannada: 'kn-IN', Malayalam: 'ml-IN', Marathi: 'mr-IN',
    Gujarati: 'gu-IN', Bengali: 'bn-IN', Punjabi: 'pa-IN',
    Odia: 'od-IN',
  };

  const startRecording = async () => {
    if (!micSupported) { setMicError('Microphone not supported in this browser.'); return; }
    setMicError('');
    try {
      chunksRef.current = [];
      const stream  = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = _getBestMime();
      const mr = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mrRef.current = mr;
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setMicLoading(true);
        try {
          // Use the actual recorded MIME (may differ from requested)
          const actualMime = mr.mimeType || mimeType || 'audio/webm';
          const ext        = actualMime.includes('ogg') ? 'ogg'
                           : actualMime.includes('mp4') ? 'mp4'
                           : 'webm';
          const blob = new Blob(chunksRef.current, { type: actualMime });
          const fd   = new FormData();
          fd.append('audio_file', blob, `voice.${ext}`);

          // Pass current language as hint so Saaras knows what to expect
          const langHint = _LANG_TO_BCP47[language] || '';
          console.log('[Voice] Selected language:', language);
          console.log('[Voice] Language hint to send:', langHint);
          if (langHint) fd.append('language_hint', langHint);

          const resp = await api.post('/customer/self-cure/transcribe', fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });

          // transcribe now returns:
          //   transcript         — English text (what user said in English)
          //   detected_language  — display name ('Hindi', 'Tamil', etc.)
          //   language_code      — BCP-47 code ('hi-IN', etc.)
          const { transcript, detected_language: detectedLang } = resp.data;

          // DO NOT auto-update language dropdown - respect user's manual selection
          // if (detectedLang && detectedLang !== 'auto') setLanguage(detectedLang);

          if (transcript && transcript.trim()) {
            // Use user's selected language (not detected) for response translation
            await sendMessage(transcript.trim(), '', language);
          } else {
            setMicError('Could not transcribe audio. Please try speaking clearly.');
          }
        } catch {
          setMicError('Transcription failed. Please type your message.');
        } finally {
          setMicLoading(false);
        }
      };
      mr.start(250); // collect chunks every 250ms for better reliability
      setRecording(true);
    } catch {
      setMicError('Microphone access denied. Please allow microphone access.');
    }
  };

  const stopRecording = () => {
    if (mrRef.current && recording) { mrRef.current.stop(); setRecording(false); }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleBackdrop = e => { if (e.target === e.currentTarget) onClose(); };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={handleBackdrop}>
      <div className="w-full max-w-md bg-white shadow-2xl flex flex-col h-full">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-blue-600 text-white flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {view === 'chat' && (
              <button onClick={backToList} title="Back to sessions"
                className="text-white/80 hover:text-white text-lg leading-none mr-1"
              >
                ←
              </button>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-bold text-base truncate">
                  💬 {view === 'list' ? 'Loan Chat' : (sessionTitle || 'Chat')}
                </p>
                <LangBadge lang={language !== 'auto' ? language : null} />
              </div>
              <p className="text-xs text-blue-100 mt-0.5 truncate">
                {loan.loan_id} · {loan.loan_type} · ₹{loan.outstanding_balance?.toLocaleString('en-IN')} outstanding
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Language Selector */}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-white/20 hover:bg-white/30 text-white text-xs font-medium px-2 py-1 rounded-lg border border-white/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/50"
              title="Select your language for voice input"
            >
              <option value="Hindi" className="text-gray-800">🇮🇳 Hindi</option>
              <option value="Tamil" className="text-gray-800">🇮🇳 Tamil</option>
              <option value="Telugu" className="text-gray-800">🇮🇳 Telugu</option>
              <option value="Kannada" className="text-gray-800">🇮🇳 Kannada</option>
              <option value="Malayalam" className="text-gray-800">🇮🇳 Malayalam</option>
              <option value="Marathi" className="text-gray-800">🇮🇳 Marathi</option>
              <option value="Gujarati" className="text-gray-800">🇮🇳 Gujarati</option>
              <option value="Bengali" className="text-gray-800">🇮🇳 Bengali</option>
              <option value="Punjabi" className="text-gray-800">🇮🇳 Punjabi</option>
              <option value="English" className="text-gray-800">🌐 English</option>
            </select>
            
            {view === 'list' && (
              <button
                onClick={createSession}
                disabled={creating}
                className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 disabled:opacity-50 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
              >
                {creating
                  ? <span className="animate-spin inline-block h-3 w-3 border-2 border-white border-t-transparent rounded-full" />
                  : <span className="text-base leading-none">+</span>
                }
                New Chat
              </button>
            )}
            <button onClick={onClose} className="text-white/70 hover:text-white text-2xl leading-none font-light">
              ✕
            </button>
          </div>
        </div>

        {/* Error strip */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-red-600 text-xs flex-shrink-0">
            ⚠️ {error}
          </div>
        )}

        {/* Multilingual info strip — shown only in chat view */}
        {view === 'chat' && (
          <div className="px-4 py-1.5 bg-blue-50 border-b border-blue-100 flex items-center gap-2 flex-shrink-0">
            <span className="text-[11px] text-blue-600 font-medium">
              🌐 Selected: {language}
            </span>
            <span className="text-[11px] text-gray-400">· Responses in your language</span>
            {micSupported && (
              <span className="ml-auto text-[11px] text-gray-400 flex items-center gap-1">
                🎤 Voice enabled
              </span>
            )}
          </div>
        )}

        {/* SESSION LIST VIEW */}
        {view === 'list' && (
          <div className="flex-1 overflow-y-auto">
            {loadingList ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full py-20 text-center px-8">
                <p className="text-5xl mb-4">💬</p>
                <p className="text-gray-800 font-semibold text-base mb-1">No chats yet for this loan</p>
                <p className="text-sm text-gray-400 mb-6">
                  Start a conversation to get help with EMIs, grace periods, restructuring options, and more.
                  Ask in Hindi, Tamil, Telugu, Kannada, Malayalam, or any Indian language.
                </p>
                <button
                  onClick={createSession}
                  disabled={creating}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors flex items-center gap-2"
                >
                  {creating
                    ? <span className="animate-spin inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    : '💬'
                  }
                  Start New Chat
                </button>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {sessions.map(s => (
                  <button
                    key={s.session_id}
                    onClick={() => openSession(s.session_id, s.session_title)}
                    className="w-full text-left px-5 py-4 hover:bg-gray-50 transition-colors flex items-start justify-between gap-3 group"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-gray-800 truncate">{s.session_title}</p>
                      {s.last_message && (
                        <p className="text-xs text-gray-400 mt-0.5 truncate">{s.last_message}</p>
                      )}
                      <p className="text-[10px] text-gray-300 mt-1">
                        {s.last_updated?.slice(0, 16)} · {s.message_count} msg{s.message_count !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 pt-0.5">
                      <span className="text-blue-400 group-hover:text-blue-600 text-sm">›</span>
                      <button
                        onClick={e => deleteSession(e, s.session_id)}
                        className="text-gray-300 hover:text-red-400 transition-colors p-1 rounded"
                        title="Delete this chat"
                      >
                        🗑
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CHAT VIEW */}
        {view === 'chat' && (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50">
              {loadingChat && (
                <div className="flex justify-center items-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent" />
                </div>
              )}

              {!loadingChat && messages.length === 0 && (
                <div className="text-center text-gray-400 text-sm mt-10 px-4">
                  <p className="text-3xl mb-3">🤖</p>
                  <p className="font-medium text-gray-600 mb-1">Multilingual AI Banking Assistant</p>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Ask about EMIs, grace periods, restructuring, and more.<br />
                    You can type or speak in Hindi, Tamil, Telugu, Kannada, Malayalam, and other Indian languages.
                  </p>
                </div>
              )}

              {!loadingChat && messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                const isAssistant = msg.role === 'assistant';
                return (
                  <div key={idx} className="space-y-1.5">
                    {/* Transcription label for voice messages */}
                    {isUser && msg.isEnglishTranscript && (
                      <div className="flex justify-end">
                        <span className="text-[10px] text-gray-400 px-2">
                          📝 Transcribed Text ({msg.originalLanguage || 'English'})
                        </span>
                      </div>
                    )}
                    
                    {/* Message bubble */}
                    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-none'
                          : isAssistant
                          ? 'bg-white text-gray-800 rounded-bl-none border border-gray-100'
                          : 'bg-yellow-50 text-gray-500 text-xs italic rounded-xl w-full text-center'
                      }`}>
                        {msg.role === 'system' && <span className="font-medium">System: </span>}
                        <p className="whitespace-pre-wrap">{msg.message_text}</p>
                        <p className={`text-[10px] mt-1 ${isUser ? 'text-blue-200' : 'text-gray-400'}`}>
                          {msg.timestamp?.slice(11, 16)}
                        </p>
                      </div>
                    </div>

                    {/* Analysis section for assistant messages */}
                    {isAssistant && msg.analysis && (
                      <div className="flex justify-start">
                        <div className="max-w-[85%] bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-[11px] text-gray-600 space-y-0.5">
                          <p className="font-semibold text-gray-700 mb-1">🧠 Analysis</p>
                          <p><span className="font-medium">Intent:</span> {msg.analysis.intent}</p>
                          <p><span className="font-medium">Sentiment:</span> {
                            msg.analysis.sentiment === 'calm' ? '😌 Calm' :
                            msg.analysis.sentiment === 'frustrated' ? '😤 Frustrated' :
                            msg.analysis.sentiment === 'angry' ? '😡 Angry' :
                            msg.analysis.sentiment === 'distressed' ? '😰 Distressed' :
                            msg.analysis.sentiment
                          }</p>
                          <p><span className="font-medium">Escalation Required:</span> {
                            msg.analysis.escalation_required
                              ? '🚨 Yes'
                              : '✅ No'
                          }</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {sending && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
                    <div className="flex gap-1 items-center">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
              {micLoading && (
                <div className="flex justify-center my-1">
                  <span className="text-xs text-blue-500 flex items-center gap-1.5">
                    <span className="inline-block w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    Transcribing voice…
                  </span>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Mic error strip */}
            {micError && (
              <div className="px-4 py-1.5 bg-red-50 border-t border-red-100 text-xs text-red-500 flex items-center gap-1 flex-shrink-0">
                ⚠️ {micError}
                <button onClick={() => setMicError('')} className="ml-auto text-gray-400 hover:text-gray-600">✕</button>
              </div>
            )}

            <div className="px-4 py-3 border-t border-gray-100 bg-white flex gap-2 items-end flex-shrink-0">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about this loan… (any language)"
                disabled={loadingChat || sending || recording || micLoading}
                className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 max-h-32 overflow-y-auto"
                style={{ lineHeight: '1.5' }}
              />

              {/* Voice mic button */}
              {micSupported && (
                <button
                  type="button"
                  onClick={recording ? stopRecording : startRecording}
                  disabled={sending || micLoading || loadingChat}
                  title={recording ? 'Stop recording' : 'Voice input — speak in any language'}
                  className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition text-sm disabled:cursor-not-allowed ${
                    recording
                      ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:text-gray-300'
                  }`}
                >
                  {micLoading
                    ? <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                    : recording ? '⏹' : '🎤'}
                </button>
              )}

              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loadingChat || sending || recording || micLoading}
                className="flex-shrink-0 w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white flex items-center justify-center text-sm font-semibold transition-colors"
              >
                {sending ? '…' : '↑'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
