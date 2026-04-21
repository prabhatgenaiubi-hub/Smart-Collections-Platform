import { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer
} from 'recharts';
import api from '../../api';

export default function OfficerDashboard() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/officer/dashboard')
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (!data)   return <div className="text-red-500">Failed to load dashboard.</div>;

  const { summary, charts } = data;

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Portfolio Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Collections Intelligence Overview</p>
        </div>
        <span className="text-xs text-gray-400">
          {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}
        </span>
      </div>

      {/* KPI Cards Row 1 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Total Borrowers"
          value={summary.total_borrowers}
          icon="👥"
          color="blue"
        />
        <KPICard
          label="High Risk Accounts"
          value={summary.high_risk_accounts}
          icon="🔴"
          color="red"
          sub={`of ${summary.total_loans} loans`}
        />
        <KPICard
          label="Expected Recovery"
          value={`₹${(summary.expected_recovery / 100000).toFixed(1)}L`}
          icon="💰"
          color="green"
        />
        <KPICard
          label="Self Cure Rate"
          value={`${summary.self_cure_rate}%`}
          icon="📈"
          color="purple"
        />
      </div>

      {/* KPI Cards Row 2 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Total Outstanding"
          value={`₹${(summary.total_outstanding / 100000).toFixed(1)}L`}
          icon="🏦"
          color="blue"
        />
        <KPICard
          label="Portfolio NPV"
          value={`₹${(summary.total_npv / 100000).toFixed(1)}L`}
          icon="📊"
          color="green"
        />
        <KPICard
          label="Grace Requests"
          value={summary.pending_grace_requests}
          icon="⏱"
          color="yellow"
          sub="Pending"
          href="/officer/grace"
        />
        <KPICard
          label="Restructure Requests"
          value={summary.pending_restructure_requests}
          icon="🔄"
          color="purple"
          sub="Pending"
          href="/officer/restructure"
        />
      </div>

      {/* Bounce Prevention - Single Consolidated Card */}
      <BounceRiskCard summary={summary} />

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Risk Distribution Pie */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Risk Distribution</h2>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={charts.risk_distribution}
                dataKey="count"
                nameKey="segment"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ segment, count }) => `${segment}: ${count}`}
              >
                {charts.risk_distribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Recovery Strategy Bar */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Recovery Strategy Mix</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart
              data={charts.recovery_strategy_mix}
              layout="vertical"
              margin={{ left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="strategy" tick={{ fontSize: 10 }} width={140} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Portfolio Summary</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <Stat label="Overall Recovery Rate" value={`${summary.overall_recovery_rate}%`} />
          <Stat label="Overdue Loans"         value={summary.overdue_loans} />
          <Stat label="Medium Risk Accounts"  value={summary.medium_risk_accounts} />
          <Stat label="Low Risk Accounts"     value={summary.low_risk_accounts} />
        </div>
      </div>
    </div>
  );
}

function BounceRiskCard({ summary }) {
  const totalLoans = summary.high_bounce_risk_customers + summary.medium_bounce_risk_customers + summary.low_bounce_risk_customers;
  
  const highPercent = totalLoans > 0 ? (summary.high_bounce_risk_customers / totalLoans * 100) : 0;
  const mediumPercent = totalLoans > 0 ? (summary.medium_bounce_risk_customers / totalLoans * 100) : 0;
  const lowPercent = totalLoans > 0 ? (summary.low_bounce_risk_customers / totalLoans * 100) : 0;
  
  return (
    <div className="bg-white rounded-2xl shadow border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2">
          🛡️ Bounce Risk & Payment Protection
        </h3>
      </div>
      
      <div className="space-y-3">
        {/* High Risk */}
        <BounceRiskRow
          icon="🔴"
          label="High Risk"
          count={summary.high_bounce_risk_customers}
          percent={highPercent}
          color="red"
          href="/officer/search?bounce_risk_level=High"
        />
        
        {/* Medium Risk */}
        <BounceRiskRow
          icon="🟡"
          label="Medium Risk"
          count={summary.medium_bounce_risk_customers}
          percent={mediumPercent}
          color="yellow"
          href="/officer/search?bounce_risk_level=Medium"
        />
        
        {/* Low Risk */}
        <BounceRiskRow
          icon="🟢"
          label="Low Risk"
          count={summary.low_bounce_risk_customers}
          percent={lowPercent}
          color="green"
        />
        
        {/* Divider */}
        <div className="border-t border-gray-200 my-3"></div>
        
        {/* Auto-Pay Enrollment */}
        <BounceRiskRow
          icon="🔒"
          label="Auto-Pay Enrolled"
          count={summary.active_autopay_mandates}
          percent={summary.autopay_enrollment_rate}
          color="purple"
          suffix={`of ${totalLoans} loans`}
        />
      </div>
    </div>
  );
}

function BounceRiskRow({ icon, label, count, percent, color, href, suffix }) {
  const colors = {
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
  };
  
  const textColors = {
    red: 'text-red-700',
    yellow: 'text-yellow-700',
    green: 'text-green-700',
    purple: 'text-purple-700',
  };
  
  const Content = (
    <div className="flex items-center gap-3">
      <span className="text-xl">{icon}</span>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-bold ${textColors[color]}`}>{count}</span>
            <span className="text-xs text-gray-500">{percent.toFixed(1)}%</span>
          </div>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full ${colors[color]} rounded-full transition-all duration-300`}
            style={{ width: `${Math.min(percent, 100)}%` }}
          ></div>
        </div>
        {suffix && <p className="text-xs text-gray-500 mt-1">{suffix}</p>}
      </div>
    </div>
  );
  
  if (href) {
    return (
      <a href={href} className="block hover:bg-gray-50 rounded-lg p-2 -m-2 transition-colors cursor-pointer">
        {Content}
      </a>
    );
  }
  
  return <div className="p-2 -m-2">{Content}</div>;
}

function KPICard({ label, value, icon, color, sub, href }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-700 border-blue-100',
    red:    'bg-red-50 text-red-700 border-red-100',
    green:  'bg-green-50 text-green-700 border-green-100',
    purple: 'bg-purple-50 text-purple-700 border-purple-100',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-100',
  };
  const Tag = href ? 'a' : 'div';
  return (
    <Tag
      href={href}
      className={`rounded-2xl border p-5 ${colors[color]} ${href ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
    >
      <div className="flex items-start justify-between">
        <span className="text-2xl">{icon}</span>
      </div>
      <p className="text-2xl font-bold mt-2">{value}</p>
      <p className="text-xs font-medium mt-1 opacity-80">{label}</p>
      {sub && <p className="text-xs opacity-60 mt-0.5">{sub}</p>}
    </Tag>
  );
}

function Stat({ label, value }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
    </div>
  );
}