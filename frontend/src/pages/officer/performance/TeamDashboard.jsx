/**
 * Team Dashboard - Performance & Coaching Overview
 * Displays team-wide metrics, leaderboard, and coaching alerts
 */

import React, { useState, useEffect } from 'react';
import api from '../../../api';

const TeamDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(30);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState('');
  const [justRefreshed, setJustRefreshed] = useState(false);
  
  // Coaching modal state
  const [showCoachingModal, setShowCoachingModal] = useState(false);
  const [coachingForm, setCoachingForm] = useState({
    officer_id: '',
    session_type: '1-on-1',
    topic: '',
    scheduled_date: '',
    notes: ''
  });
  const [schedulingCoaching, setSchedulingCoaching] = useState(false);
  
  // Report state
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportData, setReportData] = useState(null);

  // Fetch dashboard data
  const fetchDashboard = async (showRefreshIndicator = false) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/performance/team-dashboard?period_days=${periodDays}`);
      setDashboardData(response.data);
      
      if (showRefreshIndicator) {
        setJustRefreshed(true);
        setTimeout(() => setJustRefreshed(false), 2000);
      }
    } catch (err) {
      console.error('[TeamDashboard] Error fetching data:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Analyze recent unanalyzed calls
  const handleAnalyzeCalls = async () => {
    setAnalyzing(true);
    setAnalysisStatus('🔍 Finding unanalyzed calls...');
    
    try {
      console.log('[TeamDashboard] Starting batch analysis...');
      
      // Call the batch analyze endpoint
      const response = await api.post('/performance/analyze-batch', {
        limit: 10  // Analyze up to 10 calls
      });
      
      console.log('[TeamDashboard] Analysis response:', response.data);
      
      const { analyzed_count, total_unanalyzed } = response.data;
      
      if (analyzed_count > 0) {
        setAnalysisStatus(`✅ Successfully analyzed ${analyzed_count} calls! Refreshing dashboard...`);
        // Refresh dashboard after 1.5 seconds
        setTimeout(async () => {
          await fetchDashboard(true); // Pass true to show refresh indicator
          setAnalysisStatus(`🎉 Dashboard updated! ${analyzed_count} new calls analyzed.`);
          setTimeout(() => {
            setAnalyzing(false);
            setAnalysisStatus('');
          }, 3000);
        }, 1500);
      } else {
        setAnalysisStatus(`ℹ️ All calls are already analyzed! (Total: ${total_unanalyzed})`);
        setTimeout(() => {
          setAnalyzing(false);
          setAnalysisStatus('');
        }, 3000);
      }
    } catch (err) {
      console.error('[TeamDashboard] Error analyzing calls:', err);
      console.error('[TeamDashboard] Error response:', err.response?.data);
      setAnalysisStatus(`❌ Error: ${err.response?.data?.detail || err.message || 'Failed to analyze calls'}`);
      setTimeout(() => {
        setAnalyzing(false);
        setAnalysisStatus('');
      }, 4000);
    }
  };

  const handleScheduleCoaching = () => {
    setShowCoachingModal(true);
    // Pre-select first officer if available
    if (dashboardData?.leaderboard && dashboardData.leaderboard.length > 0) {
      setCoachingForm({
        ...coachingForm,
        officer_id: dashboardData.leaderboard[0].officer_id
      });
    }
  };

  const handleCloseCoachingModal = () => {
    setShowCoachingModal(false);
    setCoachingForm({
      officer_id: '',
      session_type: '1-on-1',
      topic: '',
      scheduled_date: '',
      notes: ''
    });
  };

  const handleSubmitCoaching = async (e) => {
    e.preventDefault();
    setSchedulingCoaching(true);
    
    try {
      console.log('[TeamDashboard] Scheduling coaching:', coachingForm);
      
      const response = await api.post('/performance/schedule-coaching', coachingForm);
      
      console.log('[TeamDashboard] Coaching scheduled:', response.data);
      
      alert(`✅ Success!\n\n${response.data.message}\n\nSession Type: ${response.data.session_type}\nTopic: ${response.data.topic}\nScheduled: ${new Date(response.data.scheduled_date).toLocaleString()}`);
      
      handleCloseCoachingModal();
    } catch (err) {
      console.error('[TeamDashboard] Error scheduling coaching:', err);
      alert(`❌ Error: ${err.response?.data?.detail || err.message || 'Failed to schedule coaching session'}`);
    } finally {
      setSchedulingCoaching(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportData(null);
    
    try {
      console.log('[TeamDashboard] Generating team report...');
      
      const response = await api.post('/performance/generate-report', {
        period_days: periodDays,
        format: 'json'
      });
      
      console.log('[TeamDashboard] Report generated:', response.data);
      
      setReportData(response.data);
      
      // Show report summary in alert
      const report = response.data;
      let message = `📊 Performance Report Generated\n\n`;
      message += `Period: ${report.period.start} to ${report.period.end}\n`;
      message += `Report Type: ${report.report_type}\n\n`;
      
      if (report.team_summary) {
        message += `Team Summary:\n`;
        message += `• Total Officers: ${report.team_summary.total_officers}\n`;
        message += `• Total Calls: ${report.team_summary.total_calls}\n`;
        message += `• Avg Team Score: ${report.team_summary.avg_team_score}/10\n`;
        message += `• Top Performers: ${report.team_summary.top_performers.length}\n`;
        message += `• Need Coaching: ${report.team_summary.needs_coaching.length}\n\n`;
      }
      
      message += `Recommendations:\n`;
      report.recommendations.forEach(rec => {
        message += `${rec}\n`;
      });
      
      alert(message);
      
      // Download as JSON
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `performance-report-${report.period.start}-to-${report.period.end}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
    } catch (err) {
      console.error('[TeamDashboard] Error generating report:', err);
      alert(`❌ Error: ${err.response?.data?.detail || err.message || 'Failed to generate report'}`);
    } finally {
      setGeneratingReport(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [periodDays]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-700 font-medium">❌ {error}</p>
        <button 
          onClick={fetchDashboard}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="text-center text-gray-500 py-12">
        No performance data available yet
      </div>
    );
  }

  const { period, team_metrics, leaderboard, coaching_alerts } = dashboardData;

  return (
    <div className="space-y-6">
      {/* Header with Period Selector */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Team Performance Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            {period.start_date} to {period.end_date} ({period.days} days)
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setPeriodDays(7)}
            className={`px-4 py-2 rounded ${periodDays === 7 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            7 Days
          </button>
          <button
            onClick={() => setPeriodDays(30)}
            className={`px-4 py-2 rounded ${periodDays === 30 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            30 Days
          </button>
          <button
            onClick={() => setPeriodDays(90)}
            className={`px-4 py-2 rounded ${periodDays === 90 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            90 Days
          </button>
        </div>
      </div>

      {/* Team-Wide Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Calls"
          value={team_metrics.total_calls}
          icon="📞"
          color="blue"
          highlight={justRefreshed}
        />
        <MetricCard
          title="Success Rate"
          value={`${team_metrics.success_rate}%`}
          icon="✅"
          color="green"
          subtitle="Calls scored ≥7.0"
          highlight={justRefreshed}
        />
        <MetricCard
          title="Avg Sentiment"
          value={team_metrics.avg_sentiment.toFixed(2)}
          icon="😊"
          color="purple"
          subtitle={getSentimentLabel(team_metrics.avg_sentiment)}
          highlight={justRefreshed}
        />
        <MetricCard
          title="Active Officers"
          value={team_metrics.total_officers}
          icon="👥"
          color="orange"
          highlight={justRefreshed}
        />
      </div>

      {/* Leaderboard */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800">🏆 Top Performers</h2>
          <span className="text-sm text-gray-500">Ranked by Overall Score</span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Officer</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Calls</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Success Rate</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg Sentiment</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Overall Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {leaderboard.map((entry) => (
                <tr 
                  key={entry.officer_id}
                  className={`hover:bg-gray-50 ${entry.rank <= 3 ? 'bg-yellow-50' : ''}`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {entry.rank === 1 && <span className="text-xl">🥇</span>}
                      {entry.rank === 2 && <span className="text-xl">🥈</span>}
                      {entry.rank === 3 && <span className="text-xl">🥉</span>}
                      <span className="font-semibold text-gray-700">#{entry.rank}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-800">{entry.officer_name}</p>
                      <p className="text-xs text-gray-500">{entry.officer_id}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">{entry.total_calls}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      entry.success_rate >= 75 ? 'bg-green-100 text-green-800' :
                      entry.success_rate >= 50 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {entry.success_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-gray-700">{entry.avg_sentiment.toFixed(2)}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreBadge score={entry.overall_score} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {leaderboard.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No performance data available for this period
            </div>
          )}
        </div>
      </div>

      {/* Coaching Alerts */}
      {coaching_alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">🚨 Coaching Alerts (High Priority)</h2>
          
          <div className="space-y-3">
            {coaching_alerts.map((alert) => (
              <div 
                key={alert.feedback_id}
                className="border border-orange-200 bg-orange-50 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-orange-600 text-white text-xs rounded font-medium">
                        {alert.issue_category || 'General'}
                      </span>
                      <span className="text-sm text-gray-600">Officer: {alert.officer_id}</span>
                    </div>
                    <p className="text-gray-700 text-sm">{alert.feedback_text}</p>
                    <p className="text-xs text-gray-500 mt-2">Created: {alert.created_at}</p>
                  </div>
                  <button className="ml-4 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                    View Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">⚡ Quick Actions</h2>
        
        {/* Analysis Status - More Prominent */}
        {(analyzing || analysisStatus) && (
          <div className={`mb-4 p-4 rounded-lg border-2 ${
            analysisStatus.includes('✅') ? 'bg-green-50 border-green-300 text-green-800' :
            analysisStatus.includes('❌') ? 'bg-red-50 border-red-300 text-red-800' :
            analysisStatus.includes('ℹ️') ? 'bg-blue-50 border-blue-300 text-blue-800' :
            'bg-yellow-50 border-yellow-300 text-yellow-800'
          }`}>
            <div className="flex items-center gap-3">
              {analyzing && (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current"></div>
              )}
              <p className="text-sm font-semibold">{analysisStatus || 'Processing...'}</p>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionButton
            icon="📊"
            title="Analyze Recent Calls"
            description="Run AI analysis on unanalyzed calls"
            onClick={handleAnalyzeCalls}
            disabled={analyzing}
            loading={analyzing}
          />
          <ActionButton
            icon="🎓"
            title="Schedule Coaching"
            description="Set up 1-on-1 coaching sessions"
            onClick={handleScheduleCoaching}
            disabled={schedulingCoaching}
          />
          <ActionButton
            icon="📈"
            title="Generate Report"
            description="Export performance report (JSON)"
            onClick={handleGenerateReport}
            disabled={generatingReport}
            loading={generatingReport}
          />
        </div>
      </div>

      {/* Coaching Modal */}
      {showCoachingModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-t-lg">
              <h2 className="text-2xl font-bold">🎓 Schedule Coaching Session</h2>
              <p className="text-blue-100 mt-1">Set up a coaching session for performance improvement</p>
            </div>
            
            <form onSubmit={handleSubmitCoaching} className="p-6 space-y-4">
              {/* Officer Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Officer *
                </label>
                <select
                  value={coachingForm.officer_id}
                  onChange={(e) => setCoachingForm({...coachingForm, officer_id: e.target.value})}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">-- Choose an officer --</option>
                  {dashboardData?.leaderboard?.map(officer => (
                    <option key={officer.officer_id} value={officer.officer_id}>
                      {officer.officer_name} (Score: {officer.overall_score}/10, {officer.total_calls} calls)
                    </option>
                  ))}
                </select>
              </div>

              {/* Session Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Session Type *
                </label>
                <select
                  value={coachingForm.session_type}
                  onChange={(e) => setCoachingForm({...coachingForm, session_type: e.target.value})}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="1-on-1">1-on-1 Coaching</option>
                  <option value="group">Group Session</option>
                  <option value="workshop">Workshop</option>
                  <option value="training">Training</option>
                </select>
              </div>

              {/* Topic */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Topic / Focus Area *
                </label>
                <input
                  type="text"
                  value={coachingForm.topic}
                  onChange={(e) => setCoachingForm({...coachingForm, topic: e.target.value})}
                  required
                  placeholder="e.g., Empathy and Active Listening, Objection Handling, etc."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Scheduled Date/Time */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scheduled Date & Time *
                </label>
                <input
                  type="datetime-local"
                  value={coachingForm.scheduled_date}
                  onChange={(e) => setCoachingForm({...coachingForm, scheduled_date: e.target.value})}
                  required
                  min={new Date().toISOString().slice(0, 16)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notes (Optional)
                </label>
                <textarea
                  value={coachingForm.notes}
                  onChange={(e) => setCoachingForm({...coachingForm, notes: e.target.value})}
                  rows={3}
                  placeholder="Additional notes or preparation instructions..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={handleCloseCoachingModal}
                  disabled={schedulingCoaching}
                  className="flex-1 px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={schedulingCoaching}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {schedulingCoaching ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Scheduling...
                    </>
                  ) : (
                    <>
                      <span>📅</span>
                      Schedule Session
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};


// ─────────────────────────────────────────────
// Helper Components
// ─────────────────────────────────────────────

const MetricCard = ({ title, value, icon, color, subtitle, highlight }) => {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    orange: 'bg-orange-50 border-orange-200 text-orange-700',
  };

  return (
    <div 
      className={`border rounded-lg p-5 transition-all duration-500 ${colorClasses[color] || colorClasses.blue} ${
        highlight ? 'ring-4 ring-green-400 scale-105' : ''
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
      </div>
      <p className="text-3xl font-bold">{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
};

const ScoreBadge = ({ score }) => {
  let bgColor = 'bg-gray-100 text-gray-800';
  
  if (score >= 8.5) bgColor = 'bg-green-100 text-green-800';
  else if (score >= 7.0) bgColor = 'bg-blue-100 text-blue-800';
  else if (score >= 5.0) bgColor = 'bg-yellow-100 text-yellow-800';
  else bgColor = 'bg-red-100 text-red-800';

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${bgColor}`}>
      {score.toFixed(1)}/10
    </span>
  );
};

const ActionButton = ({ icon, title, description, onClick, disabled, loading }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`bg-white border border-gray-200 rounded-lg p-4 text-left transition-all ${
      disabled 
        ? 'opacity-50 cursor-not-allowed' 
        : 'hover:shadow-lg hover:border-blue-300'
    }`}
  >
    <div className="flex items-center justify-between mb-2">
      <div className="text-3xl">{loading ? '⏳' : icon}</div>
      {loading && (
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      )}
    </div>
    <h3 className="font-semibold text-gray-800 mb-1">{title}</h3>
    <p className="text-sm text-gray-600">{loading ? 'Processing...' : description}</p>
  </button>
);

const getSentimentLabel = (score) => {
  if (score >= 0.5) return 'Very Positive';
  if (score >= 0.0) return 'Positive';
  if (score >= -0.5) return 'Neutral';
  return 'Needs Attention';
};

export default TeamDashboard;
