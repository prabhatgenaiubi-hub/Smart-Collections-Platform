/**
 * Agent Performance & Coaching Module
 * Two-panel layout: Left (Agent List) | Right (Detailed Insights)
 */

import React, { useState } from 'react';

// Dummy data for agents
const DUMMY_AGENTS = [
  {
    agent_id: "1",
    name: "Sarah Johnson",
    performance_score: 8.7,
    recovery_rate: 78,
    total_calls: 145,
    avatar_color: "bg-blue-500"
  },
  {
    agent_id: "2",
    name: "Rajesh Kumar",
    performance_score: 9.1,
    recovery_rate: 85,
    total_calls: 132,
    avatar_color: "bg-green-500"
  },
  {
    agent_id: "3",
    name: "Emily Chen",
    performance_score: 7.4,
    recovery_rate: 65,
    total_calls: 98,
    avatar_color: "bg-purple-500"
  },
  {
    agent_id: "4",
    name: "Michael Brown",
    performance_score: 8.2,
    recovery_rate: 72,
    total_calls: 120,
    avatar_color: "bg-orange-500"
  },
  {
    agent_id: "5",
    name: "Priya Sharma",
    performance_score: 9.5,
    recovery_rate: 92,
    total_calls: 156,
    avatar_color: "bg-pink-500"
  },
  {
    agent_id: "6",
    name: "David Lee",
    performance_score: 6.8,
    recovery_rate: 58,
    total_calls: 87,
    avatar_color: "bg-red-500"
  },
  {
    agent_id: "7",
    name: "Anita Desai",
    performance_score: 8.9,
    recovery_rate: 81,
    total_calls: 141,
    avatar_color: "bg-indigo-500"
  }
];

