"use client";

const arms = [
  { label:"Strength & intensity", sig:"ad_hook:strength_focus", alpha:32.4, beta:58.2, n:420, traffic:42.8, mean:0.358, low:0.26, high:0.45 },
  { label:"Community & coaching", sig:"ad_hook:community_vibe", alpha:18.2, beta:72.1, n:280, traffic:28.5, mean:0.201, low:0.12, high:0.28 },
  { label:"Progress-led training", sig:"ad_hook:progress_focus", alpha:14.5, beta:82.0, n:210, traffic:21.4, mean:0.150, low:0.08, high:0.22 },
  { label:"Extreme abs", sig:"ad_hook:extreme_abs", alpha:4.1, beta:94.2, n:72, traffic:7.3, mean:0.042, low:0.01, high:0.08 },
];
const insights = [
  { title:"Trial-led offers may outperform flat discounts in selected neighbourhoods.", status:"Hypothesis", evidence:["Segment: women 25–34","Reported lift: +31%","Sample n: 412"], detail:"Example insight only. Validate source rows, confidence interval and attribution model before treating this as a supported playbook." },
  { title:"Faster first response may correlate with higher trial attendance.", status:"Needs validation", evidence:["Reported correlation: r = 0.64","Sample n: 620","Potential confounders: 3"], detail:"Correlation does not establish causation. Compare response-time cohorts while controlling for lead source, intent and opening hours." },
];

export default function LearningPage() {
  return <div>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" /> EXPERIMENTATION / 03</div><h1>Learning lab</h1><p>Understand which creative, offer and follow-up choices earn better downstream outcomes — and how much uncertainty remains.</p></div><div className="heading-meta"><span className="period-select">DECISION POINT: AD HOOK&nbsp;⌄</span></div></div>
    <div className="demo-notice"><span className="notice-icon">i</span><span><strong>Illustrative learning state.</strong> Arm statistics and insights are hardcoded preview values. They are not loaded from the learning API and must not be interpreted as validated evidence.</span></div>
    <div className="metric-grid">
      <div className="metric-card"><div className="metric-label">Arms under observation</div><div className="metric-value">04</div><div className="metric-foot"><span>One decision point</span><span className="delta neutral">Demo set</span></div></div>
      <div className="metric-card"><div className="metric-label">Assigned observations</div><div className="metric-value">982</div><div className="metric-foot"><span>Across shown variants</span><span className="delta neutral">Sample data</span></div></div>
      <div className="metric-card"><div className="metric-label">Exploration floor</div><div className="metric-value">5.0%</div><div className="metric-foot"><span>Uniform probability mix</span><span className="delta neutral">Configured example</span></div></div>
      <div className="metric-card"><div className="metric-label">Supported insights</div><div className="metric-value">00</div><div className="metric-foot"><span>Verified in this preview</span><span className="delta neutral">None confirmed</span></div></div>
    </div>
    <div className="learning-layout">
      <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Arm posterior comparison</h2><p className="panel-subtitle">Illustrative conversion-rate posterior means and 95% credible intervals</p></div><span className="panel-kicker">BETA MODEL</span></div><div className="panel-body">{arms.map((arm,i)=><div className="posterior-row" key={arm.sig}><div className="posterior-label"><strong>{arm.label}</strong><small>{arm.sig}</small><span style={{display:"block",marginTop:5,color:"#8a948b",fontSize:9}}>{arm.n} observations · {arm.traffic}% traffic</span></div><div><div className="interval-track"><span className="interval-range" style={{left:(arm.low*100)+"%",width:((arm.high-arm.low)*100)+"%"}}/><span className="interval-dot" style={{left:(arm.mean*100)+"%"}}/></div><div style={{display:"flex",justifyContent:"space-between",marginTop:6,color:"#89928a",fontSize:9,fontFamily:"monospace"}}><span>{arm.low.toFixed(2)}</span><span>95% interval</span><span>{arm.high.toFixed(2)}</span></div></div><div className="posterior-mean">{arm.mean.toFixed(3)}<small style={{display:"block",marginTop:5,color:"#8b948c",fontSize:9,fontWeight:400}}>Beta({arm.alpha}, {arm.beta})</small></div></div>)}</div><div style={{padding:"0 19px 16px",color:"#8a948b",fontSize:9,lineHeight:1.6}}>Interval lengths are scaled to a 0–1 outcome range. Production intervals should be calculated from persisted posterior parameters.</div></section>
      <div style={{display:"grid",gap:15,alignContent:"start"}}>
        <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Traffic allocation</h2><p className="panel-subtitle">Current sample split by arm</p></div></div><div className="panel-body"><div className="chart-bars">{arms.map(a=><div className="chart-bar-group" key={a.sig}><div className="chart-bar" style={{height:a.traffic+"%"}}/><span className="chart-bar-label">{a.traffic}%</span></div>)}</div><div className="chart-caption"><span>Strength</span><span>Community</span><span>Progress</span><span>Abs</span></div><div style={{marginTop:17,paddingTop:13,borderTop:"1px solid #edf0ea",fontSize:10,color:"#6f7a71",lineHeight:1.7}}>A high allocation share is not proof of a causal win. Check credible intervals and realized downstream rewards.</div></div></section>
        <section className="panel"><div className="panel-header"><div><h2 className="panel-title">How to read this</h2><p className="panel-subtitle">Decision quality, not vanity metrics</p></div></div><div className="panel-body" style={{display:"grid",gap:13}}>{[{t:"Posterior mean",d:"Expected outcome under the current Beta posterior."},{t:"Credible interval",d:"Range of plausible conversion rates given the data and model."},{t:"Traffic allocation",d:"Where the policy sends opportunities; not necessarily the winning rate."}].map(x=><div key={x.t}><strong style={{fontSize:10}}>{x.t}</strong><p style={{margin:"5px 0 0",color:"#7b857d",fontSize:10,lineHeight:1.6}}>{x.d}</p></div>)}</div></section>
      </div>
    </div>
    <div className="section-heading"><div><h2>Playbook candidates</h2><p>Insights must retain evidence, uncertainty, sample size and expiry.</p></div><span className="panel-kicker">2 EXAMPLES · UNVERIFIED</span></div>
    <div style={{display:"grid",gap:11}}>{insights.map((ins,i)=><article className="insight-card" key={ins.title}><div className="insight-top"><h3>{ins.title}</h3><span className={"status-pill "+(i===0?"warn":"neutral")}>{ins.status}</span></div><p>{ins.detail}</p><div className="evidence-row">{ins.evidence.map(e=><span className="evidence-tag" key={e}>{e}</span>)}</div></article>)}</div>
  </div>;
}
