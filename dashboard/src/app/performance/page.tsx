"use client";

import { useMemo } from "react";
import { formatCurrencyMinor, formatDuration, formatInteger, humanizeKey } from "@/lib/api";
import { useOperationalData } from "@/lib/use-operational-data";
import { ConnectPrompt, EmptyState, ErrorNotice, LoadingState, Metric, PageHeading, PanelHeading, SectionHeading, Surface } from "@/components/primitives";

export default function PerformancePage() {
  const { connection, business, checking, connectionError, reload, data, errors, loading, refresh } = useOperationalData();
  const funnel = data.weekly?.funnel ?? {};
  const stages = useMemo(() => Object.entries(funnel), [funnel]);
  const maxCount = Math.max(1, ...stages.map(([, count]) => count));
  const activeObjectives = (data.objectives ?? []).filter((objective) => objective.status?.toLowerCase() === "active");
  const spendMinor = (data.campaigns ?? []).reduce((sum, campaign) => sum + (Number.isFinite(campaign.spend_minor) ? campaign.spend_minor : 0), 0);
  const errorsPresent = Object.entries(errors).filter(([, message]) => Boolean(message));

  if (checking) return <LoadingState label="Checking workspace connection" />;
  if (!connection) return <ConnectPrompt />;
  if (!business) return <><ErrorNotice message={connectionError || "Workspace connection could not be verified."} onRetry={() => { void reload(); }} /><ConnectPrompt /></>;

  return (
    <div className="page">
      <PageHeading
        eyebrow="COMMERCIAL INTELLIGENCE / PERFORMANCE"
        title="Follow outcomes, not noise."
        description="Live campaign reward, spend, funnel activity and business configuration returned by your ALLEYES API."
        actions={<button className="button button-primary" onClick={() => void refresh()} disabled={loading}>{loading ? "Refreshing…" : "↻ Refresh reports"}</button>}
      />
      {errorsPresent.length ? <div className="notice notice-error"><span className="notice-symbol">!</span><div className="notice-copy"><strong>Some report data could not be loaded.</strong><p>{errorsPresent.map(([key, message]) => `${humanizeKey(key)}: ${message}`).join(" · ")}</p></div></div> : null}

      <div className="metrics-grid">
        <Metric index="01" label="Campaign records" value={data.campaigns ? formatInteger(data.campaigns.length) : "No reading"} detail="Rows returned by campaign performance view" />
        <Metric index="02" label="Recorded media spend" value={data.campaigns ? formatCurrencyMinor(spendMinor, business.currency) : "No reading"} detail="Sum of reported campaign spend; no spend estimate" />
        <Metric index="03" label="Active objectives" value={data.objectives ? formatInteger(activeObjectives.length) : "No reading"} detail={data.objectives ? `${data.objectives.length} saved objectives total` : "Objective report unavailable"} />
        <Metric index="04" label="First response" value={data.weekly ? formatDuration(data.weekly.avg_first_response_seconds) : "No reading"} detail="Average from conversations table" />
      </div>

      <div className="content-grid">
        <Surface>
          <PanelHeading title="Funnel by persisted stage" detail="Counts come from contact-stage history; order follows the returned object." trailing={<span className="panel-kicker">API REPORT</span>} />
          <div className="surface-body">
            {loading && !data.weekly ? <LoadingState /> : stages.length ? <div className="funnel-list">
              {stages.map(([key, count], index) => <div className="funnel-item" key={key}>
                <div className="funnel-meta"><strong>{humanizeKey(key)}</strong><span className="funnel-value">{formatInteger(count)}</span></div>
                <div className="funnel-track"><div className="funnel-fill" style={{ width: `${Math.max(0, Math.min(100, count / maxCount * 100))}%`, opacity: Math.max(.5, 1 - index * .08) }} /></div>
              </div>)}
            </div> : <EmptyState title={errors.weekly ? "Funnel report unavailable" : "No funnel stages returned"} detail={errors.weekly || "No persisted stage counts were returned for this business."} />}
          </div>
        </Surface>
        <Surface>
          <PanelHeading title="Business locations" detail="Configured branches returned by the locations endpoint" trailing={<span className="panel-kicker">{data.locations ? `${data.locations.length} LOCATIONS` : "API READ"}</span>} />
          <div className="surface-body">
            {loading && !data.locations ? <LoadingState /> : data.locations?.length ? <div className="objective-list">
              {data.locations.map((location) => <div className="objective-row" key={location.id}>
                <strong>{location.name}</strong>
                <div className="objective-meta"><span>{location.city || "City not recorded"}</span>{location.capacity !== null && location.capacity !== undefined ? <span>Capacity {formatInteger(location.capacity)}/day</span> : null}{location.catchment_m !== null && location.catchment_m !== undefined ? <span>Catchment {formatInteger(location.catchment_m)}m</span> : null}</div>
              </div>)}
            </div> : <EmptyState title={errors.locations ? "Locations unavailable" : "No locations configured"} detail={errors.locations || "The API returned no business locations."} />}
          </div>
        </Surface>
      </div>

      <SectionHeading title="Campaign economics" description="Reward and spend from the database view, scoped to this business." trailing={<span className="panel-kicker">NO SYNTHETIC METRICS</span>} />
      <Surface>
        {loading && !data.campaigns ? <div className="surface-body"><LoadingState /></div> : data.campaigns?.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Campaign</th><th>Reward</th><th>Spend</th><th>Reward / ₹1</th></tr></thead><tbody>
          {data.campaigns.map((campaign) => <tr key={campaign.campaign_id}>
            <td><span className="cell-main">{campaign.name || "Unnamed campaign"}</span><span className="cell-secondary">{campaign.campaign_id}</span></td>
            <td className="number-cell">{Number.isFinite(campaign.reward) ? campaign.reward.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "Not recorded"}</td>
            <td className="number-cell">{formatCurrencyMinor(campaign.spend_minor, business.currency)}</td>
            <td>{Number.isFinite(campaign.reward_per_rupee) ? <span className="status-chip">{campaign.reward_per_rupee.toFixed(3)}×</span> : "Not recorded"}</td>
          </tr>)}
        </tbody></table></div> : <EmptyState title={errors.campaigns ? "Campaign endpoint unavailable" : "No campaign rows"} detail={errors.campaigns || "The campaign performance view has no rows for this business."} />}
      </Surface>

      <SectionHeading title="Objectives on record" description="Targets currently stored by the business workspace." />
      {loading && !data.objectives ? <LoadingState /> : data.objectives?.length ? <div className="insight-list">
        {data.objectives.map((objective) => <article className="insight-card" key={objective.id}>
          <div className="insight-head"><h3>{objective.statement}</h3><span className={`status-chip ${objective.status === "active" ? "" : "neutral"}`}>{humanizeKey(objective.status || "unknown")}</span></div>
          <div className="objective-meta"><span>Target {formatInteger(objective.target_value)}</span><span>Budget {formatCurrencyMinor(objective.budget_minor, business.currency)}</span><span>ID {objective.id}</span></div>
        </article>)}
      </div> : <Surface><EmptyState title={errors.objectives ? "Objectives unavailable" : "No objectives on record"} detail={errors.objectives || "No objectives were returned for this workspace."} /></Surface>}
    </div>
  );
}
