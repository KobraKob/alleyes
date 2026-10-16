export type WorkspaceConnection = {
  apiBaseUrl: string;
  businessId: string;
  apiKey: string;
  reviewerId: string;
};

export type Business = {
  id: string;
  name: string;
  timezone?: string;
  currency?: string;
  brand_profile?: Record<string, unknown> | null;
  status?: string;
};

const STORAGE_KEY = "alleeyes.workspace.v1";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function readWorkspaceConnection(): WorkspaceConnection | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<WorkspaceConnection>;
    if (!parsed.apiBaseUrl || !parsed.businessId || !parsed.apiKey) return null;
    return {
      apiBaseUrl: parsed.apiBaseUrl,
      businessId: parsed.businessId,
      apiKey: parsed.apiKey,
      reviewerId: parsed.reviewerId ?? "",
    };
  } catch {
    return null;
  }
}

export function saveWorkspaceConnection(connection: WorkspaceConnection): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(connection));
  window.dispatchEvent(new Event("alleeyes:workspace-updated"));
}

export function clearWorkspaceConnection(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event("alleeyes:workspace-updated"));
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  connection: WorkspaceConnection | null = readWorkspaceConnection(),
): Promise<T> {
  if (!connection) {
    throw new ApiError("Connect a workspace to load live records.");
  }

  const base = connection.apiBaseUrl.replace(/\/+$/, "");
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", connection.apiKey);
  headers.set("X-Business-ID", connection.businessId);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(base + path, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Could not reach the ALLEYES API. Check the URL, network, and API CORS settings.");
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : typeof payload === "string" && payload
          ? payload
          : response.statusText;
    throw new ApiError(detail || "The API returned an error.", response.status);
  }

  return payload as T;
}

export async function verifyWorkspace(connection: WorkspaceConnection): Promise<Business> {
  const base = connection.apiBaseUrl.replace(/\/+$/, "");
  let health: Response;
  try {
    health = await fetch(base + "/health", { cache: "no-store" });
  } catch {
    throw new ApiError("Could not reach /health. Check the API URL and network.");
  }
  if (!health.ok) throw new ApiError("API health check failed.", health.status);

  const business = await apiFetch<Business>("/v1/businesses", {}, connection);
  if (!business?.id || !business?.name) {
    throw new ApiError("The API responded, but did not return a business profile.");
  }
  return business;
}

export function formatInteger(value: number): string {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
}

export function formatCurrencyMinor(value: number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: /^[A-Z]{3}$/.test(currency) ? currency : "INR",
    maximumFractionDigits: 0,
  }).format(value / 100);
}

export function formatDate(value?: string | null): string {
  if (!value) return "Date not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function humanizeKey(value: string): string {
  return value.replace(/[._-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "Not recorded";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return remaining ? `${minutes}m ${remaining}s` : `${minutes} min`;
}
