import { useEffect, useState } from 'react';
import api from '../../api';
import LoanChat from '../../components/LoanChat';

const statusBadge = (status) => {
  const map = {
    Approved: 'bg-green-100 text-green-700',
    Rejected: 'bg-red-100 text-red-700',
    Pending:  'bg-yellow-100 text-yellow-700',
    None:     'bg-gray-100 text-gray-500',
  };
  return map[status] || map['None'];
};

const riskBadge = (risk) => {
  const map = {
    High:   'bg-red-100 text-red-700',
    Medium: 'bg-yellow-100 text-yellow-700',
    Low:    'bg-green-100 text-green-700',
  };
  return map[risk] || 'bg-gray-100 text-gray-500';
};

export default function CustomerLoans() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState({});
  const [message, setMessage] = useState('');
  const [selectedLoan, setSelectedLoan] = useState(null); // for modal
  const [chatLoan,     setChatLoan]     = useState(null); // for inline loan chat
  const [bounceRisks, setBounceRisks] = useState({}); // { loanId: riskData }
  const [loadingRisks, setLoadingRisks] = useState(true);
  const [showAutoPayModal, setShowAutoPayModal] = useState(null); // loanId for modal

  useEffect(() => {
    api.get('/customer/loans')
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Fetch bounce risk for all loans
  useEffect(() => {
    if (!data?.loans) return;
    
    const fetchRisks = async () => {
      const risks = {};
      for (const loan of data.loans) {
        try {
          const response = await api.get(`/bounce-prevention/loans/${loan.loan_id}/risk`);
          risks[loan.loan_id] = response.data;
        } catch (err) {
          console.error(`Failed to fetch bounce risk for ${loan.loan_id}:`, err);
          risks[loan.loan_id] = null;
        }
      }
      setBounceRisks(risks);
      setLoadingRisks(false);
    };
    
    fetchRisks();
  }, [data?.loans]);

  const submitRequest = async (loanId, type) => {
    setSubmitting(s => ({ ...s, [loanId + type]: true }));
    setMessage('');
    try {
      const endpoint = type === 'grace' ? '/grace/request' : '/restructure/request';
      await api.post(endpoint, { loan_id: loanId });
      setMessage(`✅ ${type === 'grace' ? 'Grace' : 'Restructure'} request submitted successfully!`);
      // Refresh
      const r = await api.get('/customer/loans');
      setData(r.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail.message : detail;
      setMessage(`❌ ${msg || 'Request failed.'}`);
    } finally {
      setSubmitting(s => ({ ...s, [loanId + type]: false }));
    }
  };

  const handleEnableAutoPay = async (loanId, enrollmentData) => {
    setSubmitting(s => ({ ...s, [loanId + 'autopay']: true }));
    setMessage('');
    try {
      await api.post(`/bounce-prevention/loans/${loanId}/enable-autopay`, enrollmentData);
      setMessage('✅ Auto-Pay enabled successfully! Your EMIs will be auto-debited.');
      
      // Refresh bounce risk data
      const response = await api.get(`/bounce-prevention/loans/${loanId}/risk`, { params: { recalculate: true } });
      setBounceRisks(prev => ({ ...prev, [loanId]: response.data }));
      setShowAutoPayModal(null);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail.message : detail;
      setMessage(`❌ ${msg || 'Auto-Pay enrollment failed.'}`);
    } finally {
      setSubmitting(s => ({ ...s, [loanId + 'autopay']: false }));
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Your Loans</h1>
        <span className="text-sm text-gray-500">{data?.total || 0} loan(s)</span>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-xl text-sm font-medium ${
          message.startsWith('✅') ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message}
        </div>
      )}

      {data?.loans?.length === 0 && (
        <div className="bg-white rounded-2xl shadow p-8 text-center text-gray-400">
          No loans found.
        </div>
      )}

      <div className="space-y-4">
        {data?.loans?.map((loan) => (
          <div key={loan.loan_id} className="bg-white rounded-2xl shadow hover:shadow-md transition-shadow">
            <div className="p-5">
              {/* Top row */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <button
                    onClick={() => setSelectedLoan(loan)}
                    className="text-blue-600 font-bold text-lg hover:underline"
                  >
                    {loan.loan_id}
                  </button>
                  <span className="ml-3 text-sm text-gray-500">{loan.loan_type}</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${riskBadge(loan.risk_segment)}`}>
                  {loan.risk_segment} Risk
                </span>
              </div>

              {/* Details grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <Detail label="Outstanding"   value={`₹${loan.outstanding_balance?.toLocaleString('en-IN')}`} />
                <Detail label="EMI Amount"    value={`₹${loan.emi_amount?.toLocaleString('en-IN')}`} />
                <Detail label="Next EMI Due"  value={loan.emi_due_date} />
                <Detail label="Days Past Due" value={loan.days_past_due} highlight={loan.days_past_due > 0} />
              </div>

              {/* Bounce Risk Section */}
              {!loadingRisks && bounceRisks[loan.loan_id] && (
                <div className="mb-4 p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-100">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-semibold text-gray-600">EMI Bounce Risk:</span>
                      <BounceRiskBadge risk={bounceRisks[loan.loan_id]} />
                      {bounceRisks[loan.loan_id].auto_pay_enabled && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-semibold flex items-center gap-1">
                          ✓ Auto-Pay Active
                        </span>
                      )}
                    </div>
                    {!bounceRisks[loan.loan_id].auto_pay_enabled && (
                      <button
                        onClick={() => setShowAutoPayModal(loan.loan_id)}
                        disabled={submitting[loan.loan_id + 'autopay']}
                        className="px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-300 disabled:to-gray-300 text-white text-xs font-semibold rounded-lg transition-all shadow-sm hover:shadow"
                      >
                        🔒 Enable Auto-Pay
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Status + Actions */}
              <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-gray-100">
                <StatusPill label="Grace"       status={loan.grace_status} />
                <StatusPill label="Restructure" status={loan.restructure_status} />

                <div className="ml-auto flex gap-2">
                  <button
                    onClick={() => submitRequest(loan.loan_id, 'grace')}
                    disabled={submitting[loan.loan_id + 'grace'] || loan.grace_status === 'Pending'}
                    className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-300 text-white text-xs font-semibold rounded-xl transition-colors"
                  >
                    {submitting[loan.loan_id + 'grace'] ? '...' : '⏱ Grace Request'}
                  </button>
                  <button
                    onClick={() => submitRequest(loan.loan_id, 'restructure')}
                    disabled={submitting[loan.loan_id + 'restructure'] || loan.restructure_status === 'Pending'}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white text-xs font-semibold rounded-xl transition-colors"
                  >
                    {submitting[loan.loan_id + 'restructure'] ? '...' : '🔄 Restructure'}
                  </button>
                  <button
                    onClick={() => setSelectedLoan(loan)}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
                  >
                    View Details →
                  </button>
                  <button
                    onClick={() => setChatLoan(loan)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-xl transition-colors"
                  >
                    💬 Chat
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Loan Detail Modal */}
      {selectedLoan && (
        <LoanDetailModal loan={selectedLoan} onClose={() => setSelectedLoan(null)} />
      )}

      {/* Loan-scoped AI Chat slide-over */}
      {chatLoan && (
        <LoanChat loan={chatLoan} onClose={() => setChatLoan(null)} />
      )}

      {/* Auto-Pay Enrollment Modal */}
      {showAutoPayModal && (
        <AutoPayModal
          loan={data.loans.find(l => l.loan_id === showAutoPayModal)}
          onClose={() => setShowAutoPayModal(null)}
          onSubmit={handleEnableAutoPay}
          submitting={submitting[showAutoPayModal + 'autopay']}
        />
      )}
    </div>
  );
}

function Detail({ label, value, highlight }) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`font-semibold text-sm ${highlight ? 'text-red-600' : 'text-gray-800'}`}>{value ?? '—'}</p>
    </div>
  );
}

function StatusPill({ label, status }) {
  const map = {
    Approved: 'bg-green-100 text-green-700',
    Rejected: 'bg-red-100 text-red-700',
    Pending:  'bg-yellow-100 text-yellow-700',
    None:     'bg-gray-100 text-gray-400',
    Active:   'bg-blue-100 text-blue-700',
  };
  return (
    <span className={`text-xs px-3 py-1 rounded-full font-medium ${map[status] || map['None']}`}>
      {label}: {status}
    </span>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
    </div>
  );
}

function LoanDetailModal({ loan, onClose }) {
  const [payments, setPayments] = useState([]);
  const [loadingPay, setLoadingPay] = useState(true);

  useEffect(() => {
    api.get(`/customer/loans/${loan.loan_id}/payments`)
      .then(r => setPayments(r.data.payments || []))
      .catch(console.error)
      .finally(() => setLoadingPay(false));
  }, [loan.loan_id]);

  const riskMap = {
    High:   'bg-red-100 text-red-700',
    Medium: 'bg-yellow-100 text-yellow-700',
    Low:    'bg-green-100 text-green-700',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-800">Loan Details</h2>
            <span className="font-bold text-blue-600">{loan.loan_id}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${riskMap[loan.risk_segment] || 'bg-gray-100 text-gray-500'}`}>
              {loan.risk_segment} Risk
            </span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">✕</button>
        </div>

        {/* Scrollable Body */}
        <div className="overflow-y-auto p-6 space-y-6">
          {/* Loan Summary */}
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-3 font-semibold uppercase tracking-wide">Loan Summary</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Detail label="Loan Type"      value={loan.loan_type} />
              <Detail label="Loan Amount"    value={`₹${loan.loan_amount?.toLocaleString('en-IN')}`} />
              <Detail label="Outstanding"    value={`₹${loan.outstanding_balance?.toLocaleString('en-IN')}`} />
              <Detail label="EMI Amount"     value={`₹${loan.emi_amount?.toLocaleString('en-IN')}`} />
              <Detail label="Next EMI Due"   value={loan.emi_due_date} />
              <Detail label="Days Past Due"  value={loan.days_past_due} highlight={loan.days_past_due > 0} />
              <Detail label="Interest Rate"  value={`${loan.interest_rate}%`} />
              <Detail label="Loan Status"    value={loan.loan_status} />
            </div>
          </div>

          {/* Status Pills */}
          <div className="flex flex-wrap gap-2">
            <StatusPill label="Grace"       status={loan.grace_status} />
            <StatusPill label="Restructure" status={loan.restructure_status} />
          </div>

          {/* Payment History */}
          <div>
            <p className="text-xs text-gray-500 mb-3 font-semibold uppercase tracking-wide">Payment History</p>
            {loadingPay ? (
              <div className="flex justify-center py-6">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
              </div>
            ) : payments.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">No payment records found.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-100">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Date', 'Amount', 'Status', 'Method', 'Late Fees'].map(h => (
                        <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {payments.map((p, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-600">{p.payment_date}</td>
                        <td className="px-4 py-2 font-semibold text-gray-800">₹{p.payment_amount?.toLocaleString('en-IN')}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            p.payment_status === 'On Time' ? 'bg-green-100 text-green-700'
                            : p.payment_status === 'Late' ? 'bg-red-100 text-red-700'
                            : 'bg-gray-100 text-gray-500'
                          }`}>{p.payment_status}</span>
                        </td>
                        <td className="px-4 py-2 text-gray-600">{p.payment_method || '—'}</td>
                        <td className="px-4 py-2 text-gray-600">₹{p.late_fee?.toLocaleString('en-IN') || '0'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-sm font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function BounceRiskBadge({ risk }) {
  if (!risk) return null;
  
  const levelMap = {
    High:   { bg: 'bg-red-100', text: 'text-red-700', icon: '🚨', border: 'border-red-200' },
    Medium: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: '⚠️', border: 'border-yellow-200' },
    Low:    { bg: 'bg-green-100', text: 'text-green-700', icon: '✅', border: 'border-green-200' },
  };

  const style = levelMap[risk.risk_level] || levelMap.Low;
  
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${style.bg} ${style.text} ${style.border}`}>
      <span className="text-sm">{style.icon}</span>
      <div className="flex flex-col">
        <span className="text-xs font-bold leading-tight">{risk.risk_level} Risk</span>
        <span className="text-[10px] leading-tight opacity-80">
          {(risk.next_emi_bounce_probability * 100).toFixed(0)}% bounce probability
        </span>
      </div>
    </div>
  );
}

function AutoPayModal({ loan, onClose, onSubmit, submitting }) {
  const [formData, setFormData] = useState({
    bank_account_number: '',
    ifsc_code: '',
    max_amount: loan?.emi_amount || 0,
    activation_channel: 'app'
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(loan.loan_id, formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-800">Enable Auto-Pay</h2>
              <p className="text-sm text-gray-500 mt-1">Never miss an EMI payment</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">✕</button>
          </div>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-blue-900">Loan: {loan?.loan_id}</p>
            <p className="text-xs text-blue-700 mt-1">EMI Amount: ₹{loan?.emi_amount?.toLocaleString('en-IN')}</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Bank Account Number</label>
            <input
              type="text"
              required
              maxLength={16}
              pattern="[0-9]+"
              placeholder="Enter 10-16 digit account number"
              value={formData.bank_account_number}
              onChange={(e) => setFormData({ ...formData, bank_account_number: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">IFSC Code</label>
            <input
              type="text"
              required
              maxLength={11}
              pattern="[A-Z]{4}0[A-Z0-9]{6}"
              placeholder="e.g., SBIN0001234"
              value={formData.ifsc_code}
              onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
              className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Maximum Debit Amount</label>
            <input
              type="number"
              required
              min={loan?.emi_amount}
              value={formData.max_amount}
              onChange={(e) => setFormData({ ...formData, max_amount: parseFloat(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">Recommended: EMI amount or higher</p>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <p className="text-xs font-semibold text-green-900 mb-2">Benefits of Auto-Pay (e-NACH):</p>
            <ul className="text-xs text-green-700 space-y-1">
              <li>✓ Never miss an EMI payment</li>
              <li>✓ No late payment charges</li>
              <li>✓ Maintain good credit score</li>
              <li>✓ Hassle-free automatic debits</li>
            </ul>
          </div>

          {/* Footer */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-300 disabled:to-gray-300 text-white rounded-xl font-semibold transition-all"
            >
              {submitting ? 'Enabling...' : '🔒 Enable Auto-Pay'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}