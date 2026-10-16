import type { ReactNode } from "react";

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow"><span className="eyebrow-marker" aria-hidden="true" />{children}</div>;
}

export function PageHeading({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div className="page-heading-copy">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className="heading-actions">{actions}</div> : null}
    </div>
  );
}

export function SectionHeading({
  title,
  description,
  trailing,
}: {
  title: string;
  description?: string;
  trailing?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {trailing ? <div className="section-trailing">{trailing}</div> : null}
    </div>
  );
}

export function Surface({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`surface ${className}`.trim()}>{children}</section>;
}

export function PanelHeading({
  title,
  detail,
  trailing,
}: {
  title: string;
  detail?: string;
  trailing?: ReactNode;
}) {
  return (
    <div className="surface-header">
      <div>
        <h2>{title}</h2>
        {detail ? <p>{detail}</p> : null}
      </div>
      {trailing ? <div className="surface-trailing">{trailing}</div> : null}
    </div>
  );
}

export function Metric({
  label,
  value,
  detail,
  index,
}: {
  label: string;
  value: string;
  detail?: string;
  index: string;
}) {
  return (
    <div className="metric">
      <div className="metric-top"><span>{label}</span><span className="metric-index">{index}</span></div>
      <div className="metric-value">{value}</div>
      {detail ? <div className="metric-detail">{detail}</div> : null}
    </div>
  );
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-marker" aria-hidden="true">—</span>
      <div>
        <h3>{title}</h3>
        <p>{detail}</p>
        {action ? <div className="empty-action">{action}</div> : null}
      </div>
    </div>
  );
}

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="notice notice-error" role="alert">
      <span className="notice-symbol" aria-hidden="true">!</span>
      <div className="notice-copy"><strong>Request failed</strong><p>{message}</p></div>
      {onRetry ? <button className="button button-quiet" onClick={onRetry}>Retry</button> : null}
    </div>
  );
}

export function ConnectPrompt() {
  return (
    <Surface className="connect-prompt">
      <div className="connect-prompt-mark" aria-hidden="true">↗</div>
      <div>
        <Eyebrow>WORKSPACE / CONNECTION REQUIRED</Eyebrow>
        <h2>Your business data belongs here.</h2>
        <p>Connect an ALLEYES API workspace to load real leads, campaigns, objectives and governed actions. No demo figures are substituted.</p>
        <button className="button button-primary" onClick={() => window.dispatchEvent(new Event("alleeyes:open-connection"))}>Connect workspace <span aria-hidden="true">↗</span></button>
      </div>
    </Surface>
  );
}

export function LoadingState({ label = "Loading records from ALLEYES API" }: { label?: string }) {
  return <div className="loading-state" role="status"><span className="loading-line" /><span>{label}</span></div>;
}
