import React from "react";
import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "ALLEYES — Marketing Intelligence",
  description: "Marketing operations, lead intelligence, governed automation and measurable growth.",
};

const navigation = [
  { href: "/approvals", index: "01", label: "Action desk", note: "Review & govern" },
  { href: "/performance", index: "02", label: "Performance", note: "Commercial outcomes" },
  { href: "/learning", index: "03", label: "Learning lab", note: "Test & understand" },
  { href: "/control", index: "04", label: "System control", note: "Policies & audit" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link href="/approvals" className="brand-lockup" aria-label="ALLEYES home">
              <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
              <span className="brand-word">ALL<span>EYES</span><small>MARKETING INTELLIGENCE</small></span>
            </Link>
            <div className="workspace-switcher">
              <span className="workspace-avatar">IF</span>
              <span className="workspace-copy"><strong>Iron Fitness</strong><small>Demo workspace · Gym</small></span>
              <span className="switcher-chevron">⌄</span>
            </div>
            <div className="nav-label">WORKSPACE</div>
            <nav className="main-nav" aria-label="Main navigation">
              {navigation.map((item) => (
                <Link href={item.href} key={item.href} className="nav-item">
                  <span className="nav-index">{item.index}</span>
                  <span className="nav-copy"><strong>{item.label}</strong><small>{item.note}</small></span>
                  <span className="nav-arrow">↗</span>
                </Link>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <div className="environment-card">
                <div className="environment-heading"><span className="status-dot" /> SAFE ENVIRONMENT</div>
                <strong>Dry-run enabled</strong>
                <p>Actions are simulated. No messages sent and no ad spend changed.</p>
                <div className="environment-rule"><span>LIVE SENDS</span><b>DISABLED</b></div>
              </div>
              <div className="sidebar-footer"><span>ALLEYES / 01</span><span>BUILD PREVIEW</span></div>
            </div>
          </aside>
          <main className="main-area">
            <header className="topbar">
              <div className="breadcrumb"><span>WORKSPACE</span><span className="crumb-slash">/</span><strong>MARKETING OPERATIONS</strong></div>
              <div className="topbar-right"><span className="demo-tag"><i /> DEMONSTRATION DATA</span><span className="topbar-divider" /><span className="user-avatar">K</span></div>
            </header>
            <div className="page-content">{children}</div>
            <footer className="page-footer"><span>ALLEYES INTELLIGENCE PLATFORM</span><span>DEMO DATA · NOT CONNECTED TO LIVE ACCOUNTS</span></footer>
          </main>
        </div>
      </body>
    </html>
  );
}