// Dummy detailed insights for each agent
const AGENT_INSIGHTS = {
  "1": {
    last_interactions: [
      {
        id: "int-1",
        customer_name: "John Smith",
        date: "2026-04-15",
        outcome: "Payment Scheduled",
        sentiment: "Positive",
        duration: "12:30 min"
      },
      {
        id: "int-2",
        customer_name: "Maria Garcia",
        date: "2026-04-14",
        outcome: "Grace Period Approved",
        sentiment: "Neutral",
        duration: "18:45 min"
      },
      {
        id: "int-3",
        customer_name: "Robert Taylor",
        date: "2026-04-13",
        outcome: "Payment Received",
        sentiment: "Positive",
        duration: "08:20 min"
      }
    ],
    strengths: [
      "Excellent empathy and active listening skills",
      "Clear communication of payment options",
      "Strong rapport building with customers",
      "Effective de-escalation techniques"
    ],
    improvements: [
      "Could offer payment plans earlier in conversation",
      "Occasionally misses cross-sell opportunities",
      "Follow-up documentation sometimes delayed"
    ],
    coaching_recommendation: "Sarah demonstrates strong empathy and communication skills. To further improve performance, focus on: (1) Introducing flexible payment options within the first 2-3 minutes of the call, (2) Documenting call outcomes immediately after each interaction, and (3) Identifying at least one cross-sell opportunity per qualifying call. Consider pairing with Priya for shadowing on proactive payment plan offers."
  },
  "2": {
    last_interactions: [
      {
        id: "int-4",
        customer_name: "Amit Patel",
        date: "2026-04-15",
        outcome: "Restructure Approved",
        sentiment: "Very Positive",
        duration: "22:15 min"
      },
      {
        id: "int-5",
        customer_name: "Lisa Anderson",
        date: "2026-04-15",
        outcome: "Payment Scheduled",
        sentiment: "Positive",
        duration: "14:10 min"
      },
      {
        id: "int-6",
        customer_name: "James Wilson",
        date: "2026-04-14",
        outcome: "Payment Received",
        sentiment: "Neutral",
        duration: "09:30 min"
      }
    ],
    strengths: [
      "Outstanding negotiation and persuasion skills",
      "Proactive in offering solutions",
      "Excellent product knowledge",
      "High success rate with difficult customers",
      "Consistently meets and exceeds targets"
    ],
    improvements: [
      "Call duration slightly above average",
      "Could improve time management between calls"
    ],
    coaching_recommendation: "Rajesh is a top performer with exceptional skills. Recommendations: (1) Share negotiation techniques in team workshops as a peer mentor, (2) Work on reducing average call duration by 10-15% without compromising quality, and (3) Develop a 'best practices' playbook based on successful strategies. Consider for leadership development program."
  },
  "3": {
    last_interactions: [
      {
        id: "int-7",
        customer_name: "Nancy Brown",
        date: "2026-04-14",
        outcome: "Follow-up Scheduled",
        sentiment: "Neutral",
        duration: "16:20 min"
      },
      {
        id: "int-8",
        customer_name: "Kevin Martinez",
        date: "2026-04-13",
        outcome: "No Resolution",
        sentiment: "Negative",
        duration: "25:40 min"
      },
      {
        id: "int-9",
        customer_name: "Susan Lee",
        date: "2026-04-12",
        outcome: "Payment Scheduled",
        sentiment: "Positive",
        duration: "19:15 min"
      }
    ],
    strengths: [
      "Good attention to detail",
      "Thorough documentation",
      "Patient with customer concerns"
    ],
    improvements: [
      "Needs stronger objection handling skills",
      "Sometimes struggles with difficult customers",
      "Could be more assertive in closing",
      "Confidence in product offerings needs improvement"
    ],
    coaching_recommendation: "Emily would benefit from targeted coaching in objection handling and assertiveness. Action plan: (1) Weekly role-play sessions focusing on common objections, (2) Shadow Rajesh or Priya for 2-3 calls to observe closing techniques, (3) Attend 'Confident Communication' workshop, and (4) Manager check-in after difficult calls for immediate feedback. Goal: Increase recovery rate to 70%+ within 30 days."
  },
  "4": {
    last_interactions: [
      {
        id: "int-10",
        customer_name: "Thomas Green",
        date: "2026-04-15",
        outcome: "Payment Scheduled",
        sentiment: "Positive",
        duration: "11:45 min"
      },
      {
        id: "int-11",
        customer_name: "Rachel White",
        date: "2026-04-14",
        outcome: "Grace Period Approved",
        sentiment: "Neutral",
        duration: "15:30 min"
      },
      {
        id: "int-12",
        customer_name: "Daniel King",
        date: "2026-04-13",
        outcome: "Payment Received",
        sentiment: "Positive",
        duration: "10:20 min"
      }
    ],
    strengths: [
      "Consistent performance across all call types",
      "Good balance of empathy and efficiency",
      "Reliable team player",
      "Strong compliance with procedures"
    ],
    improvements: [
      "Could be more proactive with payment solutions",
      "Opportunity to increase upsell rate",
      "Room for improvement in recovery rate"
    ],
    coaching_recommendation: "Michael is a solid performer with consistent results. To reach the next level: (1) Focus on proactive solution offering - introduce payment plans within first 3 minutes, (2) Complete 'Advanced Sales Techniques' training to boost upsell opportunities, and (3) Set a goal to increase recovery rate from 72% to 78% over next quarter. Pair with Rajesh for 2-3 shadowing sessions."
  },
  "5": {
    last_interactions: [
      {
        id: "int-13",
        customer_name: "Jennifer Adams",
        date: "2026-04-16",
        outcome: "Payment Received",
        sentiment: "Very Positive",
        duration: "09:15 min"
      },
      {
        id: "int-14",
        customer_name: "Christopher Hall",
        date: "2026-04-15",
        outcome: "Restructure Approved",
        sentiment: "Positive",
        duration: "20:30 min"
      },
      {
        id: "int-15",
        customer_name: "Michelle Scott",
        date: "2026-04-15",
        outcome: "Payment Scheduled",
        sentiment: "Very Positive",
        duration: "07:45 min"
      }
    ],
    strengths: [
      "Exceptional customer relationship skills",
      "Highest recovery rate in the team",
      "Excellent time management",
      "Natural ability to build trust quickly",
      "Proactive problem solver",
      "Mentor to other team members"
    ],
    improvements: [
      "Already operating at peak performance",
      "Could document best practices for team training"
    ],
    coaching_recommendation: "Priya is an exemplary top performer and team asset. Recommendations: (1) Formalize her role as a peer mentor - assign 1-2 junior agents for ongoing coaching, (2) Lead monthly 'Best Practices' sharing sessions with the team, (3) Document her successful strategies for training materials, and (4) Consider for Team Lead or Senior Agent promotion. Continue current excellent performance."
  },
  "6": {
    last_interactions: [
      {
        id: "int-16",
        customer_name: "Brian Young",
        date: "2026-04-14",
        outcome: "No Resolution",
        sentiment: "Negative",
        duration: "28:30 min"
      },
      {
        id: "int-17",
        customer_name: "Patricia Hill",
        date: "2026-04-13",
        outcome: "Follow-up Scheduled",
        sentiment: "Neutral",
        duration: "21:15 min"
      },
      {
        id: "int-18",
        customer_name: "Joseph Rivera",
        date: "2026-04-12",
        outcome: "No Resolution",
        sentiment: "Negative",
        duration: "30:45 min"
      }
    ],
    strengths: [
      "Shows effort and willingness to learn",
      "Punctual and reliable attendance",
      "Follows procedures correctly"
    ],
    improvements: [
      "Struggles with customer engagement",
      "Low recovery rate indicates need for skill development",
      "Call duration too long without positive outcomes",
      "Needs improvement in empathy and rapport building",
      "Difficulty handling objections and resistance"
    ],
    coaching_recommendation: "David requires intensive coaching and support. Immediate action plan: (1) Daily 15-minute coaching sessions with supervisor for 2 weeks, (2) Mandatory completion of 'Customer Engagement Fundamentals' and 'Empathetic Communication' courses, (3) Shadow top performers (Priya/Rajesh) for at least 10 calls, (4) Use scripted conversation guides until confidence improves, and (5) Weekly performance reviews with clear improvement goals. If recovery rate doesn't improve to 65%+ within 60 days, consider role reassessment."
  },
  "7": {
    last_interactions: [
      {
        id: "int-19",
        customer_name: "Elizabeth Torres",
        date: "2026-04-16",
        outcome: "Payment Scheduled",
        sentiment: "Positive",
        duration: "13:20 min"
      },
      {
        id: "int-20",
        customer_name: "Andrew Collins",
        date: "2026-04-15",
        outcome: "Grace Period Approved",
        sentiment: "Positive",
        duration: "17:10 min"
      },
      {
        id: "int-21",
        customer_name: "Barbara Walker",
        date: "2026-04-15",
        outcome: "Restructure Approved",
        sentiment: "Very Positive",
        duration: "24:15 min"
      }
    ],
    strengths: [
      "Strong analytical and problem-solving skills",
      "Excellent at complex loan restructuring",
      "Good product knowledge",
      "Professional demeanor",
      "Effective at handling escalated cases"
    ],
    improvements: [
      "Could improve speed in routine cases",
      "Sometimes over-analyzes simple situations",
      "Room to increase recovery rate by 5-7%"
    ],
    coaching_recommendation: "Anita has strong technical skills and handles complex cases well. To optimize performance: (1) Develop quick decision-making framework for routine calls to reduce duration, (2) Practice 'good enough' vs 'perfect' approaches for standard payment plans, (3) Use her analytical strengths to identify patterns in successful recoveries, and (4) Set goal to increase recovery rate to 85%+. Consider for specialized role in complex restructuring cases."
  }
};

