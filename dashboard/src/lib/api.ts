export type ApiConfig = {
  apiUrl: string;
  apiKey: string;
  businessId: string;
  userId: string;
};

export type Business = {
  id: string;
  name: string;
  timezone: string;
  currency: string;
  brand_profile: Record<string, unknown> | null;
  status: string;
};

export type Location = {
  id: string;
  name: string;
  city: string | null;
  capacity: number | null;
  catchment_m: number | null;
};

export type PackSummary = {
  slug: string;
  version: string;
  name: string;
  channels: string[];
  funnel_stage_count: number;
  decision_point_count: number;
};

export type VerticalPack = {
  slug: string;
  version: string | number;
  name: string;
  funnel_stages?: Array<Record<string, unknown> & { key: string; label?: string; name?: string }>;
  decision_points?: Array<Record<string, unknown> & { key: string; description?: string }>;
  channels?: string[];
  compliance?: Record<string, unknown>;
};

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

export type PlaybookInsight = {
  id: string;
  statement: string;
  evidence: unknown;
  confidence: number;
  status: string;
  expires_at: string | null;
  created_at: string | null;
};

export type ProposedAction = {
  id: string;
  kind: string;
  payload: Record<string, unknown>;
  risk_tier: number;
  reasoning: string | null;
  policy_results: Record<string, unknown>;
  proposed_at: string | null;
};

export type KillSwitchStatus = {
  scope: string;
  engaged: boolean;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const DEFAULT_API_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_ALLEYES_API_URL) ||
  "http://localhost:8000";

export const SESSION_CONFIG_KEY = "alleeyes.workspace.v1";

export function cleanApiUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function hasConnectionDetails(config: ApiConfig): boolean {
  return Boolean(cleanApiUrl(config.apiUrl) && config.apiKey.trim() && config.businessId.trim());
}

export function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.trim());
}

export async function apiRequest<T>(
  config: ApiConfig,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (!hasConnectionDetails(config)) {
    throw new ApiError("Connect an API URL, API key, and business ID first.");
  }

  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("X-API-Key", config.apiKey.trim());
  headers.set("X-Business-ID", config.businessId.trim());
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(cleanApiUrl(config.apiUrl) + path, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Could not reach the API. Check the URL, server status, and CORS_ORIGINS configuration.",
    );
  }

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: string; message?: string };
      message = body.detail || body.message || message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function formatCurrencyMinor(amountMinor: number, currency = "INR"): string {
  const normalizedCurrency = currency || "INR";
  const zeroDecimal = ["BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"].includes(normalizedCurrency.toUpperCase());
  const amount = amountMinor / (zeroDecimal ? 1 : 100);
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: normalizedCurrency,
      maximumFractionDigits: zeroDecimal ? 0 : 2,
    }).format(amount);
  } catch {
    return `${normalizedCurrency} ${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  }
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds <= 0) {
    return "No data";
  }
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${remainder}m` : `${hours}h`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Timestamp unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Timestamp unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}
