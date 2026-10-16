"use client";

import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  type Business,
  type WorkspaceConnection,
} from "@/lib/api";
import { useWorkspace } from "@/lib/use-workspace";

export type WeeklyReport = {
  funnel: Record<string, number>;
  avg_first_response_seconds: number;
};
export type CampaignReport = {
  campaign_id: string;
  name: string;
  reward: number;
  spend_minor: number;
  reward_per_rupee: number;
};
export type Objective = {
  id: string;
  statement: string;
  target_value: number;
  budget_minor: number;
  constraints: Record<string, unknown>;
  status: string;
};
export type Location = {
  id: string;
  name: string;
  city: string | null;
  capacity: number | null;
  catchment_m: number | null;
};
export type Insight = {
  id: string;
  statement: string;
  evidence: unknown;
  confidence: number;
  status: string;
  expires_at: string | null;
  created_at: string | null;
};
export type PackSummary = {
  slug: string;
  name: string;
  version: string;
  channels: string[];
  funnel_stage_count: number;
  decision_point_count: number;
};

type DataState = {
  weekly: WeeklyReport | null;
  campaigns: CampaignReport[] | null;
  objectives: Objective[] | null;
  locations: Location[] | null;
  insights: Insight[] | null;
  packs: PackSummary[] | null;
};
type EndpointResult = {
  key: keyof DataState;
  data?: DataState[keyof DataState];
  error?: string;
};

const emptyData: DataState = {
  weekly: null,
  campaigns: null,
  objectives: null,
  locations: null,
  insights: null,
  packs: null,
};

export function useOperationalData() {
  const workspace = useWorkspace();
  const { connection, business } = workspace;
  const [data, setData] = useState<DataState>(emptyData);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!connection || !business?.id) return;
    setLoading(true);
    const jobs: Array<Promise<EndpointResult>> = [
      apiFetch<WeeklyReport>("/v1/reports/weekly", {}, connection)
        .then((value) => ({ key: "weekly", data: value }))
        .catch((error: unknown) => ({ key: "weekly", error: error instanceof Error ? error.message : "Unable to load funnel report." })),
      apiFetch<CampaignReport[]>("/v1/reports/campaigns", {}, connection)
        .then((value) => ({ key: "campaigns", data: value }))
        .catch((error: unknown) => ({ key: "campaigns", error: error instanceof Error ? error.message : "Unable to load campaigns." })),
      apiFetch<Objective[]>("/v1/objectives", {}, connection)
        .then((value) => ({ key: "objectives", data: value }))
        .catch((error: unknown) => ({ key: "objectives", error: error instanceof Error ? error.message : "Unable to load objectives." })),
      apiFetch<Location[]>("/v1/locations", {}, connection)
        .then((value) => ({ key: "locations", data: value }))
        .catch((error: unknown) => ({ key: "locations", error: error instanceof Error ? error.message : "Unable to load locations." })),
      apiFetch<Insight[]>("/v1/insights", {}, connection)
        .then((value) => ({ key: "insights", data: value }))
        .catch((error: unknown) => ({ key: "insights", error: error instanceof Error ? error.message : "Unable to load insights." })),
      apiFetch<PackSummary[]>("/v1/packs", {}, connection)
        .then((value) => ({ key: "packs", data: value }))
        .catch((error: unknown) => ({ key: "packs", error: error instanceof Error ? error.message : "Unable to load business packs." })),
    ];

    const results = await Promise.all(jobs);
    const nextErrors: Record<string, string> = {};
    const updates: Partial<DataState> = {};
    for (const result of results) {
      if (result.error) {
        nextErrors[result.key] = result.error;
        switch (result.key) {
          case "weekly": updates.weekly = null; break;
          case "campaigns": updates.campaigns = null; break;
          case "objectives": updates.objectives = null; break;
          case "locations": updates.locations = null; break;
          case "insights": updates.insights = null; break;
          case "packs": updates.packs = null; break;
        }
        continue;
      }
      switch (result.key) {
        case "weekly":
          updates.weekly = result.data as WeeklyReport;
          break;
        case "campaigns":
          updates.campaigns = result.data as CampaignReport[];
          break;
        case "objectives":
          updates.objectives = result.data as Objective[];
          break;
        case "locations":
          updates.locations = result.data as Location[];
          break;
        case "insights":
          updates.insights = result.data as Insight[];
          break;
        case "packs":
          updates.packs = result.data as PackSummary[];
          break;
      }
    }
    setData((previous) => ({ ...previous, ...updates }));
    setErrors(nextErrors);
    setLastUpdated(new Date().toISOString());
    setLoading(false);
  }, [connection, business]);

  useEffect(() => {
    if (!connection || !business?.id) return;
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 30_000);
    return () => window.clearInterval(timer);
  }, [connection, business?.id, refresh]);

  return {
    ...workspace,
    data,
    errors,
    loading,
    lastUpdated,
    refresh,
  };
}

export type WorkspaceView = {
  connection: WorkspaceConnection | null;
  business: Business | null;
};
