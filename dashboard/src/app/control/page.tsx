"use client";

import React, { useState } from "react";

export default function ControlPage() {
  const [killSwitchEngaged, setKillSwitchEngaged] = useState(false);
  const [autonomyLevels, setAutonomyLevels] = useState({
    send_message: 1,
    create_campaign: 1,
    change_budget: 1,
    pause_campaign: 2,
  });

  const [auditLog, setAuditLog] = useState([
    { id: 104, actor: "agent:lead_response", action: "propose_action", entity: "actions", time: "2 mins ago" },
    { id: 103, actor: "system:updater", action: "update_arm_stats", entity: "arm_stats", time: "15 mins ago" },
    { id: 102, actor: "user:alex@ironfit.com", action: "approve_action", entity: "actions/act_982", time: "1 hour ago" },
    { id: 101, actor: "system:partition_manager", action: "ensure_partitions", entity: "events", time: "1 day ago" }
  ]);

  const toggleKillSwitch = () => {
    const nextState = !killSwitchEngaged;
    setKillSwitchEngaged(nextState);
    if (nextState) {
      setAuditLog([
        { id: Date.now(), actor: "user:alex@ironfit.com", action: "engage_kill_switch", entity: "kill_switches", time: "Just now" },
        ...auditLog
      ]);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">4. System Governance & Safety Controls</h2>
        <p className="text-sm text-gray-500">Autonomous boundaries, policy level controls, emergency kill switch, and immutable audit logs.</p>
      </div>

      {/* Emergency Kill Switch */}
      <div className={`p-6 rounded-lg border-2 shadow-sm flex items-center justify-between ${
        killSwitchEngaged ? "bg-red-50 border-red-500" : "bg-white border-gray-200"
      }`}>
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-gray-900">Emergency Kill Switch</h3>
            <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
              killSwitchEngaged ? "bg-red-600 text-white animate-pulse" : "bg-emerald-100 text-emerald-800"
            }`}>
              {killSwitchEngaged ? "HALTED" : "ARMED & SAFE"}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1 max-w-xl">
            Instantly blocks all executor workers, revokes dispatch tokens, cancels all queued sends, and sets all agents to read-only passive monitoring.
          </p>
        </div>
        <button
          onClick={toggleKillSwitch}
          className={`px-8 py-4 rounded-lg font-bold text-white text-base shadow-md transition ${
            killSwitchEngaged
              ? "bg-slate-800 hover:bg-slate-900"
              : "bg-red-600 hover:bg-red-700 active:scale-95"
          }`}
        >
          {killSwitchEngaged ? "Disengage & Resume System" : "ENGAGE KILL SWITCH"}
        </button>
      </div>

      {/* Autonomy Level Matrix */}
      <div className="bg-white border rounded-lg shadow-sm p-6 space-y-4">
        <h3 className="font-semibold text-gray-800">Autonomy Levels by Action Kind</h3>
        <p className="text-xs text-gray-500">
          L1: Always requires human approval | L2: Auto-approves Risk Tier 1 within caps | L3: Fully autonomous within caps
        </p>
        <div className="grid grid-cols-2 gap-4 pt-2">
          {Object.entries(autonomyLevels).map(([kind, level]) => (
            <div key={kind} className="flex justify-between items-center p-3 bg-gray-50 rounded border">
              <div>
                <span className="font-mono text-sm font-semibold text-gray-800">{kind}</span>
                <span className="block text-xs text-gray-500">Current setting: Level {level}</span>
              </div>
              <div className="flex space-x-1">
                {[1, 2, 3].map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setAutonomyLevels({ ...autonomyLevels, [kind]: lvl })}
                    className={`px-3 py-1 rounded text-xs font-bold ${
                      level === lvl ? "bg-slate-900 text-white" : "bg-white text-gray-700 border hover:bg-gray-100"
                    }`}
                  >
                    L{lvl}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Immutable Audit Log */}
      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
          <h3 className="font-semibold text-gray-800">Append-Only Audit Log</h3>
          <span className="text-xs text-gray-500 font-mono">Immutable Trigger Guard Active</span>
        </div>
        <table className="min-w-full divide-y divide-gray-200 text-sm font-mono">
          <thead className="bg-gray-50 text-gray-500 text-left font-medium">
            <tr>
              <th className="px-6 py-3">ID</th>
              <th className="px-6 py-3">Actor</th>
              <th className="px-6 py-3">Action</th>
              <th className="px-6 py-3">Entity</th>
              <th className="px-6 py-3">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {auditLog.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-gray-400">#{log.id}</td>
                <td className="px-6 py-3 font-semibold text-slate-800">{log.actor}</td>
                <td className="px-6 py-3 text-emerald-600">{log.action}</td>
                <td className="px-6 py-3 text-gray-600">{log.entity}</td>
                <td className="px-6 py-3 text-gray-400">{log.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
