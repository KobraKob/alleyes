"use client";

const locations = [
  { name: "Indiranagar", area: "East Bengaluru", leads: 142, trials: 68, members: 42, spend: "₹48,000", cac: "₹1,142", rpr: "3.42", rate: "29.6%" },
  { name: "Koramangala", area: "South Bengaluru", leads: 118, trials: 52, members: 36, spend: "₹41,500", cac: "₹1,152", rpr: "3.25", rate: "30.5%" },
  { name: "Whitefield", area: "East Bengaluru", leads: 95, trials: 40, members: 28, spend: "₹32,000", cac: "₹1,142", rpr: "3.10", rate: "29.5%" },
];

const funnel = [
  { label: "Captured leads", value: 355, width: "100%", count: "100%" },
  { label: "Trial booked", value: 186, width: "52.4%", count: "52.4%" },
  { label: "Trial attended", value: 160, width: "45.1%", count: "45.1%" },
  { label: "Paid membership", value: 106, width: "29.9%", count: "29.9%" },
];

export default function PerformancePage() {
  return <div>
    <div className="page-heading">
      <div><div className="eyebrow"><span className="eyebrow-mark" /> COMMERCIAL INTELLIGENCE / 02</div><h1>Performance overview</h1><p>Follow the money from first touch to paid membership. Compare branch efficiency, funnel leakage and acquisition cost.</p></div>
      <div className="heading-meta"><span className="period-select">OCTOBER 2026&nbsp;⌄</span></div>
    </div>
    <div className="demo-notice"><span className="notice-icon">i</span><span><strong>Illustrative workspace data.</strong> These values are sample figures for interface review, not live campaign results. Connect the reporting API before using them for business decisions.</span></div>
    <div className="metric-grid">
      <div className="metric-card"><div className="metric-label">New members</div><div className="metric-value">106<span style={{fontSize:13,color:"#879188",letterSpacing:0}}> / 120</span></div><div className="metric-foot"><span>Monthly objective</span><span className="delta">88.3% reached</span></div><div className="metric-rule"><span style={{width:"88.3%"}} /></div></div>
      <div className="metric-card"><div className="metric-label">Blended acquisition cost</div><div className="metric-value">₹1,146</div><div className="metric-foot"><span>Ceiling ₹1,500</span><span className="delta">23.6% under</span></div><div className="metric-rule"><span style={{width:"76.4%"}} /></div></div>
      <div className="metric-card"><div className="metric-label">Media spend</div><div className="metric-value">₹1.21L</div><div className="metric-foot"><span>Budget ₹1.80L</span><span className="delta neutral">67.5% used</span></div><div className="metric-rule"><span style={{width:"67.5%"}} /></div></div>
      <div className="metric-card"><div className="metric-label">Reward / rupee</div><div className="metric-value">3.28<span style={{fontSize:13,color:"#879188"}}>×</span></div><div className="metric-foot"><span>Retention-weighted proxy</span><span className="delta neutral">Sample metric</span></div><div className="metric-rule"><span style={{width:"72%"}} /></div></div>
    </div>
    <div className="content-grid">
      <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Conversion funnel</h2><p className="panel-subtitle">Lead-to-member progression across all demo branches</p></div><span className="panel-kicker">MONTH TO DATE</span></div><div className="panel-body"><div className="bar-list">{funnel.map((item,i)=><div className="bar-row" key={item.label}><div className="bar-meta"><strong>{item.label}</strong><span>{item.value.toLocaleString("en-IN")} <span style={{color:"#a0a8a0"}}>· {item.count}</span></span></div><div className="bar-track"><div className={"bar-fill "+(i===3?"dark":"")} style={{width:item.width}} /></div></div>)}</div><div style={{marginTop:20,paddingTop:14,borderTop:"1px solid #edf0ea",display:"flex",justifyContent:"space-between",gap:12,fontSize:10,color:"#778278"}}><span>Biggest drop-off: captured lead → trial booked</span><strong style={{color:"#a66a20"}}>47.6% leakage</strong></div></div></section>
      <section className="panel"><div className="panel-header"><div><h2 className="panel-title">Objective status</h2><p className="panel-subtitle">Progress against the operating brief</p></div><span className="status-pill">On track</span></div><div className="panel-body"><div style={{display:"flex",alignItems:"baseline",justifyContent:"space-between",gap:12}}><span style={{fontSize:11,color:"#727d74"}}>Membership target</span><strong style={{fontSize:24,letterSpacing:-1}}>106 <span style={{fontSize:11,color:"#7d877f",letterSpacing:0}}>/ 120</span></strong></div><div className="metric-rule" style={{height:7,marginTop:13}}><span style={{width:"88.3%"}} /></div><div style={{display:"flex",justifyContent:"space-between",marginTop:8,color:"#7b857d",fontSize:10}}><span>88.3% achieved</span><span>14 remaining</span></div><div style={{marginTop:23,paddingTop:17,borderTop:"1px solid #edf0ea"}}><div className="bar-meta"><strong>CAC ceiling</strong><span>₹1,146 / ₹1,500</span></div><div className="metric-rule" style={{height:7,marginTop:10}}><span style={{width:"76.4%",background:"#6f8a6a"}} /></div><p style={{margin:"9px 0 0",color:"#6d786e",fontSize:10,lineHeight:1.6}}>Current sample CAC sits below the stated ceiling. Validate spend and membership attribution before acting.</p></div></div></section>
    </div>
    <div className="section-heading"><div><h2>Branch economics</h2><p>Compare lead volume, trial conversion and acquisition cost.</p></div><span className="panel-kicker">3 LOCATIONS · SAMPLE</span></div>
    <section className="panel"><div className="data-table-wrap"><table><thead><tr><th>Branch</th><th>Leads</th><th>Trials attended</th><th>Members</th><th>Trial → member</th><th>Spend</th><th>CAC</th><th>Reward / ₹</th></tr></thead><tbody>{locations.map((loc)=><tr key={loc.name}><td><span className="cell-primary">{loc.name}</span><br/><span className="cell-muted">{loc.area}</span></td><td>{loc.leads}</td><td>{loc.trials}</td><td className="table-number">{loc.members}</td><td>{loc.rate}</td><td>{loc.spend}</td><td className="table-number">{loc.cac}</td><td><span className="status-pill">{loc.rpr}×</span></td></tr>)}</tbody></table></div></section>
  </div>;
}
