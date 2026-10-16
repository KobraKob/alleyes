"use client";

import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  readWorkspaceConnection,
  type Business,
  type WorkspaceConnection,
} from "@/lib/api";

export function useWorkspace() {
  const [connection, setConnection] = useState<WorkspaceConnection | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [checking, setChecking] = useState(true);
  const [connectionError, setConnectionError] = useState("");

  const reload = useCallback(async () => {
    const saved = readWorkspaceConnection();
    setConnection(saved);
    setBusiness(null);
    setConnectionError("");
    if (!saved) {
      setChecking(false);
      return;
    }

    setChecking(true);
    try {
      const profile = await apiFetch<Business>("/v1/businesses", {}, saved);
      setBusiness(profile);
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : "Workspace connection failed.");
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      const saved = readWorkspaceConnection();
      if (!active) return;
      setConnection(saved);
      setBusiness(null);
      setConnectionError("");
      if (!saved) {
        setChecking(false);
        return;
      }
      setChecking(true);
      try {
        const profile = await apiFetch<Business>("/v1/businesses", {}, saved);
        if (active) setBusiness(profile);
      } catch (error) {
        if (active) setConnectionError(error instanceof Error ? error.message : "Workspace connection failed.");
      } finally {
        if (active) setChecking(false);
      }
    };
    void refresh();
    window.addEventListener("alleeyes:workspace-updated", refresh);
    return () => {
      active = false;
      window.removeEventListener("alleeyes:workspace-updated", refresh);
    };
  }, []);

  return { connection, business, checking, connectionError, reload, connected: Boolean(connection && business) };
}
