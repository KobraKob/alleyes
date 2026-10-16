import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import AppShell from "@/components/app-shell";
import { WorkspaceProvider } from "@/components/workspace-provider";

export const metadata: Metadata = {
  title: "ALLEYES — Marketing Operations",
  description: "A connected workspace for campaign performance, governed actions, and marketing decisions.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <WorkspaceProvider>
          <AppShell>{children}</AppShell>
        </WorkspaceProvider>
      </body>
    </html>
  );
}
