"use client";

import { useCallback, useEffect, useState } from "react";
import {
  formatDate,
  humanize,
  type PackSummary,
  type PlaybookInsight,
  type VerticalPack,
} from "@/lib/api";
import { useWorkspace } from "@/components/workspace-provider";
import {
  ConnectionGate,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  PageHeader,
  Panel,
  RefreshButton,
  SectionHeading,
} from "@/components/ui";

const asEvidence = (evidence: unknown): string => {
  if (evidence === null || evidence === undefined) return "No evidence payload attached.";
  if (typeof evidence === "string") return evidence;
  try { return JSON.stringify(evidence, null, 2); } catch { return String(evidence); }
};

function ConfidenceValue({ value }: { value: number }) {
  const label = Number.isFinite(value)
    ? value >= 0 && value <= 1 ? `${Math.round(value * 100)}%` : value.toLocaleString("en-IN", { maximumFractionDigits: 3 })
    : "Not recorded";
  const width = Number.isFinite(value) && value >= 0 && value <= 1 ? Math.round(value * 100) : null;
  return (
    <div className="confidence-block">
      <div className="confidence-head"><span>RECORDED CONFIDENCE</span><strong>{label}</strong></div>
      {width !== null && <div className="confidence-track"><span style={{ width: `${width}%` }} /></div>}
    </div>
  );
}