const AgentPerformance = () => {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const handleAgentClick = (agent) => {
    setSelectedAgent(agent);
  };

  const getScoreColor = (score) => {
    if (score >= 9.0) return 'text-green-600';
    if (score >= 8.0) return 'text-blue-600';
    if (score >= 7.0) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBadgeColor = (score) => {
    if (score >= 9.0) return 'bg-green-100 text-green-800 border-green-300';
    if (score >= 8.0) return 'bg-blue-100 text-blue-800 border-blue-300';
    if (score >= 7.0) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    return 'bg-red-100 text-red-800 border-red-300';
  };

  const getSentimentBadge = (sentiment) => {
    const colors = {
      'Very Positive': 'bg-green-100 text-green-800',
      'Positive': 'bg-blue-100 text-blue-800',
      'Neutral': 'bg-gray-100 text-gray-800',
      'Negative': 'bg-red-100 text-red-800'
    };
    return colors[sentiment] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">🎯 Agent Performance & Coaching</h1>
        <p className="text-sm text-gray-600 mt-1">
          AI-driven performance analysis and coaching insights
        </p>
      </div>

      {/* Two-Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Agent List */}
        <div className="w-96 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">Team Agents ({DUMMY_AGENTS.length})</h2>
            <p className="text-xs text-gray-500 mt-1">Click an agent to view detailed insights</p>
          </div>

          <div className="flex-1 overflow-y-auto">
            {DUMMY_AGENTS.map((agent) => (
              <div
                key={agent.agent_id}
                onClick={() => handleAgentClick(agent)}
                className={`p-4 border-b border-gray-100 cursor-pointer transition-all hover:bg-blue-50 ${
                  selectedAgent?.agent_id === agent.agent_id ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  <div className={`w-12 h-12 rounded-full ${agent.avatar_color} flex items-center justify-center text-white font-bold text-lg flex-shrink-0`}>
                    {agent.name.split(' ').map(n => n[0]).join('')}
                  </div>

                  {/* Agent Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-gray-800 truncate">{agent.name}</h3>
                      {selectedAgent?.agent_id === agent.agent_id && (
                        <span className="text-blue-600 text-xl">→</span>
                      )}
                    </div>

                    {/* Performance Score */}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">Performance:</span>
                      <span className={`text-sm font-bold ${getScoreColor(agent.performance_score)}`}>
                        {agent.performance_score.toFixed(1)}/10
                      </span>
                    </div>

                    {/* Recovery Rate */}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">Recovery Rate:</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            agent.recovery_rate >= 80 ? 'bg-green-500' :
                            agent.recovery_rate >= 70 ? 'bg-blue-500' :
                            agent.recovery_rate >= 60 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${agent.recovery_rate}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-semibold text-gray-700">{agent.recovery_rate}%</span>
                    </div>

                    {/* Total Calls */}
                    <div className="text-xs text-gray-500 mt-1">
                      {agent.total_calls} calls completed
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel - Detailed Insights */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {!selectedAgent ? (
            // Empty State
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">👈</div>
                <h2 className="text-xl font-semibold text-gray-600 mb-2">Select an Agent</h2>
                <p className="text-gray-500">Click on an agent from the list to view detailed insights</p>
              </div>
            </div>
          ) : (
            // Agent Details
            <div className="p-6 space-y-6">
              {/* Agent Header */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-start gap-4">
                  <div className={`w-16 h-16 rounded-full ${selectedAgent.avatar_color} flex items-center justify-center text-white font-bold text-2xl`}>
                    {selectedAgent.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold text-gray-800">{selectedAgent.name}</h2>
                    <div className="flex items-center gap-4 mt-2">
                      <div className={`px-3 py-1 rounded-full border text-sm font-semibold ${getScoreBadgeColor(selectedAgent.performance_score)}`}>
                        Performance: {selectedAgent.performance_score.toFixed(1)}/10
                      </div>
                      <div className="text-sm text-gray-600">
                        <span className="font-semibold">{selectedAgent.recovery_rate}%</span> Recovery Rate
                      </div>
                      <div className="text-sm text-gray-600">
                        <span className="font-semibold">{selectedAgent.total_calls}</span> Total Calls
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Last 3 Interactions */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span>📞</span> Last 3 Interactions
                </h3>
                <div className="space-y-3">
                  {AGENT_INSIGHTS[selectedAgent.agent_id]?.last_interactions.map((interaction) => (
                    <div key={interaction.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-gray-800">{interaction.customer_name}</h4>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentBadge(interaction.sentiment)}`}>
                              {interaction.sentiment}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                            <span>📅 {interaction.date}</span>
                            <span>⏱️ {interaction.duration}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-semibold ${
                            interaction.outcome.includes('Payment') || interaction.outcome.includes('Approved') 
                              ? 'text-green-600' 
                              : interaction.outcome.includes('No Resolution')
                              ? 'text-red-600'
                              : 'text-gray-600'
                          }`}>
                            {interaction.outcome}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Strengths */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span>💪</span> Strengths
                </h3>
                <ul className="space-y-2">
                  {AGENT_INSIGHTS[selectedAgent.agent_id]?.strengths.map((strength, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-green-500 text-lg mt-0.5">✓</span>
                      <span className="text-gray-700">{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Improvement Areas */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span>📈</span> Improvement Areas
                </h3>
                <ul className="space-y-2">
                  {AGENT_INSIGHTS[selectedAgent.agent_id]?.improvements.map((improvement, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-orange-500 text-lg mt-0.5">→</span>
                      <span className="text-gray-700">{improvement}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* AI Coaching Recommendation */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow-lg p-6 border-2 border-blue-200">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span>🤖</span> AI-Generated Coaching Recommendation
                </h3>
                <div className="bg-white rounded-lg p-4 border border-blue-200">
                  <p className="text-gray-700 leading-relaxed whitespace-pre-line">
                    {AGENT_INSIGHTS[selectedAgent.agent_id]?.coaching_recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentPerformance;
