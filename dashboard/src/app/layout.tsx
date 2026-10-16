import type { Metadata } from "next";
import type { ReactNode } from "react";
import AppShell from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "ALLEYES — Marketing Operations",
  description: "Live business performance, governed action queues and marketing intelligence.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
