"use client";

import { useState } from "react";

type DemoAction = { id: string; kind: string; channel: string; risk: number; reasoning: string; content: string; proposed: string; checks: string[]; status: "pending" | "approved" | "rejected" };
const initialActions: DemoAction[] = [
  { id: "ACT-DEMO-014", kind: "Lead response", channel: "WhatsApp", risk: 1, reasoning: "A new enquiry asked about trial availability at the Indiranagar branch. Proposed reply uses the configured trial offer and routes unknown questions to staff.", content: "Hi there — thanks for reaching out to Iron Fitness. We can help you book a trial at our Indiranagar branch. What day and time works best for you?", proposed: "09:18:42 IST · 2 min ago", checks: ["Consent", "Quiet hours", "Claims", "Kill switch"], status: "pending" },
  { id: "ACT-DEMO-013", kind: "Campaign draft", channel: "Meta Ads", risk: 2, reasoning: "Test a schedule-led creative against the current strength-training hook. Draft remains paused pending human review.", content: "Creative hypothesis: branch-specific class schedules may improve qualified trial bookings. No campaign will be created or activated in this preview.", proposed: "09:12:05 IST · 8 min ago", checks: ["Budget envelope", "Claims", "Branch radius"], status: "pending" },
];

export default function ApprovalsPage() {
  const [actions, setActions] = useState(initialActions);
  const [filter, setFilter] = useState<"all" | "pending" | "resolved">("all");
  const [notice, setNotice] = useState("");
  const updateAction = (id:string,status:"approved"|"rejected") => {
    setActions(current => current.map(a => a.id === id ? {...a,status} : a));
    setNotice(status === "approved" ? "Demo approval recorded locally. No connector was called and no message was sent." : "Demo rejection recorded locally. No backend record was changed.");
  };
  const visible = actions.filter(a => filter === "all" || (filter === "pending" ? a.status === "pending" : a.status !== "pending"));
  const pending = actions.filter(a=>a.status==="pending").length;
  return <div>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" /> GOVERNANCE / 01</div><h1>Action desk</h1><p>Inspect what automation wants to do, why it wants to do it, and whether policy allows the action.</p></div><div className="heading-meta"><span className="status-pill warn">{pending} awaiting review</span></div></div>
    <div className="demo-notice"><span className="notice-icon">!</span><span><strong>Preview mode — no live execution.</strong> The items below are seeded examples. Approve and reject controls change this screen only; production approval must call the governed API and record the resulting audit event.</span></div>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,marginBottom:14,flexWrap:"wrap"}}><div className="heading-meta"><span className="panel-kicker">ACTION QUEUE</span><span style={{color:"#c1c7bf"}}>/</span><span>{actions.length} sample actions</span></div><div style={{display:"flex",gap:5}}>{(["all","pending","resolved"] as const).map(key=><button key={key} className="btn" onClick={()=>setFilter(key)} style={filter===key?{background:"#17211e",borderColor:"#17211e",color:"#fff"}:{}}>{key==="all"?"All actions":key==="pending"?"Pending":"Resolved"}</button>)}</div></div>
    {notice && <div className="demo-notice"><span className="notice-icon">i</span><span>{notice}</span><button className="panel-action" style={{marginLeft:"auto",flexShrink:0}} onClick={()=>setNotice("")}>Dismiss</button></div>}
    {visible.length===0?<section className="panel"><div className="empty-state"><strong>No actions in this view</strong>Try another filter or return when the queue contains new work.</div></section>:visible.map(act=><article className="action-card" key={act.id}>
      <div className="action-top"><div className="action-identity"><div className="channel-icon">{act.channel==="WhatsApp"?"W":"M"}</div><div><h2 className="action-title">{act.kind}</h2><div className="action-meta"><span className="action-id">{act.id}</span><span>·</span><span>{act.channel}</span><span>·</span><span className="status-pill warn">Risk tier {act.risk}</span><span className="status-pill neutral">{act.status==="pending"?"Pending review":act.status}</span></div></div></div>
      {act.status==="pending"?<div className="action-buttons"><button className="btn btn-primary" onClick={()=>updateAction(act.id,"approved")}>Simulate approval</button><button className="btn btn-danger" onClick={()=>updateAction(act.id,"rejected")}>Reject demo</button></div>:<div className="action-buttons"><span className="status-pill neutral">Resolved locally</span></div>}</div>
      <div className="action-content"><div><div className="field-label">Proposed payload · preview</div><div className="message-preview">{act.content}</div><div style={{marginTop:10,color:"#8a938b",fontSize:9}}>Proposed {act.proposed}</div></div><div><div className="field-label">Agent rationale</div><p className="reason-text">{act.reasoning}</p><div className="field-label" style={{marginTop:16}}>Policy pre-checks · illustrative</div><div className="checks">{act.checks.map(check=><span className="check-chip" key={check}>✓ {check}</span>)}<span className="check-chip pending">! Not API-verified</span></div></div></div>
    </article>)}
    <div className="panel" style={{marginTop:18}}><div className="panel-header"><div><h2 className="panel-title">Review standard</h2><p className="panel-subtitle">What a real approval record must include</p></div><span className="panel-kicker">GOVERNANCE CONTRACT</span></div><div className="panel-body" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:18}}>{[{n:"01",t:"Policy evidence",d:"Persist each guardrail result and rejection reason."},{n:"02",t:"Human intent",d:"Record reviewer, decision, edits and timestamp."},{n:"03",t:"Executor outcome",d:"Show connector response, retries and external reference."},{n:"04",t:"Idempotency",d:"Repeated clicks must never duplicate a side effect."}].map(x=><div key={x.n}><div className="panel-kicker">{x.n}</div><strong style={{display:"block",marginTop:8,fontSize:11}}>{x.t}</strong><p style={{margin:"6px 0 0",color:"#7b857d",fontSize:10,lineHeight:1.6}}>{x.d}</p></div>)}</div></div>
  </div>;
}
