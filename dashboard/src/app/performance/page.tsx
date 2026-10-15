"use client";

import React from "react";

export default function PerformancePage() {
  const locations = [
    { name: "Indiranagar Branch", leads: 142, trials: 68, members: 42, spend: "₹ 48,000", cac: "₹ 1,142", rpr: 3.42 },
    { name: "Koramangala Branch", leads: 118, trials: 52, members: 36, spend: "₹ 41,500", cac: "₹ 1,152", rpr: 3.25 },
    { name: "Whitefield Branch", leads: 95, trials: 40, members: 28, spend: "₹ 32,000", cac: "₹ 1,142", rpr: 3.10 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">2. Commercial Performance & Multi-Touch Attribution</h2>
        <p className="text-sm text-gray-500">Live funnel velocity, unit economics, and retention-weighted reward per rupee.</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Members Acquired</span>
          <p className="text-3xl font-bold text-slate-900 mt-2">106</p>
          <span className="text-xs text-emerald-600 font-medium">Target: 120 / month (88.3%)</span>
        </div>
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Blended CAC</span>
          <p className="text-3xl font-bold text-slate-900 mt-2">₹ 1,146</p>
          <span className="text-xs text-emerald-600 font-medium">Target Ceiling: ₹ 1,500 (-23.6%)</span>
        </div>
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Spend (Month)</span>
          <p className="text-3xl font-bold text-slate-900 mt-2">₹ 1,21,500</p>
          <span className="text-xs text-gray-500">Budget: ₹ 1,80,000</span>
        </div>
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Reward / Rupee</span>
          <p className="text-3xl font-bold text-emerald-600 mt-2">3.28</p>
          <span className="text-xs text-gray-500">Retention-weighted efficiency</span>
        </div>
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="font-semibold text-gray-800">Branch Funnel Breakdown</h3>
        </div>
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left font-medium">
            <tr>
              <th className="px-6 py-3">Location</th>
              <th className="px-6 py-3">Leads</th>
              <th className="px-6 py-3">Trials Attended</th>
              <th className="px-6 py-3">Members</th>
              <th className="px-6 py-3">Spend</th>
              <th className="px-6 py-3">CAC</th>
              <th className="px-6 py-3">Reward / Rupee</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {locations.map((loc) => (
              <tr key={loc.name} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-semibold text-gray-900">{loc.name}</td>
                <td className="px-6 py-4">{loc.leads}</td>
                <td className="px-6 py-4">{loc.trials}</td>
                <td className="px-6 py-4 font-bold text-emerald-600">{loc.members}</td>
                <td className="px-6 py-4">{loc.spend}</td>
                <td className="px-6 py-4">{loc.cac}</td>
                <td className="px-6 py-4 font-mono">{loc.rpr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
