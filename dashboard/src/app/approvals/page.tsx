"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, formatDate, humanizeKey } from "@/lib/api";
import { useWorkspace } from "@/lib/use-workspace";
import { ConnectPrompt, EmptyState, ErrorNotice, LoadingState, PageHeading, PanelHeading, SectionHeading, Surface } from "@/components/primitives";

type ProposedAction = {
  id: string;
  kind: string;
  payload: Record<string, unknown>;
  risk_tier: number;
  reasoning: string | null;
  policy_results: Record<string, unknown>;
  proposed_at: string | null;
};

type QueueFilter = "all" | "high-risk";

function readablePayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2) ?? "{}";
}

export default function ApprovalsPage() {
  const { connection, business, checking, connectionError, reload } = useWorkspace();
  const [actions, setActions] = useState<ProposedAction[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState("");

  const refresh = useCallback(async () => {
    if (!connection || !business) return;
    setLoading(true);
    setError("");
    try {
      const rows = await apiFetch<ProposedAction[]>("/v1/actions?status=proposed", {}, connection);
      setActions(Array.isArray(rows) ? rows : []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action queue could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [connection, business?.id]);

  useEffect(() => {
    if (!connection || !business) return;
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 30_000);
    return () => window.clearInterval(timer);
  }, [connection, business?.id, refresh]);

  const visible = useMemo(() => (actions ?? []).filter((action) => {
    const matchesRisk = filter === "all" || action.risk_tier >= 2;
    const searchText = `${action.kind} ${action.id} ${JSON.stringify(action.payload)} ${action.reasoning ?? ""}`.toLowerCase();
    return matchesRisk && searchText.includes(query.toLowerCase().trim());
  }), [actions, filter, query]);

  const decide = async (action: ProposedAction, decision: "approve" | "reject") => {
    if (!connection?.reviewerId) {
      setNotice("Add a reviewer user ID in Workspace settings before making an approval decision.");
      return;
    }
    const effect = decision === "approve"
      ? "Approval may execute this action through configured connectors. Continue only after checking the payload and backend safety mode."
      : "Reject this proposed action and record the decision in the backend.";
    if (!window.confirm(effect)) return;

    setBusyId(action.id);
    setError("");
    setNotice("");
    try {
      await apiFetch<{ status?: string }>(
        `/v1/actions/${encodeURIComponent(action.id)}/${decision}`,
        {
          method: "POST",
          body: JSON.stringify({
            user_id: connection.reviewerId,
            comment: decision === "approve" ? "Approved from ALLEYES action desk." : "Rejected from ALLEYES action desk.",
          }),
        },
        connection,
      );
      setNotice(decision === "approve" ? "Approval accepted by the API. Check the returned backend/executor logs for the final outcome." : "Rejection recorded by the API.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The decision was not accepted by the API.");
    } finally {
      setBusyId("");
    }
  };

  if (checking) return <LoadingState label="Checking workspace connection" />;
  if (!connection) return <ConnectPrompt />;
  if (!business) return <><ErrorNotice message={connectionError || "Workspace connection could not be verified."} onRetry={() => { void reload(); }} /><ConnectPrompt /></>;

  return (
    <div className="page">
      <PageHeading
        eyebrow="GOVERNANCE / ACTION DESK"
        title="Human review. Real consequences."
        description="Inspect the exact payload and policy evidence before recording a decision. Approval calls the backend executor; it is not a local preview."
        actions={<button className="button button-primary" onClick={() => void refresh()} disabled={loading}>{loading ? "Refreshing…" : "↻ Refresh queue"}</button>}
      />

      {!connection.reviewerId ? <div className="notice notice-error"><span className="notice-symbol">!</span><div className="notice-copy"><strong>Reviewer identity required.</strong><p>Approval and rejection endpoints require a reviewer UUID. Add it in Workspace settings before making decisions.</p></div><button className="button button-quiet" onClick={() => window.dispatchEvent(new Event("alleeyes:open-connection"))}>Workspace settings ↗</button></div> : null}
      {notice ? <div className="notice"><span className="notice-symbol">✓</span><div className="notice-copy"><strong>API response</strong><p>{notice}</p></div><button className="button button-quiet" onClick={() => setNotice("")}>Dismiss</button></div> : null}
      {error ? <ErrorNotice message={error} onRetry={() => { void refresh(); }} /> : null}

      <div className="queue-toolbar">
        <div className="queue-title"><span className="queue-live-dot" /><div><strong>Proposed actions</strong><small>{actions === null ? "Awaiting API response" : `${actions.length} pending approval records`}</small></div></div>
        <div className="queue-tools">
          <input aria-label="Search actions" className="search-input" value={query} onChange={(event) => setQuery(event.target.value)} />
          <div className="segmented-control" aria-label="Risk filter">
            <button className={filter === "all" ? "selected" : ""} onClick={() => setFilter("all")}>All risk</button>
            <button className={filter === "high-risk" ? "selected" : ""} onClick={() => setFilter("high-risk")}>Tier 2+</button>
          </div>
        </div>
      </div>

      {loading && actions === null ? <LoadingState label="Loading proposed actions from API" /> : null}
      {!loading && actions === null && !error ? <Surface><EmptyState title="Queue not loaded" detail="Refresh the queue to request proposed actions from this business workspace." action={<button className="button button-quiet" onClick={() => void refresh()}>Load queue</button>} /></Surface> : null}
      {actions?.length === 0 ? <Surface><EmptyState title="No proposed actions" detail="The API returned an empty approval queue. New proposed actions will appear here once agents create them." /></Surface> : null}
      {actions && actions.length > 0 && visible.length === 0 ? <Surface><EmptyState title="No matching actions" detail="Change the risk filter or search text to see more records." /></Surface> : null}

      {visible.length > 0 ? <div className="action-list">
        {visible.map((action) => {
          const policyItems = Object.entries(action.policy_results ?? {});
          return <article className="action-card" key={action.id}>
            <div className="action-top">
              <div className="action-identity">
                <div className="action-symbol" aria-hidden="true">↳</div>
                <div>
                  <h2>{humanizeKey(action.kind)}</h2>
                  <div className="action-meta"><span>{action.id}</span><span>·</span><span>Risk tier {action.risk_tier}</span><span>·</span><span>{formatDate(action.proposed_at)}</span></div>
                </div>
              </div>
              <div className="button-row">
                <button className="button button-danger" onClick={() => void decide(action, "reject")} disabled={Boolean(busyId) || !connection.reviewerId}>{busyId === action.id ? "Submitting…" : "Reject"}</button>
                <button className="button button-primary" onClick={() => void decide(action, "approve")} disabled={Boolean(busyId) || !connection.reviewerId}>{busyId === action.id ? "Submitting…" : "Approve & execute"}</button>
              </div>
            </div>
            <div className="action-details">
              <div>
                <div className="field-label">Action payload · from database</div>
                <pre className="payload-preview">{readablePayload(action.payload ?? {})}</pre>
              </div>
              <div>
                <div className="field-label">Agent rationale</div>
                <p className="reasoning-text">{action.reasoning || "No rationale was stored for this action."}</p>
                <div className="field-label" style={{ marginTop: 16 }}>Persisted policy results</div>
                {policyItems.length ? <div className="policy-list">{policyItems.map(([key, value]) => <span className={`status-chip ${value === false ? "danger" : value === true ? "" : "neutral"}`} key={key}>{humanizeKey(key)}: {typeof value === "string" ? value : JSON.stringify(value)}</span>)}</div> : <p className="reasoning-text">No policy results were attached to this record.</p>}
              </div>
            </div>
          </article>;
        })}
      </div> : null}

      <SectionHeading title="Decision standard" description="This screen reads the queue and submits decisions to existing backend endpoints." trailing={<span className="panel-kicker">NO LOCAL APPROVAL STATE</span>} />
      <Surface>
        <div className="surface-body definition-list">
          <div className="definition-row"><strong>Inspect the payload</strong><span>What will be sent or changed?</span></div>
          <div className="definition-row"><strong>Read stored policy results</strong><span>Do not treat missing policy data as a pass.</span></div>
          <div className="definition-row"><strong>Approve with awareness</strong><span>Current API approval calls the executor.</span></div>
          <div className="definition-row"><strong>Verify final outcome</strong><span>An accepted approval is not proof of delivery.</span></div>
        </div>
      </Surface>
    </div>
  );
}
