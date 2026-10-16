"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  apiRequest,
  cleanApiUrl,
  DEFAULT_API_URL,
  hasConnectionDetails,
  SESSION_CONFIG_KEY,
  type ApiConfig,
  type Business,
} from "@/lib/api";

type ConnectionState = "loading" | "disconnected" | "connected" | "error";

type WorkspaceContextValue = {
  config: ApiConfig;
  connectionState: ConnectionState;
  connectionMessage: string;
  business: Business | null;
  connect: (nextConfig: ApiConfig) => Promise<void>;
  disconnect: () => void;
  request: <T,>(path: string, init?: RequestInit) => Promise<T>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

const blankConfig = (): ApiConfig => ({
  apiUrl: DEFAULT_API_URL,
  apiKey: "",
  businessId: "",
  userId: "",
});

async function verifyConnection(config: ApiConfig): Promise<Business> {
  const baseUrl = cleanApiUrl(config.apiUrl);
  if (!baseUrl) throw new Error("Enter the API base URL.");
  if (!config.apiKey.trim()) throw new Error("Enter the business API key.");
  if (!config.businessId.trim()) throw new Error("Enter the business ID.");

  let health: Response;
  try {
    health = await fetch(baseUrl + "/health", { cache: "no-store" });
  } catch {
    throw new Error("API unreachable. Check the base URL, server status, and CORS settings.");
  }
  if (!health.ok) throw new Error(`API health check failed (HTTP ${health.status}).`);

  return apiRequest<Business>(
    { ...config, apiUrl: baseUrl },
    "/v1/businesses",
  );
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ApiConfig>(blankConfig);
  const [connectionState, setConnectionState] = useState<ConnectionState>("loading");
  const [connectionMessage, setConnectionMessage] = useState("Checking this browser session.");
  const [business, setBusiness] = useState<Business | null>(null);

  useEffect(() => {
    let cancelled = false;
    const stored = window.sessionStorage.getItem(SESSION_CONFIG_KEY);
    if (!stored) {
      setConnectionState("disconnected");
      setConnectionMessage("Connect a business to load real workspace data.");
      return () => { cancelled = true; };
    }

    try {
      const parsed = JSON.parse(stored) as ApiConfig;
      const restored = { ...blankConfig(), ...parsed, apiUrl: cleanApiUrl(parsed.apiUrl || DEFAULT_API_URL) };
      setConfig(restored);
      if (!hasConnectionDetails(restored)) {
        setConnectionState("disconnected");
        setConnectionMessage("Reconnect with valid API credentials.");
        return () => { cancelled = true; };
      }
      setConnectionState("loading");
      verifyConnection(restored)
        .then((connectedBusiness) => {
          if (cancelled) return;
          setBusiness(connectedBusiness);
          setConnectionState("connected");
          setConnectionMessage("Business API connected.");
        })
        .catch((error: unknown) => {
          if (cancelled) return;
          setBusiness(null);
          setConnectionState("error");
          setConnectionMessage(error instanceof Error ? error.message : "Connection failed.");
        });
    } catch {
      window.sessionStorage.removeItem(SESSION_CONFIG_KEY);
      setConnectionState("disconnected");
      setConnectionMessage("Stored connection details were invalid. Connect again.");
    }

    return () => { cancelled = true; };
  }, []);

  const connect = useCallback(async (nextConfig: ApiConfig) => {
    const normalized = { ...nextConfig, apiUrl: cleanApiUrl(nextConfig.apiUrl) };
    setConnectionState("loading");
    setConnectionMessage("Checking API and business credentials.");
    try {
      const connectedBusiness = await verifyConnection(normalized);
      window.sessionStorage.setItem(SESSION_CONFIG_KEY, JSON.stringify(normalized));
      setConfig(normalized);
      setBusiness(connectedBusiness);
      setConnectionState("connected");
      setConnectionMessage("Business API connected.");
    } catch (error) {
      setBusiness(null);
      setConnectionState("error");
      setConnectionMessage(error instanceof Error ? error.message : "Connection failed.");
      throw error;
    }
  }, []);

  const disconnect = useCallback(() => {
    window.sessionStorage.removeItem(SESSION_CONFIG_KEY);
    setConfig(blankConfig());
    setBusiness(null);
    setConnectionState("disconnected");
    setConnectionMessage("Disconnected. No workspace data is loaded.");
  }, []);

  const request = useCallback(
    <T,>(path: string, init?: RequestInit) => apiRequest<T>(config, path, init),
    [config],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({ config, connectionState, connectionMessage, business, connect, disconnect, request }),
    [config, connectionState, connectionMessage, business, connect, disconnect, request],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider.");
  return value;
}
