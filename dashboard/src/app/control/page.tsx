"use client";

import { useState } from "react";

const initialLevels = [
  { kind:"send_message",level:1,desc:"Outbound messages and follow-up sequences." },
  { kind:"create_campaign",level:1,desc:"Create a campaign draft. Activation must remain a separate decision." },
  { kind:"change_budget",level:1,desc:"Change media budget within approved caps and rate limits." },
  { kind:"pause_campaign",level:2,desc:"Pause a campaign when policy and evidence permit." },
];
const initialAudit = [
  { id:"AUD-DEMO-104",actor:"agent:lead_response",action:"propose_action",entity:"actions",time:"2 min ago" },
  { id:"AUD-DEMO-103",actor:"system:updater",action:"update_arm_stats",entity:"arm_stats",time:"15 min ago" },
  { id:"AUD-DEMO-102",actor:"user:demo",action:"approve_action",entity:"actions/ACT-DEMO-012",time:"1 hour ago" },
  { id:"AUD-DEMO-101",actor:"system:partition_manager",action:"ensure_partitions",entity:"events",time:"Yesterday" },
];

export default function ControlPage() {
  const [halted,setHalted]=useState(false);
  const [confirm,setConfirm]=useState(false);
  const [levels,setLevels]=useState(initialLevels);
  const [audit,setAudit]=useState(initialAudit);
  const [notice,setNotice]=useState("");
  const toggleHalt=()=>{
    if(!halted&&!confirm){setConfirm(true);return;}
    const next=!halted;
    setHalted(next);setConfirm(false);
    setAudit(current=>[{id:"AUD-DEMO-"+(105+current.length),actor:"user:demo",action:next?"simulate_kill_switch_engage":"simulate_kill_switch_release",entity:"kill_switches",time:"Just now"},...current]);
    setNotice(next?"Local preview marked as halted. This did not engage the production kill switch.":"Local preview marked as running. This did not release a production kill switch.");
  };
  return <div>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" /> POLICY & OVERSIGHT / 04</div><h1>System control</h1><p>Set the boundaries for autonomous work. Every permission change and emergency action must be enforced and audited server-side.</p></div><div className="heading-meta"><span className="status-pill neutral">Local preview</span></div></div>
    <div className="demo-notice"><span className="notice-icon">!</span><span><strong>Not connected to production controls.</strong> This page is a UI prototype. Policy changes, kill-switch state and audit entries exist only in browser state. Do not use this screen to manage live spend or messaging.</span></div>
    {notice&&<div className="demo-notice"><span className="notice-icon">i</span><span>{notice}</span></div>}
    <section className={"control-banner "+(halted?"is-halted":"")}><div className="control-copy"><div className="panel-kicker">EMERGENCY CONTROL / DEMO ONLY</div><h2 style={{marginTop:9}}>Global execution kill switch</h2><div className={"control-state "+(halted?"halted":"")}><span className="status-dot" style={halted?{background:"#b7463b"}:{}}/>{halted?"PREVIEW HALTED":"PREVIEW ARMED"}</div><p>In production, this control must block the executor, cancel queued sends and record a durable audit event. Here it only changes the visual preview state.</p></div><div style={{display:"grid",gap:7,justifyItems:"end"}}><button className={"btn "+(halted?"btn-primary":"btn-danger")} onClick={toggleHalt}>{confirm?"Confirm demo halt":halted?"Clear preview halt":"Simulate kill switch"}</button>{confirm&&<button className="panel-action" onClick={()=>setConfirm(false)}>Cancel</button>}</div></section>
    <div className="content-grid">
      <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Autonomy policy matrix</h2><p className="panel-subtitle">Choose the preview tier for each action kind</p></div><span className="panel-kicker">LOCAL STATE</span></div><div className="panel-body"><div style={{display:"flex",gap:10,flexWrap:"wrap",marginBottom:14}}><span className="status-pill neutral">L1 · Human approval</span><span className="status-pill warn">L2 · Low-risk auto</span><span className="status-pill">L3 · Within caps</span></div>{levels.map(item=><div className="level-row" key={item.kind}><div><strong>{item.kind}</strong><p>{item.desc}</p></div><div className="level-switch">{[1,2,3].map(level=><button key={level} className={item.level===level?"selected":""} aria-label={item.kind+" level "+level} aria-pressed={item.level===level} onClick={()=>setLevels(current=>current.map(row=>row.kind===item.kind?{...row,level}:row))}>L{level}</button>)}</div></div>)}<p style={{margin:"14px 0 0",color:"#89928a",fontSize:9,lineHeight:1.6}}>These selections do not alter backend autonomy_policies. Production implementation must persist changes through an authenticated endpoint.</p></div></section>
      <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Operating limits</h2><p className="panel-subtitle">Required guardrails before any live rollout</p></div></div><div className="panel-body" style={{display:"grid",gap:0}}>{[{t:"Consent & suppression",d:"Re-check immediately before execution."},{t:"Quiet hours",d:"Use the business timezone, not server time."},{t:"Budget cap",d:"Enforce daily and monthly ceilings."},{t:"Message frequency",d:"Apply contact-level weekly send limits."},{t:"Claims validation",d:"Deterministic blocklist before model review."},{t:"Audit immutability",d:"Append-only record of decisions and outcomes."}].map((x,i)=><div key={x.t} style={{display:"flex",gap:10,padding:"12px 0",borderBottom:i===5?"0":"1px solid #edf0ea"}}><span style={{color:"#70894b",fontWeight:800,fontSize:11}}>0{i+1}</span><div><strong style={{fontSize:10}}>{x.t}</strong><p style={{margin:"4px 0 0",fontSize:10,color:"#7b857d",lineHeight:1.5}}>{x.d}</p></div></div>)}</div></section>
    </div>
    <div className="section-heading"><div><h2>Audit trail</h2><p>Sample events for layout only. Production records must be sourced from the immutable audit log.</p></div><span className="panel-kicker">APPEND-ONLY MODEL · DEMO RECORDS</span></div>
    <section className="panel"><div className="data-table-wrap"><table><thead><tr><th>Event ID</th><th>Actor</th><th>Action</th><th>Entity</th><th>Relative time</th></tr></thead><tbody>{audit.map(row=><tr key={row.id}><td className="cell-muted">{row.id}</td><td><span className="audit-actor">{row.actor}</span></td><td><span className="audit-action">{row.action}</span></td><td>{row.entity}</td><td className="cell-muted">{row.time}</td></tr>)}</tbody></table></div></section>
  </div>;
}
