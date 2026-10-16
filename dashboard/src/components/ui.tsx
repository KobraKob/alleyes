"use client";

import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div className="page-heading-main">
        <p className="eyebrow"><span className="eyebrow-mark" />{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action && <div className="page-heading-action">{action}</div>}
    </div>
  );
}

export function SectionHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="section-heading-action">{action}</div>}
    </div>
  );
}

export function LiveNotice({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "warning" | "success" }) {
  return <div className={"live-notice " + tone}><span className="notice-symbol" aria-hidden="true">{tone === "success" ? "✓" : tone === "warning" ? "!" : "i"}</span><div>{children}</div></div>;
}

export function Panel({
  title,
  description,
  action,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{title}</h2>
          {description && <p className="panel-subtitle">{description}</p>}
        </div>
        {action && <div className="panel-header-action">{action}</div>}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function MetricCard({
  label,
  value,
  note,
  marker = "•",
  emphasis = false,
}: {
  label: string;
  value: string;
  note: string;
  marker?: string;
  emphasis?: boolean;
}) {
  return (
    <article className={"metric-card " + (emphasis ? "metric-card-emphasis" : "")}>
      <div className="metric-card-top">
        <span>{label}</span>
        <span className="metric-marker" aria-hidden="true">{marker}</span>
      </div>
      <strong className="metric-value">{value}</strong>
      <p className="metric-note">{note}</p>
    </article>
  );
}

export function LoadingState({ label = "Loading from API" }: { label?: string }) {
  return <div className="state-panel" role="status"><span className="loading-orbit" aria-hidden="true" /><strong>{label}</strong><p>Waiting for a response from the configured workspace.</p></div>;
}

export function ErrorState({
  title = "Could not load this view",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="state-panel state-error" role="alert">
      <span className="state-code">REQUEST FAILED</span>
      <strong>{title}</strong>
      <p>{message}</p>
      {onRetry && <button className="button button-outline" onClick={onRetry}>Retry request <span aria-hidden="true">↻</span></button>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true">—</span>
      <strong>{title}</strong>
      <p>{description}</p>
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

export function ConnectionGate() {
  return (
    <section className="connection-gate">
      <div className="gate-index">ALLEYES / CONNECTOR 00</div>
      <div className="gate-rule" />
      <h2>Nothing guessed.<br /><span>Everything sourced.</span></h2>
      <p>Connect a business API to load its real campaign, funnel, action, and policy data. This dashboard does not generate sample metrics.</p>
      <button className="button button-primary" onClick={() => window.dispatchEvent(new Event("alleeyes:open-connection"))}>
        Connect workspace <span aria-hidden="true">↗</span>
      </button>
      <div className="gate-foot"><span>API KEY + BUSINESS ID</span><span>SESSION ONLY</span></div>
    </section>
  );
}

export function RefreshButton({ onClick, busy = false }: { onClick: () => void; busy?: boolean }) {
  return <button className="button button-outline" onClick={onClick} disabled={busy}><span aria-hidden="true" className={busy ? "spin-icon" : ""}>↻</span>{busy ? "Refreshing" : "Refresh data"}</button>;
}
