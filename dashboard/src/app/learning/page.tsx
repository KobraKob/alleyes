"use client";

import React from "react";

export default function LearningPage() {
  const arms = [
    { label: "Strength & High Intensity Hook", signature: "ad_hook:strength_focus", alpha: 32.4, beta: 58.2, n: 420, traffic: "42.8%", mean: "0.358", ci: "[0.26, 0.45]" },
    { label: "Community & Vibe Hook", signature: "ad_hook:community_vibe", alpha: 18.2, beta: 72.1, n: 280, traffic: "28.5%", mean: "0.201", ci: "[0.12, 0.28]" },
    { label: "Weight Loss Transformation", signature: "ad_hook:weight_loss", alpha: 14.5, beta: 82.0, n: 210, traffic: "21.4%", mean: "0.150", ci: "[0.08, 0.22]" },
    { label: "Aggressive Abs/Crunches", signature: "ad_hook:extreme_abs", alpha: 4.1, beta: 94.2, n: 72, traffic: "7.3%", mean: "0.042", ci: "[0.01, 0.08]" },
  ];

  const insights = [
    {
      statement: "7-Day Unlimited Free Workout Trial beats flat percentage discounts by 31% for women 25-34 near Indiranagar.",
      confidence: 0.92,
      status: "supported",
      evidence: "lift: +31%, CI: [0.14, 0.48], n: 412, OPE SNIPS p < 0.01",
      expires_at: "in 76 days"
    },
    {
      statement: "Immediate WhatsApp triage (<60s) yields 2.8x higher trial attendance compared to follow-ups after 15 minutes.",
      confidence: 0.88,
      status: "supported",
      evidence: "SLA response correlation: r = 0.64, n: 620",
      expires_at: "in 82 days"
    }
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">3. Autonomous Learning & Bandit Optimization</h2>
        <p className="text-sm text-gray-500">Live Bayesian Thompson sampling posteriors, traffic probability matching, and validated playbook insights.</p>
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
          <h3 className="font-semibold text-gray-800">Decision Point: ad_hook (Thompson Beta Bandit)</h3>
          <span className="text-xs font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded">ε = 0.05 Floor | M = 2000 Draws</span>
        </div>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left font-medium">
            <tr>
              <th className="px-6 py-3">Arm Variant</th>
              <th className="px-6 py-3">Signature</th>
              <th className="px-6 py-3">Posterior Beta(α, β)</th>
              <th className="px-6 py-3">Observations (n)</th>
              <th className="px-6 py-3">Current Traffic</th>
              <th className="px-6 py-3">Posterior Mean</th>
              <th className="px-6 py-3">95% Credible Interval</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {arms.map((arm) => (
              <tr key={arm.signature} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-semibold text-gray-900">{arm.label}</td>
                <td className="px-6 py-4 font-mono text-xs text-gray-500">{arm.signature}</td>
                <td className="px-6 py-4 font-mono">Beta({arm.alpha}, {arm.beta})</td>
                <td className="px-6 py-4 font-bold">{arm.n}</td>
                <td className="px-6 py-4 font-bold text-emerald-600">{arm.traffic}</td>
                <td className="px-6 py-4 font-mono">{arm.mean}</td>
                <td className="px-6 py-4 text-xs font-mono text-gray-600">{arm.ci}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-bold text-gray-900">Validated Playbook Insights</h3>
        <div className="grid gap-4">
          {insights.map((ins, i) => (
            <div key={i} className="bg-white border rounded-lg p-5 shadow-sm space-y-2">
              <div className="flex justify-between items-start">
                <p className="font-semibold text-gray-900 text-base">{ins.statement}</p>
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded uppercase">{ins.status}</span>
                  <span className="text-xs text-gray-500 font-mono">{(ins.confidence * 100).toFixed(0)}% Conf</span>
                </div>
              </div>
              <div className="flex justify-between items-center text-xs text-gray-500 font-mono pt-2 border-t">
                <span>Evidence: {ins.evidence}</span>
                <span>Decays: {ins.expires_at}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
