"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  formatCurrencyMinor,
  formatDate,
  formatDuration,
  humanize,
  type Business,
  type CampaignReport,
  type Location,
  type PackSummary,
  type ProposedAction,
  type WeeklyReport,
} from "@/lib/api";
import { useWorkspace } from "@/components/workspace-provider";
import {
  ConnectionGate,
  EmptyState,
  ErrorState,
  LiveNotice,
  LoadingState,
  MetricCard,
  PageHeader,
  Panel,
  RefreshButton,
  SectionHeading,
} from "@/components/ui";

type OverviewData = {
  business: Business | null;
  locations: Location[];
  weekly: WeeklyReport | null;
  campaigns: CampaignReport[];
  actions: ProposedAction[];
  packs: PackSummary[];
};

const emptyData: OverviewData = {
  business: null,
  locations: [],
  weekly: null,
  campaigns: [],
  actions: [],
  packs: [],
};

const number = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
const spendLabel = (campaigns: CampaignReport[], currency: string) =>
  formatCurrencyMinor(campaigns.reduce((total, row) => total + row.spend_minor, 0), currency);

export default function DashboardPage() {
  const { connectionState, request, business: connectedBusiness } = useWorkspace();
  const [data, setData] = useState<OverviewData>(emptyData);
  const [loading, setLoading] = useState(false);
  const [fatalError, setFatalError] = useState("");
  const [sectionErrors, setSectionErrors] = useState<string[]>([]);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setFatalError("");
    const results = await Promise.allSettled([
      request<Business>("/v1/businesses"),
      request<Location[]>("/v1/locations"),
      request<WeeklyReport>("/v1/reports/weekly"),
      request<CampaignReport[]>("/v1/reports/campaigns"),
      request<ProposedAction[]>("/v1/actions?status=proposed"),
      request<PackSummary[]>("/v1/packs"),
    ]);
    const labels = ["Business profile", "Locations", "Funnel report", "Campaign report", "Action queue", "Vertical packs"];
    const errors: string[] = [];
    results.forEach((result, index) => {
      if (result.status === "rejected") {
        errors.push(`${labels[index]}: ${result.reason instanceof Error ? result.reason.message : "Request failed"}`);
      }
    });
    if (results.every((result) => result.status === "rejected")) {
      setFatalError(errors[0] || "API requests failed.");
      setSectionErrors([]);
      setLoading(false);
      return;
    }
    setData({
      business: results[0].status === "fulfilled" ? results[0].value : connectedBusiness,
      locations: results[1].status === "fulfilled" ? results[1].value : [],
      weekly: results[2].status === "fulfilled" ? results[2].value : null,
      campaigns: results[3].status === "fulfilled" ? results[3].value : [],
      actions: results[4].status === "fulfilled" ? results[4].value : [],
      packs: results[5].status === "fulfilled" ? results[5].value : [],
    });
    setSectionErrors(errors);
    setRefreshedAt(new Date().toISOString());
    setLoading(false);
  }, [request, connectedBusiness]);

  useEffect(() => {
    if (connectionState === "connected") void load();
  }, [connectionState, load]);

  if (connectionState === "loading") return <LoadingState label="Checking workspace connection" />;
  if (connectionState !== "connected") return <><PageHeader eyebrow="WORKSPACE / 01" title="Overview" description="Your operating picture, built from connected business data." /><ConnectionGate /></>;
  if (fatalError) return <><PageHeader eyebrow="WORKSPACE / 01" title="Overview" description="Your operating picture, built from connected business data." action={<RefreshButton onClick={() => void load()} busy={loading} />} /><ErrorState message={fatalError} onRetry={() => void load()} /></>;

  const funnelRows = Object.entries(data.weekly?.funnel ?? {}).sort((a, b) => b[1] - a[1]);
  const maxFunnel = Math.max(1, ...funnelRows.map(([, value]) => value));
  const campaigns = [...data.campaigns].sort((a, b) => b.reward_per_rupee - a.reward_per_rupee);
  const currency = data.business?.currency || "INR";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="WORKSPACE / 01"
        title="Overview"
        description="Your operating picture. Actual records only; each figure below comes from the connected business API."
        action={<RefreshButton onClick={() => void load()} busy={loading} />}
      />

      {sectionErrors.length > 0 && (
        <LiveNotice tone="warning">
          <strong>Some sections did not load.</strong>
          <ul className="compact-error-list">{sectionErrors.map((error) => <li key={error}>{error}</li>)}</ul>
        </LiveNotice>
      )}

      <section className="overview-hero">
        <div className="hero-main">
          <div className="hero-topline"><span className="hero-live-dot" /> LIVE WORKSPACE <span className="hero-divider">/</span> {data.business?.timezone || "TIMEZONE NOT SET"}</div>
          <h2>{data.business?.name || "Business workspace"}<br /><span>in focus.</span></h2>
          <p>{data.business?.brand_profile && Object.keys(data.business.brand_profile).length > 0
            ? "Performance, funnel movement, and pending actions from your connected records."
            : "Your business is connected. Add brand context and objectives to make actions more specific."}</p>
          <div className="hero-footer">
            <span><b>{data.business?.status || "Unknown status"}</b> <i>/</i> Business status</span>
            <span><b>{data.locations.length}</b> locations on record</span>
          </div>
        </div>
        <div className="hero-side">
          <div className="hero-side-label">CURRENT OPERATING SIGNAL</div>
          <div className="signal-count">{data.actions.length.toString().padStart(2, "0")}</div>
          <div className="signal-title">Actions awaiting review</div>
          <p>Proposed actions requiring human approval, returned by the governance API.</p>
          <Link href="/approvals" className="hero-link">Open action desk <span>↗</span></Link>
          <div className="hero-side-rule" />
          <div className="hero-refresh"><span>LAST API REFRESH</span><strong>{formatDate(refreshedAt)}</strong></div>
        </div>
      </section>

      <div className="metric-grid">
        <MetricCard label="Locations" value={number(data.locations.length)} note="Configured business locations" marker="⌖" />
        <MetricCard label="Campaign records" value={number(data.campaigns.length)} note="Present in performance view" marker="↗" />
        <MetricCard label="Tracked media spend" value={spendLabel(data.campaigns, currency)} note="Sum of campaign spend records" marker="₹" emphasis />
        <MetricCard label="First response" value={formatDuration(data.weekly?.avg_first_response_seconds)} note="Mean recorded conversation response" marker="◷" />
      </div>

      <div className="dashboard-grid">
        <Panel
          title="Funnel by stage"
          description="Counts from the configured business funnel. Stage counts are not added together."
          action={<span className="micro-tag">LIVE REPORT</span>}
          className="funnel-panel"
        >
          {data.weekly === null ? (
            <EmptyState title="Funnel report unavailable" description="The API did not return stage counts for this request." />
          ) : funnelRows.length === 0 ? (
            <EmptyState title="No funnel activity recorded" description="Stage counts will appear here after matching conversion events are ingested." />
          ) : (
            <div className="funnel-list">
              {funnelRows.map(([key, value], index) => (
                <div className="funnel-item" key={key}>
                  <div className="funnel-line">
                    <span className="funnel-index">{String(index + 1).padStart(2, "0")}</span>
                    <strong>{humanize(key)}</strong>
                    <b>{number(value)}</b>
                  </div>
                  <div className="funnel-track"><span style={{ width: `${Math.max(value > 0 ? 2 : 0, value / maxFunnel * 100)}%` }} /></div>
                </div>
              ))}
            </div>
          )}
          <div className="panel-footnote">Source: <code>/v1/reports/weekly</code></div>
        </Panel>

        <Panel title="Campaign efficiency" description="Sorted by reported reward per rupee." action={<Link href="/performance" className="inline-link">Full report ↗</Link>}>
          {data.campaigns.length === 0 ? (
            <EmptyState title="No campaign results yet" description="Campaign rows appear after the reporting view has recorded attributable outcomes and spend." />
          ) : (
            <div className="campaign-mini-list">
              {campaigns.slice(0, 5).map((campaign, index) => (
                <div className="campaign-mini-row" key={campaign.campaign_id}>
                  <span className="campaign-rank">{String(index + 1).padStart(2, "0")}</span>
                  <div className="campaign-mini-copy"><strong>{campaign.name}</strong><span>{formatCurrencyMinor(campaign.spend_minor, currency)} spend</span></div>
                  <div className="campaign-rpr"><strong>{campaign.reward_per_rupee.toFixed(2)}×</strong><span>reward / ₹</span></div>
                </div>
              ))}
            </div>
          )}
          <div className="panel-footnote">Source: <code>/v1/reports/campaigns</code></div>
        </Panel>
      </div>

      <div className="dashboard-grid dashboard-grid-bottom">
        <Panel title="Approval queue" description="Proposed actions returned by the policy pipeline." action={<Link href="/approvals" className="inline-link">Review queue ↗</Link>}>
          {data.actions.length === 0 ? (
            <EmptyState title="Queue is clear" description="No actions are currently returned as proposed and approval-required." />
          ) : (
            <div className="queue-preview">
              {data.actions.slice(0, 4).map((action) => (
                <Link href="/approvals" className="queue-preview-row" key={action.id}>
                  <span className="queue-marker" />
                  <span className="queue-main"><strong>{humanize(action.kind)}</strong><small>{action.id.slice(0, 8)} · {formatDate(action.proposed_at)}</small></span>
                  <span className={"risk-tag risk-" + Math.min(3, Math.max(1, action.risk_tier))}>R{action.risk_tier}</span>
                  <span className="row-arrow">↗</span>
                </Link>
              ))}
            </div>
          )}
        </Panel>
        <Panel title="Installed verticals" description="Runtime packs available to this application." action={<Link href="/learning" className="inline-link">Explore packs ↗</Link>}>
          {data.packs.length === 0 ? (
            <EmptyState title="No vertical packs returned" description="Check API connectivity and the pack registry route." />
          ) : (
            <div className="vertical-grid">
              {data.packs.slice(0, 6).map((pack) => (
                <article className="vertical-card" key={pack.slug}>
                  <span className="vertical-card-slug">{pack.slug}</span>
                  <strong>{pack.name}</strong>
                  <span>{pack.funnel_stage_count} stages <i>·</i> {pack.decision_point_count} decisions</span>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
