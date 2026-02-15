// Typed API client for the IDS backend.
//
// Browser side uses NEXT_PUBLIC_API_URL + NEXT_PUBLIC_API_KEY (dev only).
// In production the API key should be kept server-side; this scaffold is
// explicit about that compromise so it can be hardened later without
// changing call sites.

import type {
  Alert,
  AuditPrediction,
  EvaluationReport,
  HealthResponse,
  MetadataResponse,
  NetworkFlow,
  PredictionResponse,
  TrainingSummary,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

function withAuth(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  return { ...init, headers };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, withAuth(init));
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
      else if (body?.error) detail = `${body.error}: ${body.detail ?? ""}`;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// --- endpoints ---------------------------------------------------------

export const api = {
  health: () => request<HealthResponse>("/health"),
  metadata: () => request<MetadataResponse>("/metadata"),
  predict: (features: NetworkFlow, model_name?: string) =>
    request<PredictionResponse>("/predict", {
      method: "POST",
      body: JSON.stringify({ features, model_name }),
    }),
  listPredictions: (params: {
    limit?: number;
    offset?: number;
    only_malicious?: boolean;
    model?: string;
  } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qs.set(k, String(v));
    });
    const q = qs.toString();
    return request<AuditPrediction[]>(`/audit/predictions${q ? `?${q}` : ""}`);
  },
  listAlerts: (unackedOnly = false) =>
    request<Alert[]>(`/audit/alerts?unacked_only=${unackedOnly}`),
  ackAlert: (id: number) =>
    request<Alert>(`/audit/alerts/${id}/ack`, { method: "POST" }),
  modelsMetrics: () => request<EvaluationReport>("/metrics/models"),
  trainingMetrics: () => request<TrainingSummary>("/metrics/training"),
};

export function websocketUrl(path: string): string {
  const url = new URL(API_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  return url.toString();
}

export function getApiKey(): string {
  return API_KEY;
}
