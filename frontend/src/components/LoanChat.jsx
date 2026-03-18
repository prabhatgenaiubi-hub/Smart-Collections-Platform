import { useEffect, useRef, useState, useCallback } from 'react';
import api from '../api';

export default function LoanChat({ loan, onClose }) {
  const bottomRef = useRef(null);

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
    setInput(''); setError('');
    loadSessions();
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !sessionId || sending) return;
    setInput(''); setSending(true); setError('');
    setMessages(m => [...m, { role: 'user', message_text: text, timestamp: new Date().toISOString() }]);
    try {
      const r = await api.post(`/chat/sessions/${sessionId}/message`, {
        message: text,
        loan_id: loan.loan_id,
      });
      setMessages(m => [...m, r.data.ai_response]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message.');
      setMessages(m => [...m, {
        role: 'assistant',
        message_text: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally { setSending(false); }
  };

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
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
              <p className="font-bold text-base truncate">
                💬 {view === 'list' ? 'Loan Chat' : (sessionTitle || 'Chat')}
              </p>
              <p className="text-xs text-blue-100 mt-0.5 truncate">
                {loan.loan_id} · {loan.loan_type} · ₹{loan.outstanding_balance?.toLocaleString('en-IN')} outstanding
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
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
                <div className="text-center text-gray-400 text-sm mt-10">
                  <p className="text-3xl mb-2">🤖</p>
                  <p>Ask anything about this loan — EMIs, grace periods, restructuring, and more.</p>
                </div>
              )}

              {!loadingChat && messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                      isUser
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : msg.role === 'assistant'
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
              <div ref={bottomRef} />
            </div>

            <div className="px-4 py-3 border-t border-gray-100 bg-white flex gap-2 items-end flex-shrink-0">
              <textarea
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about this loan…"
                disabled={loadingChat || sending}
                className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 max-h-32 overflow-y-auto"
                style={{ lineHeight: '1.5' }}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loadingChat || sending}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors flex-shrink-0"
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
