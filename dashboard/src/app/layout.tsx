import React from "react";
import "./globals.css";

export const metadata = {
  title: "Autonomous Marketing Engine",
  description: "Governance, Performance, Learning & Control",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 font-sans min-h-screen">
        <header className="bg-slate-900 text-white shadow">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse"></span>
              <h1 className="text-xl font-bold tracking-tight">Autonomous Marketing Engine</h1>
              <span className="text-xs bg-slate-800 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">v1.0 (Gym)</span>
            </div>
            <nav className="flex space-x-6 text-sm font-medium">
              <a href="/approvals" className="hover:text-emerald-400 transition-colors">1. Approval Queue</a>
              <a href="/performance" className="hover:text-emerald-400 transition-colors">2. Performance</a>
              <a href="/learning" className="hover:text-emerald-400 transition-colors">3. Learning</a>
              <a href="/control" className="hover:text-emerald-400 transition-colors">4. Control</a>
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
