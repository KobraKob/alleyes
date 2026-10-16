"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  isUuid,
  type ApiConfig,
} from "@/lib/api";
import { useWorkspace } from "@/components/workspace-provider";

const navigation = [
  { href: "/", label: "Overview", number: "01", glyph: "◫" },
  { href: "/approvals", label: "Action desk", number: "02", glyph: "⌁" },
  { href: "/performance", label: "Performance", number: "03", glyph: "↗" },
  { href: "/learning", label: "Learning lab", number: "04", glyph: "◉" },
  { href: "/control", label: "System control", number: "05", glyph: "⊙" },
];

function ConnectionDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { config, connect, disconnect, connectionState, connectionMessage, business } = useWorkspace();
  const [form, setForm] = useState<ApiConfig>(config);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setForm(config);
      setError("");
    }
  }, [open, config]);

  if (!open) return null;

  const change = (key: keyof ApiConfig, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!isUuid(form.businessId)) {
      setError("Business ID must be a valid UUID.");
      return;
    }
    if (form.userId.trim() && !isUuid(form.userId)) {
      setError("Reviewer user ID must be a valid UUID, or leave it empty.");
      return;
    }
    try {
      await connect(form);
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not connect.");
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="connection-dialog" role="dialog" aria-modal="true" aria-labelledby="connection-title">
        <div className="dialog-top">
          <div className="brand-symbol" aria-hidden="true"><span /><span /><span /></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close connection settings">×</button>
        </div>
        <p className="eyebrow">WORKSPACE CONNECTION</p>
        <h2 id="connection-title">Connect ALLEYES</h2>
        <p className="dialog-description">
          Use your deployed API or local backend. Credentials stay in this browser tab and are not committed to the repository.
        </p>
        <form onSubmit={submit} className="connection-form">
          <label>
            <span>API base URL</span>
            <input
              type="url"
              required
              value={form.apiUrl}
              onChange={(event) => change("apiUrl", event.target.value)}
              autoComplete="url"
            />
            <small>Base address only. Do not append an API route.</small>
          </label>
          <label>
            <span>Business ID</span>
            <input
              type="text"
              required
              value={form.businessId}
              onChange={(event) => change("businessId", event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label>
            <span>Business API key</span>
            <input
              type="password"
              required
              value={form.apiKey}
              onChange={(event) => change("apiKey", event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label>
            <span>Reviewer user ID <small className="optional-label">OPTIONAL</small></span>
            <input
              type="text"
              value={form.userId}
              onChange={(event) => change("userId", event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            <small>Required for approving or rejecting actions.</small>
          </label>
          {(error || connectionState === "error") && (
            <div className="form-error" role="alert">{error || connectionMessage}</div>
          )}
          {connectionState === "connected" && business && (
            <div className="form-success" role="status">
              Connected to {business.name}. Data is fetched from the configured API.
            </div>
          )}
          <button className="button button-primary button-wide" type="submit" disabled={connectionState === "loading"}>
            {connectionState === "loading" ? "Checking connection…" : "Verify & connect"}
            <span aria-hidden="true">↗</span>
          </button>
        </form>
        <div className="dialog-footer">
          <span>API keys are held in session storage.</span>
          {connectionState === "connected" && (
            <button type="button" className="text-button danger-text" onClick={() => { disconnect(); onClose(); }}>
              Disconnect
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

function Brand() {
  return (
    <Link href="/" className="brand-lockup" aria-label="ALLEYES overview">
      <span className="brand-symbol" aria-hidden="true"><span /><span /><span /></span>
      <span className="brand-type">ALLEYES<span className="brand-dot">.</span><small>MARKETING OPERATIONS</small></span>
    </Link>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { connectionState, connectionMessage, business } = useWorkspace();
  const [connectionOpen, setConnectionOpen] = useState(false);
  const currentPage = navigation.find((item) => item.href === pathname) ?? navigation[0];
  const linked = connectionState === "connected";

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="app-frame">
        <aside className="sidebar">
          <Brand />
          <div className={"workspace-card " + (linked ? "is-connected" : "")}>
            <div className="workspace-avatar">{linked ? business?.name?.slice(0, 2).toUpperCase() : "—"}</div>
            <div className="workspace-card-copy">
              <strong>{linked ? business?.name : "No workspace linked"}</strong>
              <span>{linked ? business?.status || "Business workspace" : "Connect to load live data"}</span>
            </div>
            <button className="workspace-edit" onClick={() => setConnectionOpen(true)} aria-label="Workspace connection settings">↗</button>
          </div>
          <div className="nav-section-label">OPERATIONS <span>/{navigation.length.toString().padStart(2, "0")}</span></div>
          <nav className="main-nav" aria-label="Main navigation">
            {navigation.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link key={item.href} href={item.href} className={"nav-link " + (active ? "active" : "")} aria-current={active ? "page" : undefined}>
                  <span className="nav-glyph" aria-hidden="true">{item.glyph}</span>
                  <span className="nav-label">{item.label}</span>
                  <span className="nav-number">{item.number}</span>
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-bottom">
            <div className="connection-status">
              <span className={"connection-indicator " + (linked ? "online" : connectionState === "loading" ? "pending" : "offline")} />
              <div>
                <strong>{linked ? "API connected" : connectionState === "loading" ? "Checking API" : "API not connected"}</strong>
                <p>{linked ? "Authenticated business context" : "No metrics are fabricated"}</p>
              </div>
            </div>
            <button className="sidebar-connection-button" onClick={() => setConnectionOpen(true)}>
              {linked ? "Connection settings" : "Connect workspace"} <span aria-hidden="true">↗</span>
            </button>
            <div className="sidebar-footnote"><span>ALLEYES</span><span>BUILD / LIVE DATA FIRST</span></div>
          </div>
        </aside>

        <main className="main-area" id="main-content">
          <header className="topbar">
            <div className="topbar-page">
              <span className="topbar-section">WORKSPACE</span>
              <span className="crumb-divider">/</span>
              <strong>{currentPage.label.toUpperCase()}</strong>
            </div>
            <div className="topbar-controls">
              <span className={"connection-chip " + (linked ? "connected" : "")}>
                <i />{linked ? "CONNECTED" : connectionState === "loading" ? "CHECKING" : "NOT CONNECTED"}
              </span>
              <button className="button button-outline top-connect" onClick={() => setConnectionOpen(true)}>
                {linked ? "Workspace" : "Connect API"} <span aria-hidden="true">↗</span>
              </button>
              <div className="profile-mark" aria-label="ALLEYES workspace">A</div>
            </div>
          </header>
          <div className="page-content">{children}</div>
          <footer className="page-footer">
            <span>ALLEYES <i>×</i> DECISION SYSTEMS</span>
            <span>{linked ? business?.name : "AWAITING WORKSPACE CONNECTION"}</span>
          </footer>
        </main>
      </div>
      <ConnectionDialog open={connectionOpen} onClose={() => setConnectionOpen(false)} />
    </>
  );
}
