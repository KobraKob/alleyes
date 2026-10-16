"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  clearWorkspaceConnection,
  saveWorkspaceConnection,
  verifyWorkspace,
  type WorkspaceConnection,
} from "@/lib/api";
import { useWorkspace } from "@/lib/use-workspace";

const navigation = [
  { href: "/", icon: "◫", label: "Overview", note: "Business pulse" },
  { href: "/approvals", icon: "↳", label: "Action desk", note: "Review proposed work" },
  { href: "/performance", icon: "⌁", label: "Performance", note: "Outcomes & spend" },
  { href: "/learning", icon: "⊹", label: "Learning lab", note: "Evidence & insights" },
  { href: "/control", icon: "⛭", label: "System control", note: "Safety & health" },
];

function ConnectionDialog({
  open,
  onClose,
  current,
}: {
  open: boolean;
  onClose: () => void;
  current: WorkspaceConnection | null;
}) {
  const [form, setForm] = useState<WorkspaceConnection>({
    apiBaseUrl: "",
    businessId: "",
    apiKey: "",
    reviewerId: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setForm({
      apiBaseUrl: current?.apiBaseUrl ?? process.env.NEXT_PUBLIC_ALLEYES_API_URL ?? "",
      businessId: current?.businessId ?? "",
      apiKey: current?.apiKey ?? "",
      reviewerId: current?.reviewerId ?? "",
    });
    setError("");
  }, [open, current]);

  if (!open) return null;

  const update = (key: keyof WorkspaceConnection, value: string) => {
    setForm((previous) => ({ ...previous, [key]: value }));
  };

  const connect = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const candidate = {
      apiBaseUrl: form.apiBaseUrl.trim().replace(/\/+$/, ""),
      businessId: form.businessId.trim(),
      apiKey: form.apiKey.trim(),
      reviewerId: form.reviewerId.trim(),
    };
    try {
      const parsedUrl = new URL(candidate.apiBaseUrl);
      if (!["https:", "http:"].includes(parsedUrl.protocol)) {
        throw new Error("Use an HTTP or HTTPS API URL.");
      }
      await verifyWorkspace(candidate);
      saveWorkspaceConnection(candidate);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to connect workspace.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="connection-dialog" role="dialog" aria-modal="true" aria-labelledby="connection-title">
        <div className="dialog-top">
          <div><div className="eyebrow"><span className="eyebrow-marker" /> WORKSPACE CONFIGURATION</div><h2 id="connection-title">Connect ALLEYES</h2></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close connection settings">×</button>
        </div>
        <p className="dialog-intro">Connect to your API to load actual workspace records. Credentials stay in this browser session and are cleared when the session ends.</p>
        <form onSubmit={connect} className="connection-form">
          <label>API base URL<input required type="url" autoComplete="url" value={form.apiBaseUrl} onChange={(event) => update("apiBaseUrl", event.target.value)} /></label>
          <label>Business ID<input required value={form.businessId} onChange={(event) => update("businessId", event.target.value)} autoComplete="off" /></label>
          <label>API key<input required type="password" value={form.apiKey} onChange={(event) => update("apiKey", event.target.value)} autoComplete="off" /></label>
          <label>Reviewer user ID <span className="label-optional">OPTIONAL · REQUIRED TO APPROVE ACTIONS</span><input value={form.reviewerId} onChange={(event) => update("reviewerId", event.target.value)} autoComplete="off" /></label>
          <p className="form-help">The API must allow this dashboard origin in CORS. Never use a browser-exposed key with broader permissions than this workspace requires.</p>
          {error ? <div className="form-error" role="alert">{error}</div> : null}
          <div className="dialog-actions">
            {current ? <button type="button" className="button button-quiet" onClick={() => { clearWorkspaceConnection(); onClose(); }}>Disconnect</button> : <span />}
            <button type="button" className="button button-quiet" onClick={onClose}>Cancel</button>
            <button type="submit" className="button button-primary" disabled={busy}>{busy ? "Verifying…" : "Verify & connect"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { connection, business, checking, connectionError } = useWorkspace();
  const [connectionOpen, setConnectionOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const openDialog = () => setConnectionOpen(true);
    window.addEventListener("alleeyes:open-connection", openDialog);
    return () => window.removeEventListener("alleeyes:open-connection", openDialog);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const active = navigation.find((item) => item.href === pathname);
  const status = business ? "CONNECTED" : checking ? "CHECKING API" : connection ? "CONNECTION ERROR" : "NOT CONNECTED";

  return (
    <div className="app-shell">
      {mobileOpen ? <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <Link href="/" className="brand-lockup" aria-label="ALLEYES overview">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <span className="brand-word">ALLEYES<span className="brand-period">.</span><small>MARKETING OPERATIONS</small></span>
        </Link>
        <button className="workspace-switcher" onClick={() => setConnectionOpen(true)}>
          <span className="workspace-avatar">{business?.name?.slice(0, 2).toUpperCase() ?? "↗"}</span>
          <span className="workspace-copy"><strong>{business?.name ?? "Connect workspace"}</strong><small>{business ? business.status ?? "Business workspace" : "Live data · API connection"}</small></span>
          <span className="switcher-chevron">⌄</span>
        </button>
        <div className="nav-label">COMMAND CENTER <span>05</span></div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map((item, index) => (
            <Link href={item.href} key={item.href} aria-current={active?.href === item.href ? "page" : undefined} className={`nav-item ${active?.href === item.href ? "nav-item-active" : ""}`}>
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span className="nav-copy"><strong>{item.label}</strong><small>{item.note}</small></span>
              <span className="nav-index">{String(index + 1).padStart(2, "0")}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="connection-card" onClick={() => setConnectionOpen(true)}>
            <span className={`connection-light ${business ? "is-online" : connectionError ? "is-error" : ""}`} />
            <span className="connection-card-copy"><strong>{status}</strong><small>{business ? "API credentials verified" : connectionError ? "Check connection settings" : "Connect to load live records"}</small></span>
            <span aria-hidden="true">↗</span>
          </button>
          <div className="sidebar-foot"><span>ALLEYES / 01</span><span>WORKSPACE</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation">☰</button>
            <div className="breadcrumb"><span>ALLEYES</span><span className="crumb-slash">/</span><strong>{active?.label.toUpperCase() ?? "WORKSPACE"}</strong></div>
          </div>
          <div className="topbar-right">
            <span className={`connection-badge ${business ? "badge-online" : connectionError ? "badge-error" : ""}`}><i />{status}</span>
            <button className="button button-small button-quiet" onClick={() => setConnectionOpen(true)}>{business ? "Workspace settings" : "Connect workspace"} <span aria-hidden="true">↗</span></button>
          </div>
        </header>
        <div className="page-content">{connectionError ? <div className="global-connection-warning"><strong>Workspace is not responding.</strong><span>{connectionError}</span><button className="button button-quiet" onClick={() => setConnectionOpen(true)}>Fix connection</button></div> : null}{children}</div>
        <footer className="page-footer"><span>ALLEYES INTELLIGENCE</span><span>{business ? `${business.timezone ?? "BUSINESS TIMEZONE"} · ${business.currency ?? "CURRENCY"}` : "NO LIVE DATA UNTIL A WORKSPACE IS CONNECTED"}</span></footer>
      </main>

      <ConnectionDialog open={connectionOpen} onClose={() => setConnectionOpen(false)} current={connection} />
    </div>
  );
}
