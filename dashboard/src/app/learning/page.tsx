"use client";

import { formatDate, formatInteger, humanizeKey } from "@/lib/api";
import { useOperationalData } from "@/lib/use-operational-data";
import { ConnectPrompt, EmptyState, ErrorNotice, LoadingState, PageHeading, PanelHeading, SectionHeading, Surface } from "@/components/primitives";

function evidenceText(value: unknown): string {
  if (value === null || value === undefined) return "No evidence payload was stored with this insight.";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "Evidence payload could not be displayed.";
  }
}

export default function LearningPage() {
  const { connection, business, checking, connectionError, reload, data, errors, loading, refresh } = useOperationalData();

  if (checking) return <LoadingState label="Checking workspace connection" />;
  if (!connection) return <ConnectPrompt />;
  if (!business) return <><ErrorNotice message={connectionError || "Workspace connection could not be verified."} onRetry={() => { void reload(); }} /><ConnectPrompt /></>;

  return (
    <div className="page">
      <PageHeading
        eyebrow="EXPERIMENTATION / LEARNING LAB"
        title="Evidence before certainty."
        description="Review persisted playbook insights and the vertical configurations installed on this API. No sample posteriors, invented uplift, or fabricated confidence."
        actions={<button className="button button-primary" onClick={() => void refresh()} disabled={loading}>{loading ? "Refreshing…" : "↻ Refresh evidence"}</button>}
      />

      {Object.entries(errors).filter(([, message]) => Boolean(message)).length ? <div className="notice notice-error"><span className="notice-symbol">!</span><div className="notice-copy"><strong>Some data sources are unavailable.</strong><p>{Object.entries(errors).filter(([, message]) => Boolean(message)).map(([key, message]) => `${humanizeKey(key)}: ${message}`).join(" · ")}</p></div></div> : null}

      <div className="metrics-grid">
        <div className="metric"><div className="metric-top"><span>Persisted insights</span><span className="metric-index">01</span></div><div className="metric-value">{data.insights ? formatInteger(data.insights.length) : "No reading"}</div><div className="metric-detail">{data.insights ? "Returned by the playbook insights endpoint" : errors.insights || "Waiting for API data"}</div></div>
        <div className="metric"><div className="metric-top"><span>Installed verticals</span><span className="metric-index">02</span></div><div className="metric-value">{data.packs ? formatInteger(data.packs.length) : "No reading"}</div><div className="metric-detail">{data.packs ? "Discovered from runtime pack configuration" : errors.packs || "Waiting for API data"}</div></div>
        <div className="metric"><div className="metric-top"><span>Configured decision points</span><span className="metric-index">03</span></div><div className="metric-value">{data.packs ? formatInteger(data.packs.reduce((sum, pack) => sum + pack.decision_point_count, 0)) : "No reading"}</div><div className="metric-detail">Sum of decision points across discovered packs</div></div>
        <div className="metric"><div className="metric-top"><span>Posterior diagnostics</span><span className="metric-index">04</span></div><div className="metric-value">Not exposed</div><div className="metric-detail">The current API has no arm-statistics read endpoint</div></div>
      </div>

      <SectionHeading title="Persisted playbook insights" description="Confidence and evidence are displayed exactly as returned by the business API." trailing={<span className="panel-kicker">LIVE DATABASE RECORDS</span>} />
      {loading && !data.insights ? <LoadingState /> : data.insights?.length ? <div className="insight-list">
        {data.insights.map((insight) => {
          const confidence = Math.max(0, Math.min(1, Number(insight.confidence) || 0));
          return <article className="insight-card" key={insight.id}>
            <div className="insight-head"><h3>{insight.statement}</h3><span className={`status-chip ${/valid|approved|active/i.test(insight.status) ? "" : "warn"}`}>{humanizeKey(insight.status || "unknown")}</span></div>
            <div className="confidence-line"><span>Stored confidence · {(confidence * 100).toFixed(1)}%</span><div className="confidence-track"><div className="confidence-fill" style={{ width: `${confidence * 100}%` }} /></div></div>
            <div className="evidence-box">{evidenceText(insight.evidence)}</div>
            <div className="objective-meta"><span>Created {formatDate(insight.created_at)}</span><span>Expires {insight.expires_at ? formatDate(insight.expires_at) : "No expiry recorded"}</span><span>ID {insight.id}</span></div>
          </article>;
        })}
      </div> : <Surface><EmptyState title={errors.insights ? "Insight endpoint unavailable" : "No insights have been persisted"} detail={errors.insights || "When the engine stores an insight with evidence and confidence, it will appear here. This view does not manufacture recommendations."} /></Surface>}

      <SectionHeading title="Installed business packs" description="Runtime configurations discovered by the backend, not a static frontend catalog." trailing={<span className="panel-kicker">{data.packs ? `${data.packs.length} FOUND` : "API READ"}</span>} />
      {loading && !data.packs ? <LoadingState /> : data.packs?.length ? <div className="pack-grid">
        {data.packs.map((pack) => <article className="pack-card" key={pack.slug}>
          <div className="pack-card-top"><span>PACK / {pack.slug.toUpperCase()}</span><span>v{pack.version}</span></div>
          <h3>{pack.name}</h3>
          <p>Configuration loaded by the backend pack registry. Funnel stages and decision points reflect the currently installed YAML file.</p>
          <div className="pack-tags"><span>{formatInteger(pack.funnel_stage_count)} stages</span><span>{formatInteger(pack.decision_point_count)} decision points</span></div>
          <div className="pack-tags">{(pack.channels ?? []).map((channel) => <span key={channel}>{humanizeKey(channel)}</span>)}</div>
        </article>)}
      </div> : <Surface><EmptyState title={errors.packs ? "Pack registry unavailable" : "No installed packs returned"} detail={errors.packs || "The backend pack registry returned an empty list."} /></Surface>}

      <SectionHeading title="Learning data contract" description="What this interface can and cannot prove today." />
      <Surface>
        <div className="surface-body definition-list">
          <div className="definition-row"><strong>Verified insight</strong><span>Must be persisted with evidence, confidence and status.</span></div>
          <div className="definition-row"><strong>Posterior state</strong><span>Requires a read endpoint for arm alpha/beta and observation counts.</span></div>
          <div className="definition-row"><strong>Causal lift</strong><span>Requires defined attribution, sample size and uncertainty bounds.</span></div>
          <div className="definition-row"><strong>Automatic learning</strong><span>Requires rewards and observed outcomes to flow back into the engine.</span></div>
        </div>
      </Surface>
    </div>
  );
}
