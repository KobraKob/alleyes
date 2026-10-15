"use client";

import React, { useState } from "react";

export default function ApprovalsPage() {
  const [actions, setActions] = useState([
    {
      id: "act_sample_01",
      kind: "send_message",
      channel: "whatsapp",
      risk_tier: 1,
      reasoning: "Immediate qualification reply offering 7-day trial to Indiranagar walk-in lead.",
      payload: {
        to: "+919876543210",
        content: "Hey there! We would love to offer you a free 7-day workout pass at our Indiranagar gym.",
      },
      policy_results: {
        kill_switch: { passed: true },
        consent: { passed: true },
        quiet_hours: { passed: true },
        claims_check: { passed: true },
        whatsapp_window: { passed: true }
      },
      proposed_at: "2026-10-14 22:30 UTC"
    }
  ]);

  const [message, setMessage] = useState("");

  const handleApprove = (id: string) => {
    setActions(actions.filter(a => a.id !== id));
    setMessage(`Action ${id} approved and dispatched.`);
  };

  const handleReject = (id: string) => {
    setActions(actions.filter(a => a.id !== id));
    setMessage(`Action ${id} rejected.`);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">1. Approval Queue (L1 / L2 Actions)</h2>
          <p className="text-sm text-gray-500">Autonomous actions requiring explicit human confirmation before execution.</p>
        </div>
        <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2.5 py-1 rounded-full">
          {actions.length} Pending Actions
        </span>
      </div>

      {message && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded text-sm">
          {message}
        </div>
      )}

      {actions.length === 0 ? (
        <div className="bg-white border rounded-lg p-12 text-center text-gray-500">
          No actions currently awaiting approval. System operating smoothly within autonomous bounds.
        </div>
      ) : (
        <div className="grid gap-4">
          {actions.map((act) => (
            <div key={act.id} className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-lg">{act.kind}</span>
                    <span className="text-xs bg-slate-100 px-2 py-0.5 rounded font-mono uppercase">{act.channel}</span>
                    <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded font-semibold">Tier {act.risk_tier}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">Proposed at: {act.proposed_at}</p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleApprove(act.id)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-sm font-medium transition"
                  >
                    Approve & Send
                  </button>
                  <button
                    onClick={() => handleReject(act.id)}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded text-sm font-medium transition"
                  >
                    Reject
                  </button>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded text-sm border font-mono">
                <span className="font-semibold text-gray-700 block mb-1">Payload Content:</span>
                {act.payload.content}
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="font-semibold text-gray-700 block">Agent Reasoning:</span>
                  <p className="text-gray-600 mt-0.5">{act.reasoning}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-700 block">Policy Guardrail Checks:</span>
                  <div className="flex space-x-2 mt-1">
                    {Object.entries(act.policy_results).map(([check, res]: any) => (
                      <span key={check} className="bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[10px]">
                        ✓ {check}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
