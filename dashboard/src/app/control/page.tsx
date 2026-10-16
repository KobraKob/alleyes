"use client";

import { useCallback, useEffect, useState } from "react";
import { humanize, type KillSwitchStatus } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-provider";
import {
  ConnectionGate,
  ErrorState,
  LiveNotice,
  LoadingState,
  PageHeader,
  Panel,
  RefreshButton,
} from "@/components/ui";

export default function ControlPage() {
  const { connectionState, config, request } = useWorkspace();
  const [switchStatus, setSwitchStatus] = useState<KillSwitchStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await request<KillSwitchStatus>("/v1/kill-switch/status");
      setSwitchStatus(result);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not read kill-switch status.");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (connectionState === "connected") void refresh();
  }, [connectionState, refresh]);

  async function toggleSwitch(engaged: boolean) {
    if (!reason.trim()) {
      setError("Enter a reason before changing the global kill switch.");
      return;
    }
    const verb = engaged ? "engage" : "release";
    const warning = engaged
      ? "Engage the global kill switch? The backend will cancel matching proposed or approved unexecuted actions."
      : "Release the global kill switch? New actions may proceed through the remaining policy and executor checks.";
    if (!window.confirm(warning)) return;

    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request<KillSwitchStatus & { status: string }>(
        "/v1/kill-switch",
        {
          method: "POST",
          body: JSON.stringify({
            scope: "all",
            engaged,
            user_id: config.userId.trim() || null,
            reason: reason.trim(),
          }),
        },
      );
      setSwitchStatus({ scope: result.scope, engaged: result.engaged });
      setNotice(result.engaged ? "Global kill switch is engaged in the backend." : "Global kill switch is released in the backend.");
      setReason("");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : `Could not ${verb} the kill switch.`);
    } finally {
      setBusy(false);
    }
  }

  if (connectionState === "loading") return <LoadingState label="Checking workspace connection" />;
  if (connectionState !== "connected") return <><PageHeader eyebrow="POLICY / 05" title="System control" description="Read and operate the global kill switch through the authenticated API." /><ConnectionGate /></>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="POLICY / 05"
        title="System control"
        description="Read and operate the global execution kill switch. Every state change is sent to the backend, not simulated in the browser."
        action={<RefreshButton onClick={() => void refresh()} busy={loading} />}
      />

      {notice && <LiveNotice tone="success">{notice}</LiveNotice>}
      {error && <ErrorState title="Control request failed" message={error} onRetry={() => void refresh()} />}

      <section className={"kill-switch-panel " + (switchStatus?.engaged ? "engaged" : "")}>
        <div className="kill-switch-visual" aria-hidden="true">
          <span className="kill-switch-ring"><span /></span>
          <span className="kill-switch-visual-label">GLOBAL / ALL</span>
        </div>
        <div className="kill-switch-copy">
          <div className="kill-switch-topline"><span className={"status-lamp " + (switchStatus ? switchStatus.engaged ? "red" : "green" : "grey")} />{loading && !switchStatus ? "READING STATE" : switchStatus ? switchStatus.engaged ? "HALT ENGAGED" : "HALT RELEASED" : "STATUS UNKNOWN"}</div>
          <h2>{switchStatus ? switchStatus.engaged ? "Execution halted." : "Execution can proceed." : "Check control state."}</h2>
          <p>{switchStatus
            ? switchStatus.engaged
              ? "The backend reports the global kill switch is engaged. Keep it active while investigating the underlying issue."
              : "The global kill switch is currently released. Actions must still pass the configured policy and executor checks."
            : "Read the current global kill-switch status from the business API before changing execution state."}</p>
          <div className="kill-switch-meta"><span>SCOPE <b>{switchStatus ? humanize(switchStatus.scope) : "All actions"}</b></span><span>STATE SOURCE <b>Backend API</b></span></div>
        </div>
        <div className="kill-switch-action">
          {!switchStatus?.engaged ? (
            <button className="button button-danger button-wide" onClick={() => void toggleSwitch(true)} disabled={busy || loading || !switchStatus}>
              {busy ? "Updating state…" : "Engage kill switch"} <span aria-hidden="true">⏻</span>
            </button>
          ) : (
            <button className="button button-primary button-wide" onClick={() => void toggleSwitch(false)} disabled={busy || loading}>
              {busy ? "Updating state…" : "Release kill switch"} <span aria-hidden="true">↗</span>
            </button>
          )}
          <small>Confirmation required. Reason is recorded with the change.</small>
        </div>
      </section>

      <section className="control-reason-panel">
        <label className="reason-editor">
          <span>Change reason <i>REQUIRED</i></span>
          <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} maxLength={500} />
          <small>Describe the incident or operational reason. Avoid personal customer data.</small>
        </label>
        <div className="reason-guidance">
          <strong>Before changing state</strong>
          <p>Confirm the affected business, identify queued work, and tell the team who owns the incident. Releasing the switch does not replace normal policy checks.</p>
          <div className="reason-rule" />
          <span>{reason.trim().length}/500 characters</span>
        </div>
      </section>

      <div className="dashboard-grid control-info-grid">
        <Panel title="What engagement does" description="Behaviour performed by the current backend handler.">
          <div className="control-fact-list">
            <div><span>01</span><p>Persists the global kill-switch state for this business.</p></div>
            <div><span>02</span><p>Rejects matching proposed or approved actions that have not executed yet.</p></div>
            <div><span>03</span><p>Returns the resulting state so this screen can confirm the change.</p></div>
          </div>
        </Panel>
        <Panel title="Operational boundary" description="Keep these limits visible to reviewers.">
          <div className="control-fact-list">
            <div><span>!</span><p>This UI reflects the API response; it is not an independent monitor of every connector.</p></div>
            <div><span>!</span><p>Verify worker enforcement, in-flight network requests, and provider-side campaign state during incident response.</p></div>
            <div><span>!</span><p>The current API does not expose audit-history queries. This page will not fabricate an audit table.</p></div>
          </div>
        </Panel>
      </div>
      <div className="footnote footnote-bottom">State endpoint: <code>GET /v1/kill-switch/status</code> · Change endpoint: <code>POST /v1/kill-switch</code></div>
    </div>
  );
}
