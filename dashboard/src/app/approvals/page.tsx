"use client";

import { useCallback, useEffect, useState } from "react";
import {
  formatDate,
  humanize,
  isUuid,
  type ProposedAction,
} from "@/lib/api";
import { useWorkspace } from "@/components/workspace-provider";
import {
  ConnectionGate,
  EmptyState,
  ErrorState,
  LiveNotice,
  LoadingState,
  PageHeader,
  Panel,
  RefreshButton,
} from "@/components/ui";

const displayJson = (value: unknown) => {
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
};

function PolicySummary({ results }: { results: Record<string, unknown> }) {
  const entries = Object.entries(results || {});
  if (!entries.length) {
    return <p className="muted-copy">No policy evidence was attached to this action.</p>;
  }
  return (
    <div className="policy-check-list">
      {entries.map(([key, value]) => {
        const passed = value === true || (typeof value === "object" && value !== null && "passed" in value && (value as { passed?: unknown }).passed === true);
        const failed = value === false || (typeof value === "object" && value !== null && "passed" in value && (value as { passed?: unknown }).passed === false);
        return (
          <div className="policy-check" key={key}>
            <span className={"policy-check-status " + (passed ? "pass" : failed ? "fail" : "unknown")}>{passed ? "✓" : failed ? "×" : "·"}</span>
            <span className="policy-check-copy"><strong>{humanize(key)}</strong><small>{typeof value === "string" ? value : typeof value === "boolean" ? (value ? "Passed" : "Failed") : displayJson(value)}</small></span>
          </div>
        );
      })}
    </div>
  );
}

export default function ApprovalsPage() {
  const { connectionState, config, request } = useWorkspace();
  const [actions, setActions] = useState<ProposedAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [commentById, setCommentById] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await request<ProposedAction[]>("/v1/actions?status=proposed");
      setActions(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the action queue.");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (connectionState === "connected") void load();
  }, [connectionState, load]);

  async function decide(action: ProposedAction, decision: "approve" | "reject") {
    if (!isUuid(config.userId)) {
      setNotice("Set a valid reviewer user ID in workspace connection settings before recording a decision.");
      window.dispatchEvent(new Event("alleeyes:open-connection"));
      return;
    }
    const explanation = commentById[action.id]?.trim() || undefined;
    const promptText = decision === "approve"
      ? "Approve this action? The backend governance pipeline will record your decision and may invoke its executor."
      : "Reject this proposed action? The decision will be recorded in the backend.";
    if (!window.confirm(promptText)) return;
    setBusyId(action.id);
    setError("");
    setNotice("");
    try {
      const response = await request<{ status?: string; action_id?: string; [key: string]: unknown }>(
        `/v1/actions/${encodeURIComponent(action.id)}/${decision}`,
        {
          method: "POST",
          body: JSON.stringify({ user_id: config.userId, comment: explanation ?? null }),
        },
      );
      setNotice(`${decision === "approve" ? "Approval" : "Rejection"} recorded by API. Result: ${response.status || "received"}.`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit this decision.");
    } finally {
      setBusyId("");
    }
  }

  if (connectionState === "loading") return <LoadingState label="Checking workspace connection" />;
  if (connectionState !== "connected") return <><PageHeader eyebrow="GOVERNANCE / 02" title="Action desk" description="Inspect proposed work and record a decision through the governed API." /><ConnectionGate /></>;

  const pendingCount = actions.length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="GOVERNANCE / 02"
        title="Action desk"
        description="Review the actual proposed actions returned by the policy pipeline. Decisions are submitted to the backend; they are not local UI toggles."
        action={<RefreshButton onClick={() => void load()} busy={loading} />}
      />

      <div className="desk-summary">
        <div className="desk-summary-main">
          <span className="micro-tag">GOVERNED QUEUE</span>
          <strong>{pendingCount.toString().padStart(2, "0")} <span>awaiting decision</span></strong>
          <p>Only actions whose current status is proposed and which require approval are returned by this endpoint.</p>
        </div>
        <div className="desk-summary-side"><span>DECISION AUTHORITY</span><strong>{isUuid(config.userId) ? "Reviewer configured" : "Reviewer ID required"}</strong><small>{isUuid(config.userId) ? "User ID is set for API submissions." : "Connect settings and enter reviewer UUID to approve or reject."}</small></div>
      </div>

      {notice && <LiveNotice tone="success">{notice}</LiveNotice>}
      {error && <ErrorState title="Action request failed" message={error} onRetry={() => void load()} />}

      {loading && actions.length === 0 ? <LoadingState label="Loading proposed actions" /> : actions.length === 0 && !error ? (
        <Panel title="Queue clear" description="No proposed actions currently require human review.">
          <EmptyState title="Nothing needs a decision" description="New approval-required actions will appear here when the backend returns them." />
        </Panel>
      ) : (
        <div className="action-list">
          {actions.map((action, index) => (
            <article className="action-card" key={action.id}>
              <header className="action-card-head">
                <div className="action-card-title-wrap">
                  <div className="action-count">{String(index + 1).padStart(2, "0")}</div>
                  <div>
                    <div className="action-title-line"><h2>{humanize(action.kind)}</h2><span className={"risk-tag risk-" + Math.min(3, Math.max(1, action.risk_tier))}>RISK {action.risk_tier}</span></div>
                    <div className="action-meta-line"><code>{action.id}</code><span>Proposed {formatDate(action.proposed_at)}</span></div>
                  </div>
                </div>
                <span className="status-tag status-warning"><i />Awaiting review</span>
              </header>

              <div className="action-card-grid">
                <section className="action-detail-section">
                  <p className="detail-label">AGENT REASONING</p>
                  <p className="action-reasoning">{action.reasoning || "No reasoning was attached to this action."}</p>
                  <details className="payload-details">
                    <summary>Inspect exact payload <span>↘</span></summary>
                    <pre>{displayJson(action.payload)}</pre>
                  </details>
                </section>
                <section className="action-detail-section policy-section">
                  <p className="detail-label">RECORDED POLICY RESULTS</p>
                  <PolicySummary results={action.policy_results} />
                </section>
              </div>

              <div className="action-card-footer">
                <label className="comment-field">
                  <span>Decision note <small>OPTIONAL</small></span>
                  <input value={commentById[action.id] || ""} onChange={(event) => setCommentById((current) => ({ ...current, [action.id]: event.target.value }))} />
                </label>
                <div className="decision-buttons">
                  <button className="button button-danger" onClick={() => void decide(action, "reject")} disabled={busyId === action.id}>
                    {busyId === action.id ? "Submitting…" : "Reject"}
                  </button>
                  <button className="button button-primary" onClick={() => void decide(action, "approve")} disabled={busyId === action.id}>
                    {busyId === action.id ? "Submitting…" : "Approve action"} <span aria-hidden="true">↗</span>
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="workflow-note">
        <span className="workflow-note-index">00 / NOTE</span>
        <p>Approval can trigger the configured executor. Verify dry-run status, connector credentials, consent, and budget policy before granting approval to production actions.</p>
      </div>
    </div>
  );
}
