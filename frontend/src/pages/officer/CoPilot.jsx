import { useEffect, useRef, useState } from 'react';
import api from '../../api';

// ── Helpers ────────────────────────────────────────────────────────────────────

function tonalityBadge(t) {
  const map = {
    Positive:   'bg-green-100 text-green-700 border border-green-200',
    Negative:   'bg-red-100   text-red-700   border border-red-200',
    Neutral:    'bg-yellow-100 text-yellow-700 border border-yellow-200',
    Frustrated: 'bg-orange-100 text-orange-700 border border-orange-200',
    Anxious:    'bg-purple-100 text-purple-700 border border-purple-200',
    Cooperative:'bg-blue-100  text-blue-700   border border-blue-200',
    Resistant:  'bg-rose-100  text-rose-700   border border-rose-200',
  };
  return map[t] ?? 'bg-gray-100 text-gray-600 border border-gray-200';
}

function tonalityEmoji(t) {
  const m = {
    Positive:'😊', Negative:'😟', Neutral:'😐',
    Frustrated:'😤', Anxious:'😰', Cooperative:'🤝', Resistant:'🚫',
  };
  return m[t] ?? '😐';
}

function ScoreBar({ score }) {
  const s   = score ?? 0;
  const pct = Math.round(((s + 1) / 2) * 100);
  const col = s > 0.2 ? 'bg-green-500' : s < -0.2 ? 'bg-red-500' : 'bg-yellow-400';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-3 rounded-full transition-all ${col}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold w-12 text-right text-gray-700">
        {s > 0 ? '+' : ''}{s.toFixed(2)}
      </span>
    </div>
  );
}

