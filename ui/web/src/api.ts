// Thin fetch wrapper over the management API (architecture.md #8). This is the ONLY
// module that talks to the backend -- components never call fetch() directly, so the
// web client stays a pure consumer of the one shared API (never embeds its own
// routing/gating/cost logic).
import type { GateOut, ModelEndpoint, RedactionLogEntry, RunOut, RunSummaryOut } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listRuns: () => request<RunSummaryOut[]>("/runs"),
  getRun: (runId: string) => request<RunOut>(`/runs/${runId}`),
  startRun: (goal: string) =>
    request<RunSummaryOut>("/runs", { method: "POST", body: JSON.stringify({ goal }) }),
  cancelRun: (runId: string) => request<RunSummaryOut>(`/runs/${runId}/cancel`, { method: "POST" }),
  getRegistry: () => request<ModelEndpoint[]>("/registry"),
  updateRegistryEntry: (modelId: string, update: Partial<ModelEndpoint>) =>
    request<ModelEndpoint>(`/registry/${modelId}`, { method: "PUT", body: JSON.stringify(update) }),
  listGates: () => request<GateOut[]>("/gates"),
  resolveGate: (gateId: string, approved: boolean) =>
    request<GateOut>(`/gates/${gateId}/resolve`, { method: "POST", body: JSON.stringify({ approved }) }),
  getRedactionLog: () => request<RedactionLogEntry[]>("/redaction-log"),
};

export function wsUrlForRun(runId: string): string {
  return `${API_BASE.replace(/^http/, "ws")}/runs/${runId}/ws`;
}
