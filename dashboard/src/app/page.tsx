"use client";

import { useMemo } from "react";
import { formatDate, formatDuration, formatInteger, formatCurrencyMinor, humanizeKey } from "@/lib/api";
import { useOperationalData } from "@/lib/use-operational-data";
import { ConnectPrompt, EmptyState, ErrorNotice, LoadingState, Metric, PageHeading, PanelHeading, SectionHeading, Surface } from "@/components/primitives";

export default function OverviewPage() {
  const { connection, business, checking, connectionError, data, errors, loading, lastUpdated, refresh, reload } = useOperationalData();
  const funnel = data.weekly?.funnel ?? {};
  const funnelEntries = useMemo(() => Object.entries(funnel), [funnel]);
  const maxStage = Math.max(1, ...funnelEntries.map(([, count]) => count));
  const activeObjectives = (data.objectives ?? []).filter((item) => item.status?.toLowerCase() === "active");
  const anyErrors = Object.entries(errors).filter(([, message]) => Boolean(message));

  if (checking) return <LoadingState label="Checking workspace connection" />;
  if (!connection) return <ConnectPrompt />;
  if (!business) return <><ErrorNotice message={connectionError || "Workspace connection could not be verified."} onRetry={() => { void reload(); }} /><ConnectPrompt /></>;

  return (
    <div className="page">
      <PageHeading
        eyebrow="COMMAND CENTER / OVERVIEW"
        title={`The operating picture.`}
        description={`A live read on ${business.name}. Numbers below come from this workspace’s API; unavailable endpoints stay visibly unavailable.`}
        actions={<div className="button-row"><span className="panel-kicker">{lastUpdated ? `UPDATED ${formatDate(lastUpdated)}` : "AWAITING FIRST SYNC"}</span><button className="button button-primary" onClick={() => void refresh()} disabled={loading}>{loading ? "Syncing…" : "↻ Refresh data"}</button></div>}
      />

      {anyErrors.length > 0 ? <div className="notice notice-error"><span className="notice-symbol">!</span><div className="notice-copy"><strong>Some endpoints returned errors.</strong><p>{anyErrors.map(([key, message]) => `${humanizeKey(key)}: ${message}`).join(" · ")}</p></div></div> : null}

      <div className="metrics-grid">
        <Metric index="01" label="Funnel stages reporting" value={data.weekly ? formatInteger(funnelEntries.length) : "No reading"} detail={data.weekly ? "Distinct stages returned by the API" : errors.weekly ? "Report endpoint unavailable" : "Waiting for the report endpoint"} />
        <Metric index="02" label="Campaign records" value={data.campaigns ? formatInteger(data.campaigns.length) : "No reading"} detail={data.campaigns ? "Rows in campaign performance view" : errors.campaigns ? "Campaign report unavailable" : "Waiting for campaign data"} />
        <Metric index="03" label="Active objectives" value={data.objectives ? formatInteger(activeObjectives.length) : "No reading"} detail={data.objectives ? `${data.objectives.length} objective records returned` : errors.objectives ? "Objective endpoint unavailable" : "Waiting for objective data"} />
        <Metric index="04" label="Average first response" value={data.weekly ? formatDuration(data.weekly.avg_first_response_seconds) : "No reading"} detail="Calculated by the backend from recorded conversations" />
      </div>

      <div className="content-grid">
        <Surface>
          <PanelHeading title="Funnel pulse" detail="Recorded contact-stage history, ordered by actual API keys" trailing={<span className="panel-kicker">LIVE REPORT</span>} />
          <div className="surface-body">
            {loading && !data.weekly ? <LoadingState /> : funnelEntries.length ? (
              <div className="funnel-list">
                {funnelEntries.map(([key, count], index) => (
                  <div className="funnel-item" key={key}>
                    <div className="funnel-meta"><strong>{humanizeKey(key)}</strong><span className="funnel-value">{formatInteger(count)}</span></div>
                    <div className="funnel-track"><div className="funnel-fill" style={{ width: `${Math.max(0, Math.min(100, (count / maxStage) * 100))}%`, opacity: Math.max(.48, 1 - index * .08) }} /></div>
                  </div>
                ))}
              </div>
            ) : <EmptyState title={errors.weekly ? "Funnel unavailable" : "No funnel records"} detail={errors.weekly || "The report returned no funnel stages. Once events and stage history are recorded, they will appear here."} />}
            {data.weekly ? <div className="funnel-footnote"><span>First response</span><strong>{formatDuration(data.weekly.avg_first_response_seconds)}</strong></div> : null}
          </div>
        </Surface>

        <Surface>
          <PanelHeading title="Operating objectives" detail="Current goals stored for this business" trailing={<span className="panel-kicker">{data.objectives ? `${data.objectives.length} RECORDS` : "API READ"}</span>} />
          <div className="surface-body">
            {loading && !data.objectives ? <LoadingState /> : data.objectives?.length ? (
              <div className="objective-list">
                {data.objectives.slice(0, 5).map((objective) => (
                  <div className="objective-row" key={objective.id}>
                    <strong>{objective.statement}</strong>
                    <div className="objective-meta"><span className={`status-chip ${objective.status === "active" ? "" : "neutral"}`}>{humanizeKey(objective.status || "unknown")}</span><span>Target {formatInteger(objective.target_value)}</span><span>{formatCurrencyMinor(objective.budget_minor, business.currency)}</span></div>
                  </div>
                ))}
              </div>
            ) : <EmptyState title={errors.objectives ? "Objectives unavailable" : "No objectives configured"} detail={errors.objectives || "Create an objective in the workspace before expecting an operating target here."} />}
          </div>
        </Surface>
      </div>

      <SectionHeading title="Campaign economics" description="Values returned by the campaign reward-per-rupee view. No spend or conversion figures are inferred." trailing={<button className="button button-quiet button-small" onClick={() => window.location.assign("/performance")}>Open performance ↗</button>} />
      <Surface>
        {loading && !data.campaigns ? <div className="surface-body"><LoadingState /></div> : data.campaigns?.length ? (
          <div className="table-wrap"><table className="data-table"><thead><tr><th>Campaign</th><th>Reward</th><th>Spend</th><th>Reward / currency unit</th></tr></thead><tbody>
            {data.campaigns.slice(0, 8).map((campaign) => (
              <tr key={campaign.campaign_id}>
                <td><span className="cell-main">{campaign.name || "Unnamed campaign"}</span><span className="cell-secondary">{campaign.campaign_id}</span></td>
                <td className="number-cell">{Number.isFinite(campaign.reward) ? campaign.reward.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "Not recorded"}</td>
                <td className="number-cell">{formatCurrencyMinor(campaign.spend_minor, business.currency)}</td>
                <td><span className="status-chip">{Number.isFinite(campaign.reward_per_rupee) ? campaign.reward_per_rupee.toFixed(3) : "Not recorded"}×</span></td>
              </tr>
            ))}
          </tbody></table></div>
        ) : <EmptyState title={errors.campaigns ? "Campaign report unavailable" : "No campaign records returned"} detail={errors.campaigns || "The performance view contains no campaigns for this business yet."} />}
      </Surface>

      <SectionHeading title="Evidence worth reviewing" description="Only insights persisted by the workspace appear here." trailing={<button className="button button-quiet button-small" onClick={() => window.location.assign("/learning")}>Open learning lab ↗</button>} />
      {loading && !data.insights ? <LoadingState /> : data.insights?.length ? (
        <div className="insight-list">
          {data.insights.slice(0, 3).map((insight) => (
            <article className="insight-card" key={insight.id}>
              <div className="insight-head"><h3>{insight.statement}</h3><span className="status-chip">{humanizeKey(insight.status)}</span></div>
              <div className="confidence-line"><span>Confidence · {Math.round(Math.max(0, Math.min(1, insight.confidence)) * 100)}%</span><div className="confidence-track"><div className="confidence-fill" style={{ width: `${Math.max(0, Math.min(1, insight.confidence)) * 100}%` }} /></div></div>
            </article>
          ))}
        </div>
      ) : <Surface><EmptyState title={errors.insights ? "Insight feed unavailable" : "No persisted insights"} detail={errors.insights || "The workspace has not returned any playbook insights. This screen will populate when verified records exist."} /></Surface>}
    </div>
  );
}