function langBadge(lang) {
  const scripts = {
    Hindi: '🇮🇳', Tamil: '🇮🇳', Telugu: '🇮🇳', Kannada: '🇮🇳',
    Malayalam: '🇮🇳', Marathi: '🇮🇳', Gujarati: '🇮🇳', Bengali: '🇮🇳',
    English: '🌐',
  };
  const flag = scripts[lang] ?? '🌐';
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700 border border-indigo-200">
      {flag} {lang}
    </span>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function CoPilot() {
  // ── form state ────────────────────────────────────────────────
  const [customers,   setCustomers]   = useState([]);
  const [customerId,  setCustomerId]  = useState('');
  const [loanId,      setLoanId]      = useState('');
  const [audioFile,   setAudioFile]   = useState(null);
  const fileRef = useRef(null);

  // ── UI state ──────────────────────────────────────────────────
  const [phase,   setPhase]   = useState('idle');   // idle | loading | results
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState('');

  // ── history ───────────────────────────────────────────────────
  const [history, setHistory] = useState([]);
  const [histLoading, setHistLoading] = useState(false);

  // ── copy helpers ──────────────────────────────────────────────
  const [copiedIdx,    setCopiedIdx]    = useState(null);
  const [copiedAll,    setCopiedAll]    = useState(false);
  const [copiedTrans,  setCopiedTrans]  = useState(false);

  // ── Load customer list ────────────────────────────────────────
  useEffect(() => {
    api.get('/officer/search?q=')
      .then(r => setCustomers(r.data.customers ?? []))
      .catch(() => {});
  }, []);

  // ── Load history when customer changes ────────────────────────
  useEffect(() => {
    if (!customerId) { setHistory([]); return; }
    setHistLoading(true);
    api.get(`/officer/copilot/history/${customerId}`)
      .then(r => setHistory(r.data.sessions ?? []))
      .catch(() => setHistory([]))
      .finally(() => setHistLoading(false));
  }, [customerId, result]);   // re-fetch after new analysis

  // ── Submit ────────────────────────────────────────────────────
  async function handleAnalyze(e) {
    e.preventDefault();
    if (!customerId) { setError('Please select a customer.'); return; }
    if (!audioFile)  { setError('Please select an audio file.'); return; }
    setError('');
    setPhase('loading');

    const fd = new FormData();
    fd.append('customer_id', customerId);
    if (loanId.trim()) fd.append('loan_id', loanId.trim());
    fd.append('audio_file', audioFile);

    try {
      const resp = await api.post('/officer/copilot/upload-call', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      setResult(resp.data);
      setPhase('results');
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Upload failed.';
      setError(msg);
      setPhase('idle');
    }
  }

  function handleReset() {
    setPhase('idle');
    setResult(null);
    setError('');
    setAudioFile(null);
    setLoanId('');
    setCopiedIdx(null);
    setCopiedAll(false);
    setCopiedTrans(false);
    if (fileRef.current) fileRef.current.value = '';
  }

  function copyText(text, cb) {
    navigator.clipboard.writeText(text).then(() => {
      cb(true);
      setTimeout(() => cb(false), 2000);
    });
  }

  // ── Load a past session into results panel ─────────────────────
  async function loadSession(sessionId) {
    setPhase('loading');
    setError('');
    try {
      const resp = await api.get(`/officer/copilot/suggestions/${sessionId}`);
      setResult({
        call_session_id:     resp.data.call_session_id,
        customer_id:         resp.data.customer_id,
        customer_name:       customers.find(c => c.customer_id === resp.data.customer_id)?.customer_name ?? resp.data.customer_id,
        transcript:          resp.data.transcript,
        language_detected:   resp.data.language_detected,
        sentiment_score:     resp.data.sentiment_score,
        tonality:            resp.data.tonality,
        suggested_responses: resp.data.suggested_responses,
        questions_to_ask:    resp.data.questions_to_ask,
        nudges:              resp.data.nudges,
      });
      setPhase('results');
    } catch (err) {
      setError('Failed to load session.');
      setPhase('idle');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">

      {/* ── Page Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🎯 Collections Co-Pilot</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Upload a call recording → get real-time suggestions, questions &amp; nudges
          </p>
        </div>
        {phase === 'results' && (
          <button
            onClick={handleReset}
            className="text-sm px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 transition"
          >
            ← New Analysis
          </button>
        )}
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          <span className="text-lg leading-none">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          SECTION 1 — Upload Panel  (always visible unless results)
          ════════════════════════════════════════════════════════ */}
      {phase !== 'results' && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">📤 Upload Call Recording</h2>
          <form onSubmit={handleAnalyze} className="space-y-4">

            {/* Customer select */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Customer <span className="text-red-500">*</span>
              </label>
              <select
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                <option value="">— Select customer —</option>
                {customers.map(c => (
                  <option key={c.customer_id} value={c.customer_id}>
                    {c.customer_name} ({c.customer_id})
                  </option>
                ))}
              </select>
            </div>

            {/* Loan ID (optional) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Loan ID <span className="text-gray-400 font-normal">(optional — focus analysis on a specific loan)</span>
              </label>
              <input
                type="text"
                value={loanId}
                onChange={e => setLoanId(e.target.value)}
                placeholder="e.g. LOAN0012"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>

            {/* Audio file */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Audio File <span className="text-red-500">*</span>
                <span className="text-gray-400 font-normal ml-1">(mp3, wav, m4a, webm, ogg, flac)</span>
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".mp3,.wav,.m4a,.webm,.ogg,.flac,audio/*"
                onChange={e => setAudioFile(e.target.files[0] ?? null)}
                className="w-full text-sm text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
              />
              {audioFile && (
                <p className="mt-1 text-xs text-gray-400">
                  Selected: <span className="font-medium text-gray-600">{audioFile.name}</span>{' '}
                  ({(audioFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {/* Submit */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={phase === 'loading'}
                className="px-6 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {phase === 'loading' ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analysing…
                  </span>
                ) : '🔍 Analyse Call'}
              </button>
              {phase === 'loading' && (
                <span className="text-xs text-gray-400">Transcribing + generating suggestions — this may take 20–60 s…</span>
              )}
            </div>
          </form>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          RESULTS — shown only when phase === 'results'
          ════════════════════════════════════════════════════════ */}
      {phase === 'results' && result && (
        <div className="space-y-5">

          {/* ── SECTION 2 — Transcript Card ── */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-gray-800">📝 Transcript</h2>
                {langBadge(result.language_detected)}
              </div>
              <button
                onClick={() => copyText(result.transcript, setCopiedTrans)}
                className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition"
              >
                {copiedTrans ? '✅ Copied' : '📋 Copy'}
              </button>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto bg-gray-50 rounded-xl p-4">
              {result.transcript}
            </p>
          </div>

          {/* ── SECTION 3 — Sentiment Row ── */}
          <div className="grid grid-cols-2 gap-4">
            {/* Score */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Sentiment Score</p>
              <ScoreBar score={result.sentiment_score} />
              <p className="mt-2 text-xs text-gray-400">
                {result.sentiment_score > 0.2
                  ? 'Customer appears open and cooperative.'
                  : result.sentiment_score < -0.2
                  ? 'Customer is distressed or resistant — handle carefully.'
                  : 'Neutral tone — build rapport before discussing repayment.'}
              </p>
            </div>
            {/* Tonality */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Tonality</p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-3xl">{tonalityEmoji(result.tonality)}</span>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${tonalityBadge(result.tonality)}`}>
                  {result.tonality}
                </span>
              </div>
              <p className="mt-2 text-xs text-gray-400">
                Customer ID: {result.customer_id} &nbsp;|&nbsp; {result.customer_name}
              </p>
            </div>
          </div>

          {/* ── SECTION 4 — Suggested Responses ── */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-gray-800">💬 Suggested Responses</h2>
              <button
                onClick={() => copyText(
                  (result.suggested_responses ?? []).map((r, i) => `${i + 1}. ${r}`).join('\n'),
                  setCopiedAll
                )}
                className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition"
              >
                {copiedAll ? '✅ Copied All' : '📋 Copy All'}
              </button>
            </div>
            <div className="space-y-3">
              {(result.suggested_responses ?? []).map((resp, idx) => (
                <div key={idx} className="flex items-start gap-3 p-4 rounded-xl bg-indigo-50 border border-indigo-100">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                    {idx + 1}
                  </span>
                  <p className="flex-1 text-sm text-gray-700 leading-relaxed">{resp}</p>
                  <button
                    onClick={() => {
                      copyText(resp, (v) => {
                        if (v) setCopiedIdx(idx);
                        else if (copiedIdx === idx) setCopiedIdx(null);
                      });
                    }}
                    className="flex-shrink-0 text-xs px-2 py-0.5 rounded border border-indigo-200 text-indigo-500 hover:bg-indigo-100 transition"
                  >
                    {copiedIdx === idx ? '✅' : '📋'}
                  </button>
                </div>
              ))}
              {(!result.suggested_responses || result.suggested_responses.length === 0) && (
                <p className="text-sm text-gray-400 italic">No suggestions generated.</p>
              )}
            </div>
          </div>

          {/* ── SECTION 5 — Questions + Nudges (two columns) ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Root-Cause Questions */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">❓ Root-Cause Questions</h2>
              <ol className="space-y-2 list-none">
                {(result.questions_to_ask ?? []).map((q, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="flex-shrink-0 text-indigo-400 font-bold mt-0.5">{i + 1}.</span>
                    <span>{q}</span>
                  </li>
                ))}
                {(!result.questions_to_ask || result.questions_to_ask.length === 0) && (
                  <li className="text-sm text-gray-400 italic">No questions generated.</li>
                )}
              </ol>
            </div>

            {/* Nudges & Alerts */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">🔔 Nudges &amp; Alerts</h2>
              <ul className="space-y-2">
                {(result.nudges ?? []).map((n, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="flex-shrink-0 text-orange-400 mt-0.5">●</span>
                    <span className="text-gray-700">{n}</span>
                  </li>
                ))}
                {(!result.nudges || result.nudges.length === 0) && (
                  <li className="text-sm text-gray-400 italic">No nudges generated.</li>
                )}
              </ul>
            </div>
          </div>

        </div>  /* end results */
      )}

      {/* ════════════════════════════════════════════════════════
          Past Sessions for selected customer
          ════════════════════════════════════════════════════════ */}
      {customerId && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-3">🕐 Past Co-Pilot Sessions</h2>

          {histLoading ? (
            <div className="flex justify-center py-4">
              <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No past sessions for this customer.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                    <th className="pb-2 font-medium">Date / Time</th>
                    <th className="pb-2 font-medium">Language</th>
                    <th className="pb-2 font-medium">Sentiment</th>
                    <th className="pb-2 font-medium">Tonality</th>
                    <th className="pb-2 font-medium">Loan</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {history.map(s => (
                    <tr key={s.call_session_id} className="hover:bg-gray-50 transition">
                      <td className="py-2 pr-3 text-gray-700 whitespace-nowrap">
                        {s.upload_time ? new Date(s.upload_time).toLocaleString('en-IN', {
                          day: '2-digit', month: 'short', year: 'numeric',
                          hour: '2-digit', minute: '2-digit',
                        }) : '—'}
                      </td>
                      <td className="py-2 pr-3">
                        {langBadge(s.language_detected ?? 'English')}
                      </td>
                      <td className="py-2 pr-3">
                        {s.sentiment_score !== null && s.sentiment_score !== undefined
                          ? <span className={`font-semibold ${s.sentiment_score > 0.2 ? 'text-green-600' : s.sentiment_score < -0.2 ? 'text-red-600' : 'text-yellow-600'}`}>
                              {s.sentiment_score > 0 ? '+' : ''}{Number(s.sentiment_score).toFixed(2)}
                            </span>
                          : '—'}
                      </td>
                      <td className="py-2 pr-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${tonalityBadge(s.tonality ?? 'Neutral')}`}>
                          {s.tonality ?? '—'}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-gray-500">
                        {s.loan_id ?? '—'}
                      </td>
                      <td className="py-2">
                        <button
                          onClick={() => loadSession(s.call_session_id)}
                          className="text-xs px-3 py-1 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100 hover:bg-indigo-100 transition font-medium"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