export default function LearningPage() {
  const { connectionState, request } = useWorkspace();
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState("");
  const [pack, setPack] = useState<VerticalPack | null>(null);
  const [insights, setInsights] = useState<PlaybookInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [packLoading, setPackLoading] = useState(false);
  const [error, setError] = useState("");
  const [packError, setPackError] = useState("");
  const [insightError, setInsightError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setInsightError("");
    const [packResult, insightResult] = await Promise.allSettled([
      request<PackSummary[]>("/v1/packs"),
      request<PlaybookInsight[]>("/v1/insights"),
    ]);
    if (packResult.status === "fulfilled") {
      setPacks(packResult.value);
      setSelectedSlug((current) => current && packResult.value.some((item) => item.slug === current) ? current : packResult.value[0]?.slug || "");
    } else {
      setPacks([]);
      setError(packResult.reason instanceof Error ? packResult.reason.message : "Could not load vertical packs.");
    }
    if (insightResult.status === "fulfilled") {
      setInsights(insightResult.value);
    } else {
      setInsights([]);
      setInsightError(insightResult.reason instanceof Error ? insightResult.reason.message : "Could not load playbook insights.");
    }
    setLoading(false);
  }, [request]);

  useEffect(() => {
    if (connectionState === "connected") void load();
  }, [connectionState, load]);

  useEffect(() => {
    if (connectionState !== "connected" || !selectedSlug) {
      setPack(null);
      return;
    }
    let cancelled = false;
    setPackLoading(true);
    setPackError("");
    request<VerticalPack>(`/v1/packs/${encodeURIComponent(selectedSlug)}`)
      .then((value) => { if (!cancelled) setPack(value); })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setPack(null);
        setPackError(reason instanceof Error ? reason.message : "Could not load the selected pack.");
      })
      .finally(() => { if (!cancelled) setPackLoading(false); });
    return () => { cancelled = true; };
  }, [connectionState, request, selectedSlug]);

  if (connectionState === "loading") return <LoadingState label="Checking workspace connection" />;
  if (connectionState !== "connected") return <><PageHeader eyebrow="EXPERIMENTATION / 04" title="Learning lab" description="Inspect available decision points and recorded playbook insights from your API." /><ConnectionGate /></>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="EXPERIMENTATION / 04"
        title="Learning lab"
        description="Explore the runtime decision configuration and evidence recorded by the reporting system. Posterior statistics are shown only when a live endpoint exposes them."
        action={<RefreshButton onClick={() => void load()} busy={loading} />}
      />

      {error && <ErrorState title="Vertical pack registry unavailable" message={error} onRetry={() => void load()} />}
      <div className="learning-overview-grid">
        <MetricCard label="Available verticals" value={String(packs.length)} note="Validated packs returned by runtime registry" marker="◈" />
        <MetricCard label="Playbook insights" value={String(insights.length)} note="Records returned by the insight endpoint" marker="⌁" />
        <MetricCard label="Decision points" value={pack ? String(pack.decision_points?.length ?? 0) : "—"} note={pack ? `Configured in ${pack.name}` : "Select a pack to inspect its configuration"} marker="◎" emphasis />
      </div>

      <section className="pack-selector-panel">
        <div>
          <p className="detail-label">VERTICAL CONFIGURATION</p>
          <h2>Inspect a runtime pack</h2>
          <p>Each pack defines funnel stages, decision points, channels, and policy metadata. The registry is read directly from the API.</p>
        </div>
        <label className="pack-select-label">
          <span>Selected pack</span>
          <select value={selectedSlug} onChange={(event) => setSelectedSlug(event.target.value)} disabled={packs.length === 0}>
            {packs.length === 0 ? <option value="">No packs available</option> : packs.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}
          </select>
        </label>
      </section>

      {packError && <ErrorState title="Pack could not be loaded" message={packError} />}
      {packLoading ? <LoadingState label="Loading selected vertical pack" /> : pack ? (
        <div className="dashboard-grid learning-pack-grid">
          <Panel title={pack.name} description={`Runtime pack · ${pack.slug} · version ${pack.version}`} action={<span className="micro-tag">FROM API</span>}>
            <div className="detail-label">FUNNEL STAGES <span className="detail-count">{pack.funnel_stages?.length ?? 0}</span></div>
            {!pack.funnel_stages?.length ? <EmptyState title="No stages configured" description="This pack defines no funnel stages." /> : (
              <div className="stage-config-list">
                {pack.funnel_stages.map((stage, index) => (
                  <div className="stage-config" key={stage.key}>
                    <span className="stage-config-index">{String(index + 1).padStart(2, "0")}</span>
                    <div><strong>{String(stage.label || stage.name || humanize(stage.key))}</strong><small>{stage.key}</small></div>
                    <code>{typeof stage.reward_weight === "number" ? `w ${stage.reward_weight}` : "Configured"}</code>
                  </div>
                ))}
              </div>
            )}
            <div className="detail-label decision-label">DECISION POINTS <span className="detail-count">{pack.decision_points?.length ?? 0}</span></div>
            {!pack.decision_points?.length ? <EmptyState title="No decision points configured" description="This pack defines no decision points." /> : (
              <div className="decision-list">
                {pack.decision_points.map((point) => (
                  <article className="decision-row" key={point.key}>
                    <span className="decision-icon">↗</span>
                    <div><strong>{humanize(point.key)}</strong><p>{point.description || "No description provided in this pack."}</p></div>
                    <code>{typeof point.algorithm === "string" ? point.algorithm : "—"}</code>
                  </article>
                ))}
              </div>
            )}
            <div className="panel-footnote">Source: <code>/v1/packs/{pack.slug}</code></div>
          </Panel>

          <div className="learning-side-stack">
            <Panel title="Supported channels" description="Channels named by the selected pack.">
              {!pack.channels?.length ? <EmptyState title="No channels configured" description="No channel values were returned." /> : (
                <div className="channel-tag-list">{pack.channels.map((channel) => <span className="channel-tag" key={channel}>{humanize(channel)}</span>)}</div>
              )}
            </Panel>
            <Panel title="Policy metadata" description="Configured compliance fields from pack YAML.">
              {!pack.compliance || Object.keys(pack.compliance).length === 0 ? <EmptyState title="No compliance metadata" description="This pack does not return a compliance object." /> : (
                <pre className="metadata-block">{asEvidence(pack.compliance)}</pre>
              )}
            </Panel>
            <div className="endpoint-note">
              <span className="endpoint-note-mark">i</span>
              <p>Bandit posterior parameters and observation counts are not exposed by the current dashboard API. This screen does not invent conversion rates or claim a winning variant.</p>
            </div>
          </div>
        </div>
      ) : !packLoading && !error ? (
        <EmptyState title="No vertical configuration selected" description="Once the API registry returns a pack, its stages and decision points will appear here." />
      ) : null}

      <SectionHeading title="Playbook insights" description="Stored insight records. Confidence and evidence reflect the backend record, not an independent validation." action={<span className="micro-tag">{insights.length} RECORDS</span>} />
      {insightError && <div className="live-notice warning"><span className="notice-symbol">!</span><div>{insightError}</div></div>}
      {insights.length === 0 && !insightError ? (
        <Panel title="No stored insights" description="Insights are retrieved from the reporting database.">
          <EmptyState title="Nothing recorded yet" description="Insights appear here when the backend has stored playbook_insights rows for this business." />
        </Panel>
      ) : (
        <div className="insight-list">
          {insights.map((insight) => (
            <article className="insight-card" key={insight.id}>
              <div className="insight-card-header">
                <span className="insight-status">{humanize(insight.status)}</span>
                <code>{insight.id}</code>
              </div>
              <h3>{insight.statement}</h3>
              <ConfidenceValue value={insight.confidence} />
              <details className="payload-details evidence-details">
                <summary>Inspect evidence <span>↘</span></summary>
                <pre>{asEvidence(insight.evidence)}</pre>
              </details>
              <div className="insight-meta"><span>Created {formatDate(insight.created_at)}</span><span>{insight.expires_at ? `Expires ${formatDate(insight.expires_at)}` : "No expiry recorded"}</span></div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
