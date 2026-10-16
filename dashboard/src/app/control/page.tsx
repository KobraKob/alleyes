"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, formatDate, humanizeKey } from "@/lib/api";
import { useWorkspace } from "@/lib/use-workspace";
import { ConnectPrompt, EmptyState, ErrorNotice, LoadingState, Metric, PageHeading, PanelHeading, SectionHeading, Surface } from "@/components/primitives";

type Probe = { status: string; engine?: string; database?: string };

export default function ControlPage() {
  const { connection, business, checking, connectionError, reload } = useWorkspace();
  const [health, setHealth] = useState<Probe | null>(null);
  const [readiness, setReadiness] = useState<Probe | null>(null);
  const [probeLoading, setProbeLoading] = useState(false);
  const [probeError, setProbeError] = useState("");
  const [killSwitch, setKillSwitch] = useState<boolean | null>(null);
  const [killScope, setKillScope] = useState("all");
  const [killReason, setKillReason] = useState("");
  const [killBusy, setKillBusy] = useState(false);
  const [killMessage, setKillMessage] = useState("");
  const [killError, setKillError] = useState("");
  const [lastCommandAt, setLastCommandAt] = useState<string | null>(null);

  const runProbes = useCallback(async () => {
    if (!connection || !business?.id) return;
    setProbeLoading(true);
    setProbeError("");
    const outcomes = await Promise.allSettled([
      apiFetch<Probe>("/health", {}, connection),
      apiFetch<Probe>("/ready", {}, connection),
    ]);
    if (outcomes[0].status === "fulfilled") setHealth(outcomes[0].value);
    else setProbeError(outcomes[0].reason instanceof Error ? outcomes[0].reason.message : "Liveness probe failed.");
    if (outcomes[1].status === "fulfilled") setReadiness(outcomes[1].value);
    else {
      setReadiness(null);
      setProbeError((previous) => [previous, outcomes[1].reason instanceof Error ? outcomes[1].reason.message : "Readiness probe failed."].filter(Boolean).join(" "));
    }
    setProbeLoading(false);
  }, [connection, business?.id]);

  useEffect(() => {
    if (connection && business?.id) void runProbes();
  }, [connection, business?.id, runProbes]);

  const sendKillSwitch = async (engaged: boolean) => {
    if (!connection || !business?.id) return;
    const confirmation = engaged
      ? "Engage the " + killScope + " kill switch? This changes backend execution controls for this business."
      : "Release the " + killScope + " kill switch? This may allow governed actions to execute again. Verify the existing halt state outside this UI first.";
    if (!window.confirm(confirmation)) return;

    setKillBusy(true);
    setKillError("");
    setKillMessage("");
    try {
      const result = await apiFetch<{ status: string; scope: string; engaged: boolean }>(
        "/v1/kill-switch",
        {
          method: "POST",
          body: JSON.stringify({
            scope: killScope,
            engaged,
            reason: killReason.trim() || "Manual kill-switch command from ALLEYES system control.",
          }),
        },
        connection,
      );
      setKillSwitch(result.engaged);
      setLastCommandAt(new Date().toISOString());
      setKillMessage("API confirmed scope '" + result.scope + "' updated. Engaged = " + String(result.engaged) + ".");
      setKillReason("");
    } catch (error) {
      setKillError(error instanceof Error ? error.message : "Kill-switch request failed.");
    } finally {
      setKillBusy(false);
    }
  };

  if (checking) return <LoadingState label="Checking workspace connection" />;
  if (!connection) return <ConnectPrompt />;
  if (!business) return <><ErrorNotice message={connectionError || "Workspace connection could not be verified."} onRetry={() => { void reload(); }} /><ConnectPrompt /></>;

  return (
    <div className="page">
      <PageHeading
        eyebrow="POLICY & OVERSIGHT / SYSTEM CONTROL"
        title="Controls must be real."
        description="Inspect API readiness and issue explicit kill-switch commands. Controls without read endpoints remain marked unknown."
        actions={<button className="button button-primary" onClick={() => void runProbes()} disabled={probeLoading}>{probeLoading ? "Probing…" : "↻ Run health checks"}</button>}
      />

      {probeError ? <ErrorNotice message={probeError} onRetry={() => { void runProbes(); }} /> : null}
      {killMessage ? <div className="notice"><span className="notice-symbol">✓</span><div className="notice-copy"><strong>Command response received</strong><p>{killMessage} {lastCommandAt ? "Returned " + formatDate(lastCommandAt) + "." : ""}</p></div><button className="button button-quiet" onClick={() => setKillMessage("")}>Dismiss</button></div> : null}
      {killError ? <ErrorNotice message={killError} /> : null}

      <div className="metrics-grid">
        <Metric index="01" label="API liveness" value={health?.status ? humanizeKey(health.status) : probeLoading ? "Checking" : "Unknown"} detail={health?.engine ? "Service: " + health.engine : "GET /health"} />
        <Metric index="02" label="Database readiness" value={readiness?.database ? humanizeKey(readiness.database) : probeLoading ? "Checking" : "Unknown"} detail="GET /ready verifies database connectivity" />
        <Metric index="03" label="Kill-switch state" value={killSwitch === null ? "Unknown" : killSwitch ? "Engaged" : "Released"} detail={killSwitch === null ? "No GET status endpoint exists; state is not guessed." : "Last confirmed command response only"} />
        <Metric index="04" label="Business status" value={humanizeKey(business.status || "unknown")} detail={business.name} />
      </div>

      <section className={"control-banner" + (killSwitch === true ? " is-engaged" : "")}>
        <div className="control-copy">
          <div className="panel-kicker">EMERGENCY EXECUTION CONTROL</div>
          <h2>Business kill switch</h2>
          <div className={"control-state" + (killSwitch === true ? " is-engaged" : "")}><i />{killSwitch === null ? "CURRENT STATE NOT QUERIED" : killSwitch ? "LAST COMMAND: ENGAGED" : "LAST COMMAND: RELEASED"}</div>
          <p>The endpoint accepts an explicit scope and engaged flag. There is no read endpoint for existing switch state, so a page refresh correctly returns this control to “Unknown”. Confirm the scope and business before sending a command.</p>
        </div>
        <div className="kill-form">
          <label>Scope<select value={killScope} onChange={(event) => setKillScope(event.target.value)}><option value="all">All actions</option><option value="whatsapp">WhatsApp</option><option value="meta_ads">Meta Ads</option><option value="email">Email</option><option value="campaign">Campaigns</option></select></label>
          <label>Reason <span className="label-optional">OPTIONAL</span><input value={killReason} onChange={(event) => setKillReason(event.target.value)} /></label>
          <div className="button-row"><button className="button button-danger" onClick={() => void sendKillSwitch(true)} disabled={killBusy}>{killBusy ? "Sending…" : "Engage switch"}</button><button className="button button-quiet" onClick={() => void sendKillSwitch(false)} disabled={killBusy}>{killBusy ? "Sending…" : "Release switch"}</button></div>
        </div>
      </section>

      <div className="content-grid content-grid-equal">
        <Surface>
          <PanelHeading title="Business context" detail="Read from the authenticated business record" trailing={<span className="panel-kicker">LIVE</span>} />
          <div className="surface-body definition-list">
            <div className="definition-row"><strong>Business name</strong><span>{business.name}</span></div>
            <div className="definition-row"><strong>Business ID</strong><span>{business.id}</span></div>
            <div className="definition-row"><strong>Timezone</strong><span>{business.timezone || "Not configured"}</span></div>
            <div className="definition-row"><strong>Currency</strong><span>{business.currency || "Not configured"}</span></div>
            <div className="definition-row"><strong>Business status</strong><span>{humanizeKey(business.status || "unknown")}</span></div>
          </div>
        </Surface>
        <Surface>
          <PanelHeading title="Available control surfaces" detail="Endpoints exposed by the current backend" />
          <div className="surface-body definition-list">
            <div className="definition-row"><strong>Health probes</strong><span className="status-chip">GET /health · GET /ready</span></div>
            <div className="definition-row"><strong>Kill switch</strong><span className="status-chip">POST /v1/kill-switch</span></div>
            <div className="definition-row"><strong>Approval queue</strong><span className="status-chip">GET /v1/actions</span></div>
            <div className="definition-row"><strong>Autonomy policy read/write</strong><span className="status-chip warn">Not exposed here</span></div>
            <div className="definition-row"><strong>Audit-log query</strong><span className="status-chip warn">Not exposed here</span></div>
          </div>
        </Surface>
      </div>

      <SectionHeading title="Control-plane gaps" description="Capabilities are not represented as active until the backend exposes tenant-scoped endpoints." />
      <Surface>
        <EmptyState title="No policy matrix or audit timeline is available from the current API" detail="The frontend no longer fabricates autonomy levels or audit rows. Add authenticated read/write endpoints for autonomy policies and immutable audit events before exposing those controls." />
      </Surface>
    </div>
  );
}
