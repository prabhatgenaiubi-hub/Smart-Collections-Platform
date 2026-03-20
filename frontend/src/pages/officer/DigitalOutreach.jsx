/**
 * DigitalOutreach.jsx
 * ===================
 * Bank Officer — Multichannel Personalised Digital Outreach Agent
 *
 * Flow (Human-in-the-Loop):
 *   1. Officer picks a customer + loan
 *   2. Selects channel (WhatsApp / Email) and objective
 *   3. Clicks "Generate Draft" → AI builds personalised message
 *   4. Officer reads and EDITS the draft freely (HITL textarea)
 *   5. Officer clicks "Send" → backend sends via selected channel
 *   6. Status badge shown; history log updates below
 *
 * Channels supported (MVP): WhatsApp, Email
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../../api';

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const CHANNELS = [
  { value: 'whatsapp', label: '💬 WhatsApp', icon: '💬' },
  { value: 'email',    label: '📧 Email',    icon: '📧' },
];

const OBJECTIVES = [
  { value: 'reminder',              label: '🔔 Payment Reminder' },
  { value: 'overdue',               label: '⚠️ Overdue Notice' },
  { value: 'grace_followup',        label: '⏱ Grace Period Follow-up' },
  { value: 'restructure_followup',  label: '🔄 Restructure Follow-up' },
];

const STATUS_STYLES = {
  sent       : 'bg-green-100  text-green-800  border-green-200',
  mock_sent  : 'bg-yellow-100 text-yellow-800 border-yellow-200',
  failed     : 'bg-red-100    text-red-800    border-red-200',
};

const STATUS_LABELS = {
  sent       : '✅ Sent',
  mock_sent  : '🟡 Mock Sent (no credentials)',
  failed     : '❌ Failed',
};

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function DigitalOutreach() {
  // ── Customer / loan search ───────────────────────────────────────────────
  const [searchQuery,   setSearchQuery]   = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching,     setSearching]     = useState(false);

  // ── Selected customer + loan ─────────────────────────────────────────────
  const [selectedCustomer, setSelectedCustomer] = useState(null);   // full customer obj
  const [selectedLoan,     setSelectedLoan]     = useState(null);   // full loan obj

  // ── Form state ───────────────────────────────────────────────────────────
  const [channel,   setChannel]   = useState('whatsapp');
  const [objective, setObjective] = useState('reminder');

  // ── Draft / HITL ─────────────────────────────────────────────────────────
  const [generating,    setGenerating]    = useState(false);
  const [generatedData, setGeneratedData] = useState(null);   // GenerateResponse
  const [editedMessage, setEditedMessage] = useState('');
  const [editedSubject, setEditedSubject] = useState('');

  // ── Send ─────────────────────────────────────────────────────────────────
  const [sending,       setSending]       = useState(false);
  const [sendResult,    setSendResult]    = useState(null);   // SendResponse
  const [sendError,     setSendError]     = useState('');

  // ── History ──────────────────────────────────────────────────────────────
  const [history,       setHistory]       = useState([]);
  const [loadingHistory,setLoadingHistory]= useState(false);

  // ─────────────────────────────────────────────
  // Search customers
  // ─────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    const q = searchQuery.trim();
    if (!q) return;
    setSearching(true);
    setSearchResults([]);
    try {
      // /officer/search accepts: customer_id, name, loan_id (OR logic)
      // Send all three so "CUST001", a name, or a loan ID all work
      const res = await api.get('/officer/search', {
        params: { customer_id: q, name: q },
      });

      // Response: { results: [ loanSummary, ... ], total: N }
      // Each loanSummary has: customer_id, customer_name, loan_id, ...
      // Group by customer so we display one row per customer
      const loanRows = res.data.results || [];
      const customerMap = {};
      loanRows.forEach((row) => {
        if (!customerMap[row.customer_id]) {
          customerMap[row.customer_id] = {
            customer_id   : row.customer_id,
            customer_name : row.customer_name,
          };
        }
      });
      setSearchResults(Object.values(customerMap));
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setSearching(false);
    }
  }, [searchQuery]);

  const handleSelectCustomer = async (customerStub) => {
    // Fetch full customer profile + loans from /officer/customers/{id}
    try {
      const res = await api.get(`/officer/customers/${customerStub.customer_id}`);
      const data = res.data;
      // Merge customer fields + loans into a single object for convenience
      const fullCustomer = {
        ...data.customer,
        loans: data.loans || [],
      };
      setSelectedCustomer(fullCustomer);
    } catch (err) {
      console.error('Failed to load customer:', err);
      // Fallback: use stub without loans
      setSelectedCustomer({ ...customerStub, loans: [] });
    }
    setSelectedLoan(null);
    setGeneratedData(null);
    setEditedMessage('');
    setEditedSubject('');
    setSendResult(null);
    setSendError('');
    setSearchResults([]);
    setSearchQuery('');
    fetchHistory(customerStub.customer_id);
  };

  const handleSelectLoan = (loan) => {
    setSelectedLoan(loan);
    setGeneratedData(null);
    setEditedMessage('');
    setEditedSubject('');
    setSendResult(null);
    setSendError('');
  };

  // ─────────────────────────────────────────────
  // Load outreach history
  // ─────────────────────────────────────────────
  const fetchHistory = async (customerId) => {
    setLoadingHistory(true);
    try {
      const res = await api.get(`/outreach/history/${customerId}`);
      setHistory(Array.isArray(res.data) ? res.data : []);
    } catch {
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // ─────────────────────────────────────────────
  // Generate draft
  // ─────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!selectedCustomer || !selectedLoan) return;
    setGenerating(true);
    setGeneratedData(null);
    setEditedMessage('');
    setEditedSubject('');
    setSendResult(null);
    setSendError('');

    try {
      const res = await api.post('/outreach/generate', {
        customer_id : selectedCustomer.customer_id,
        loan_id     : selectedLoan.loan_id,
        channel,
        objective,
      });
      setGeneratedData(res.data);
      setEditedMessage(res.data.ai_draft || '');
      setEditedSubject(res.data.subject  || '');
    } catch (err) {
      setSendError(
        err.response?.data?.detail || 'Draft generation failed. Please try again.'
      );
    } finally {
      setGenerating(false);
    }
  };

  // ─────────────────────────────────────────────
  // Send (HITL — uses editedMessage, not ai_draft)
  // ─────────────────────────────────────────────
  const handleSend = async () => {
    if (!generatedData || !editedMessage.trim()) return;
    setSending(true);
    setSendResult(null);
    setSendError('');

    try {
      const res = await api.post('/outreach/send', {
        customer_id   : generatedData.customer_id,
        loan_id       : generatedData.loan_id,
        channel       : generatedData.channel,
        contact       : generatedData.contact,
        ai_draft      : generatedData.ai_draft,
        final_message : editedMessage,
        subject       : editedSubject || undefined,
        objective     : generatedData.objective,
      });
      setSendResult(res.data);
      // refresh history
      fetchHistory(generatedData.customer_id);
    } catch (err) {
      setSendError(
        err.response?.data?.detail || 'Send failed. Please try again.'
      );
    } finally {
      setSending(false);
    }
  };

  // ─────────────────────────────────────────────
  // Reset form
  // ─────────────────────────────────────────────
  const handleReset = () => {
    setSelectedCustomer(null);
    setSelectedLoan(null);
    setGeneratedData(null);
    setEditedMessage('');
    setEditedSubject('');
    setSendResult(null);
    setSendError('');
    setHistory([]);
    setSearchQuery('');
    setSearchResults([]);
  };

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────
  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* ── Page Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            📡 Digital Outreach Agent
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Generate AI-personalised messages, review &amp; edit, then send via WhatsApp or Email.
          </p>
        </div>
        {selectedCustomer && (
          <button
            onClick={handleReset}
            className="text-sm text-slate-500 hover:text-red-600 transition-colors underline"
          >
            ↩ Start over
          </button>
        )}
      </div>

      {/* ── Step 1: Customer Search ── */}
      <Section title="Step 1 — Select Customer" step={1}>
        {!selectedCustomer ? (
          <>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search by name, ID or phone…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="flex-1 border border-slate-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearch}
                disabled={searching || !searchQuery.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {searching ? 'Searching…' : 'Search'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <ul className="mt-3 border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-56 overflow-y-auto">
                {searchResults.map((c) => (
                  <li key={c.customer_id}>
                    <button
                      onClick={() => handleSelectCustomer(c)}
                      className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors"
                    >
                      <p className="text-sm font-semibold text-slate-800">{c.customer_name}</p>
                      <p className="text-xs text-slate-500">
                        {c.customer_id}
                        {c.mobile_number && <>&nbsp;·&nbsp;{c.mobile_number}</>}
                        {c.email_id && <>&nbsp;·&nbsp;{c.email_id}</>}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {searchResults.length === 0 && searchQuery && !searching && (
              <p className="mt-2 text-sm text-slate-400">No results found.</p>
            )}
          </>
        ) : (
          <CustomerCard customer={selectedCustomer} />
        )}
      </Section>

      {/* ── Step 2: Loan + Channel + Objective ── */}
      {selectedCustomer && (
        <Section title="Step 2 — Select Loan, Channel &amp; Objective" step={2}>
          {/* Loans */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Select Loan
            </label>
            {(selectedCustomer.loans || []).length === 0 ? (
              <p className="text-sm text-slate-400">No loans found for this customer.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {(selectedCustomer.loans || []).map((loan) => (
                  <button
                    key={loan.loan_id}
                    onClick={() => handleSelectLoan(loan)}
                    className={`border rounded-lg p-3 text-left transition-all ${
                      selectedLoan?.loan_id === loan.loan_id
                        ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-300'
                        : 'border-slate-200 hover:border-blue-300 hover:bg-blue-50'
                    }`}
                  >
                    <p className="text-sm font-semibold text-slate-800">{loan.loan_type}</p>
                    <p className="text-xs text-slate-500">
                      ID: {loan.loan_id.slice(0, 8)}…
                    </p>
                    <p className="text-xs text-slate-600 mt-1">
                      EMI ₹{loan.emi_amount?.toLocaleString('en-IN')}
                      &nbsp;·&nbsp; DPD: {loan.days_past_due} days
                    </p>
                    <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      loan.risk_segment === 'High'   ? 'bg-red-100 text-red-700'    :
                      loan.risk_segment === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-green-100 text-green-700'
                    }`}>
                      {loan.risk_segment} Risk
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Channel */}
          <div className="space-y-2 mt-4">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Channel
            </label>
            <div className="flex gap-3">
              {CHANNELS.map((ch) => (
                <button
                  key={ch.value}
                  onClick={() => { setChannel(ch.value); setGeneratedData(null); }}
                  className={`flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium transition-all ${
                    channel === ch.value
                      ? 'border-blue-500 bg-blue-600 text-white'
                      : 'border-slate-200 text-slate-600 hover:border-blue-400 hover:bg-blue-50'
                  }`}
                >
                  {ch.icon} {ch.label.split(' ')[1]}
                </button>
              ))}
            </div>
          </div>

          {/* Objective */}
          <div className="space-y-2 mt-4">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Objective
            </label>
            <div className="grid grid-cols-2 gap-2">
              {OBJECTIVES.map((obj) => (
                <button
                  key={obj.value}
                  onClick={() => { setObjective(obj.value); setGeneratedData(null); }}
                  className={`px-3 py-2 border rounded-lg text-sm font-medium text-left transition-all ${
                    objective === obj.value
                      ? 'border-blue-500 bg-blue-600 text-white'
                      : 'border-slate-200 text-slate-600 hover:border-blue-400 hover:bg-blue-50'
                  }`}
                >
                  {obj.label}
                </button>
              ))}
            </div>
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={!selectedLoan || generating}
            className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <><Spinner /> Generating AI Draft…</>
            ) : (
              '✨ Generate AI Draft'
            )}
          </button>
        </Section>
      )}

      {/* ── Step 3: Review & Edit (HITL) + Send ── */}
      {generatedData && (
        <Section title="Step 3 — Review, Edit &amp; Send" step={3}>

          {/* Contact info */}
          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-sm">
            <span className="font-medium text-slate-600">Sending to:</span>
            <span className="font-semibold text-slate-800">{generatedData.contact}</span>
            <span className="ml-auto px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 capitalize">
              {generatedData.channel}
            </span>
          </div>

          {/* Email subject (only for email) */}
          {generatedData.channel === 'email' && (
            <div className="mt-3 space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Email Subject
              </label>
              <input
                type="text"
                value={editedSubject}
                onChange={(e) => setEditedSubject(e.target.value)}
                placeholder="Enter email subject…"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {/* HITL message editor */}
          <div className="mt-3 space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Message  <span className="text-blue-600 font-normal normal-case">(you can edit)</span>
              </label>
              {editedMessage !== generatedData.ai_draft && (
                <span className="text-xs text-amber-600 font-medium">✏️ Edited from AI draft</span>
              )}
            </div>
            <textarea
              value={editedMessage}
              onChange={(e) => setEditedMessage(e.target.value)}
              rows={8}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              placeholder="AI draft will appear here for you to review and edit…"
            />
            <p className="text-xs text-slate-400">
              {editedMessage.length} characters &nbsp;·&nbsp;
              {editedMessage === generatedData.ai_draft
                ? 'No changes from AI draft'
                : 'Modified — original AI draft is preserved in audit log'}
            </p>
          </div>

          {/* Original AI draft (collapsible peek) */}
          {editedMessage !== generatedData.ai_draft && (
            <details className="mt-2 text-xs">
              <summary className="cursor-pointer text-slate-500 hover:text-slate-700">
                View original AI draft
              </summary>
              <pre className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded-lg whitespace-pre-wrap text-slate-600 font-mono">
                {generatedData.ai_draft}
              </pre>
            </details>
          )}

          {/* Send button + result */}
          {!sendResult ? (
            <button
              onClick={handleSend}
              disabled={sending || !editedMessage.trim()}
              className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {sending ? (
                <><Spinner /> Sending…</>
              ) : (
                `📤 Send via ${generatedData.channel === 'whatsapp' ? 'WhatsApp' : 'Email'}`
              )}
            </button>
          ) : (
            <div className={`mt-4 flex items-start gap-3 p-4 border rounded-lg ${STATUS_STYLES[sendResult.status] || ''}`}>
              <div className="flex-1">
                <p className="text-sm font-semibold">{STATUS_LABELS[sendResult.status] || sendResult.status}</p>
                <p className="text-xs mt-0.5">{sendResult.message}</p>
                {sendResult.officer_edited && (
                  <p className="text-xs mt-1 opacity-75">ℹ️ Message was edited by officer before sending.</p>
                )}
              </div>
              <button
                onClick={() => {
                  setGeneratedData(null);
                  setEditedMessage('');
                  setEditedSubject('');
                  setSendResult(null);
                }}
                className="text-xs underline opacity-75 hover:opacity-100"
              >
                New message
              </button>
            </div>
          )}

          {sendError && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              ⚠️ {sendError}
            </div>
          )}
        </Section>
      )}

      {/* ── Outreach History ── */}
      {selectedCustomer && (
        <Section title="Outreach History" step={null}>
          {loadingHistory ? (
            <p className="text-sm text-slate-400">Loading history…</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-slate-400">No outreach history for this customer yet.</p>
          ) : (
            <div className="space-y-3">
              {history.map((item) => (
                <div
                  key={item.event_id}
                  className="border border-slate-200 rounded-lg p-4 bg-white space-y-1"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[item.status] || 'bg-slate-100 text-slate-700'}`}>
                      {STATUS_LABELS[item.status] || item.status}
                    </span>
                    <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full capitalize">
                      {item.channel}
                    </span>
                    <span className="text-xs text-slate-500 capitalize">{item.objective.replace('_', ' ')}</span>
                    {item.officer_edited && (
                      <span className="text-xs text-amber-600 font-medium">✏️ Edited</span>
                    )}
                    <span className="ml-auto text-xs text-slate-400">
                      {new Date(item.sent_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">To: {item.contact}</p>
                  <details className="text-xs mt-1">
                    <summary className="cursor-pointer text-slate-400 hover:text-slate-600">
                      View message
                    </summary>
                    <pre className="mt-1 p-2 bg-slate-50 rounded whitespace-pre-wrap text-slate-600 font-mono">
                      {item.final_message}
                    </pre>
                  </details>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function Section({ title, step, children }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100 bg-slate-50">
        {step && (
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
            {step}
          </span>
        )}
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function CustomerCard({ customer }) {
  return (
    <div className="flex items-center gap-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
      <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center text-lg font-bold flex-shrink-0">
        {customer.customer_name?.[0]?.toUpperCase() || '?'}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 truncate">{customer.customer_name}</p>
        <p className="text-xs text-slate-500">
          {customer.customer_id} &nbsp;·&nbsp; {customer.mobile_number}
        </p>
        <p className="text-xs text-slate-500 truncate">{customer.email_id}</p>
      </div>
      <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">Selected</span>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}
