"use client";

import { useCallback, useEffect, useState } from "react";
import {
  formatCurrencyMinor,
  formatDuration,
  humanize,
  type Business,
  type CampaignReport,
  type WeeklyReport,
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

const number = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);

export default function PerformancePage() {
  const { connectionState, request, business: connectedBusiness } = useWorkspace();
  const [business, setBusiness] = useState<Business | null>(connectedBusiness);
  const [weekly, setWeekly] = useState<WeeklyReport | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [partialErrors, setPartialErrors] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const results = await Promise.allSettled([
      request<Business>("/v1/businesses"),
      request<WeeklyReport>("/v1/reports/weekly"),
      request<CampaignReport[]>("/v1/reports/campaigns"),
    ]);
    const failed = results.filter((item) => item.status === "rejected");
    if (failed.length === results.length) {
      setError(failed[0].status === "rejected" && failed[0].reason instanceof Error ? failed[0].reason.message : "Reporting requests failed.");
      setPartialErrors([]);
      setLoading(false);
      return;
    }
    setBusiness(results[0].status === "fulfilled" ? results[0].value : connectedBusiness);
    setWeekly(results[1].status === "fulfilled" ? results[1].value : null);
    setCampaigns(results[2].status === "fulfilled" ? results[2].value : []);
    const names = ["Business profile", "Funnel report", "Campaign report"];
    setPartialErrors(results.flatMap((item, index) => item.status === "rejected" ? [`${names[index]} unavailable: ${item.reason instanceof Error ? item.reason.message : "request failed"}`] : []));
    setLoading(false);
  }, [request, connectedBusiness]);

  useEffect(() => {
    if (connectionState === "connected") void load();
  }, [connectionState, load]);

  if (connectionState === "loading") return <LoadingState label="Checking workspace connection" />;
  if (connectionState !== "connected") return <><PageHeader eyebrow="COMMERCIAL / 03" title="Performance" description="Campaign outcomes and funnel movement from actual business records." /><ConnectionGate /></>;
  if (error) return <><PageHeader eyebrow="COMMERCIAL / 03" title="Performance" description="Campaign outcomes and funnel movement from actual business records." action={<RefreshButton onClick={() => void load()} busy={loading} />} /><ErrorState title="Reporting unavailable" message={error} onRetry={() => void load()} /></>;

  const currency = business?.currency || "INR";
  const spendMinor = campaigns.reduce((sum, campaign) => sum + campaign.spend_minor, 0);
  const rewardTotal = campaigns.reduce((sum, campaign) => sum + campaign.reward, 0);
  const bestRatio = campaigns.reduce<number | null>((best, campaign) => best === null || campaign.reward_per_rupee > best ? campaign.reward_per_rupee : best, null);
  const funnelRows = Object.entries(weekly?.funnel ?? {});
  const maxFunnel = Math.max(1, ...funnelRows.map(([, value]) => value));
  const sortedCampaigns = [...campaigns].sort((a, b) => b.reward_per_rupee - a.reward_per_rupee);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="COMMERCIAL / 03"
        title="Performance"
        description="Spend, reward, and stage movement from the reporting API. Weighted reward is a model outcome, not booked revenue."
        action={<RefreshButton onClick={() => void load()} busy={loading} />}
      />

      {partialErrors.map((item) => <div className="live-notice warning" key={item}><span className="notice-symbol">!</span><div>{item}</div></div>)}

      <div className="metric-grid">
        <MetricCard label="Campaign records" value={number(campaigns.length)} note="Campaigns present in the reporting view" marker="↗" />
        <MetricCard label="Spend recorded" value={campaigns.length ? formatCurrencyMinor(spendMinor, currency) : "No data"} note="Sum of reported campaign spend" marker="₹" emphasis />
        <MetricCard label="Weighted reward" value={campaigns.length ? rewardTotal.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "No data"} note="Sum of model reward values; not revenue" marker="Σ" />
        <MetricCard label="Best reward / rupee" value={bestRatio === null ? "No data" : `${bestRatio.toFixed(2)}×`} note="Highest value among reported campaigns" marker="⌁" />
      </div>

      <div className="dashboard-grid performance-grid">
        <Panel title="Funnel movement" description="Stage counts returned by the business funnel report." action={<span className="micro-tag">WEEKLY REPORT</span>}>
          {weekly === null ? (
            <EmptyState title="Funnel data unavailable" description="The reporting endpoint did not return funnel counts for this refresh." />
          ) : funnelRows.length === 0 ? (
            <EmptyState title="No funnel counts recorded" description="Ingest conversion events and configure funnel stages to populate this report." />
          ) : (
            <>
              <div className="funnel-list funnel-list-performance">
                {funnelRows.map(([key, value], index) => (
                  <div className="funnel-item" key={key}>
                    <div className="funnel-line"><span className="funnel-index">{String(index + 1).padStart(2, "0")}</span><strong>{humanize(key)}</strong><b>{number(value)}</b></div>
                    <div className="funnel-track"><span style={{ width: `${Math.max(value > 0 ? 2 : 0, value / maxFunnel * 100)}%` }} /></div>
                  </div>
                ))}
              </div>
              <p className="footnote">Bars are normalized to the largest returned stage count. Counts are shown independently and are not summed.</p>
            </>
          )}
        </Panel>
        <Panel title="Response speed" description="Mean first-response time from recorded conversations.">
          <div className="response-speed">
            <span className="response-speed-mark" aria-hidden="true">◷</span>
            <strong>{formatDuration(weekly?.avg_first_response_seconds)}</strong>
            <p>{weekly && weekly.avg_first_response_seconds > 0
              ? `Average across conversations included by the reporting query.`
              : "No response duration has been recorded in the reporting view."}</p>
          </div>
          <div className="detail-pair"><span>Business timezone</span><strong>{business?.timezone || "Not configured"}</strong></div>
          <div className="detail-pair"><span>Report endpoint</span><code>/v1/reports/weekly</code></div>
        </Panel>
      </div>

      <SectionHeading title="Campaign economics" description="Actual rows from the campaign reward-per-rupee view." action={<span className="micro-tag">{campaigns.length} RECORDS</span>} />
      <section className="panel">
        {campaigns.length === 0 ? (
          <EmptyState title="No campaign economics to show" description="This table appears when the reporting view has campaign reward and spend records." />
        ) : (
          <div className="table-scroller">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Spend</th><th>Reward</th><th>Reward / rupee</th><th>Relative efficiency</th></tr></thead>
              <tbody>
                {sortedCampaigns.map((campaign) => {
                  const maxRatio = Math.max(0.0001, ...campaigns.map((item) => item.reward_per_rupee));
                  return (
                    <tr key={campaign.campaign_id}>
                      <td><strong className="table-primary">{campaign.name}</strong><small className="table-secondary">{campaign.campaign_id}</small></td>
                      <td>{formatCurrencyMinor(campaign.spend_minor, currency)}</td>
                      <td>{campaign.reward.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td><strong className="ratio-value">{campaign.reward_per_rupee.toFixed(2)}×</strong></td>
                      <td><div className="table-bar"><span style={{ width: `${Math.max(campaign.reward_per_rupee > 0 ? 2 : 0, campaign.reward_per_rupee / maxRatio * 100)}%` }} /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <div className="footnote footnote-bottom">Reward is configured by ALLEYES and can combine multiple funnel events. It should not be interpreted as currency or revenue unless your reward definition explicitly makes it so.</div>
    </div>
  );
}
