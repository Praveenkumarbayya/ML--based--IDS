"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Shield, ShieldAlert } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { AuditPrediction } from "@/lib/types";
import { formatDate, formatLatencyMs, formatPercent } from "@/lib/utils";

export default function AuditPage() {
  const [onlyMalicious, setOnlyMalicious] = useState(false);
  const [model, setModel] = useState<string>("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const meta = useQuery({ queryKey: ["metadata"], queryFn: () => api.metadata() });
  const preds = useQuery({
    queryKey: ["audit", { onlyMalicious, model }],
    queryFn: () =>
      api.listPredictions({
        limit: 200,
        only_malicious: onlyMalicious,
        model: model || undefined,
      }),
    refetchInterval: 5000,
  });
  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.listAlerts(true),
    refetchInterval: 5000,
  });

  const client = useQueryClient();
  const ack = useMutation({
    mutationFn: (id: number) => api.ackAlert(id),
    onSuccess: () => client.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <p className="text-sm text-muted">
          Every prediction and alert is persisted to SQLite and queryable here.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between flex gap-2">
            <CardTitle>Predictions</CardTitle>
            <div className="flex items-center gap-2 ml-auto">
              <label className="text-xs text-muted flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={onlyMalicious}
                  onChange={(e) => setOnlyMalicious(e.target.checked)}
                  className="accent-primary"
                />
                Malicious only
              </label>
              <Select value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="">All models</option>
                {meta.data?.available_models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {preds.isLoading ? (
              <div className="text-sm text-muted">Loading…</div>
            ) : (preds.data ?? []).length === 0 ? (
              <div className="text-sm text-muted py-10 text-center">No predictions recorded.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-muted border-b border-border">
                      <th className="py-2 px-2">Time</th>
                      <th className="py-2 px-2">Label</th>
                      <th className="py-2 px-2">Model</th>
                      <th className="py-2 px-2">Confidence</th>
                      <th className="py-2 px-2">Latency</th>
                      <th className="py-2 px-2">IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(preds.data ?? []).map((p) => (
                      <RowOrExpanded
                        key={p.id}
                        p={p}
                        expanded={expanded === p.id}
                        onToggle={() => setExpanded(expanded === p.id ? null : p.id)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Unacknowledged alerts</CardTitle>
          </CardHeader>
          <CardContent>
            {(alerts.data ?? []).length === 0 ? (
              <div className="text-sm text-muted py-6 text-center">
                No outstanding alerts.
              </div>
            ) : (
              <ul className="space-y-2">
                {alerts.data!.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center gap-2 rounded-md border border-border bg-surface-2 p-3"
                  >
                    <ShieldAlert
                      className={
                        a.severity === "high" ? "h-4 w-4 text-danger" : "h-4 w-4 text-warning"
                      }
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <Badge variant={a.severity === "high" ? "malicious" : "warning"}>
                          {a.severity}
                        </Badge>
                        <span className="text-xs text-muted">#{a.id}</span>
                      </div>
                      <div className="text-[10px] text-subtle">{formatDate(a.created_at)}</div>
                    </div>
                    <Button
                      size="sm"
                      variant="subtle"
                      onClick={() => ack.mutate(a.id)}
                      disabled={ack.isPending}
                    >
                      <CheckCircle2 className="h-3 w-3" />
                      Ack
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function RowOrExpanded({
  p,
  expanded,
  onToggle,
}: {
  p: AuditPrediction;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className="border-b border-border hover:bg-surface-2 cursor-pointer"
        onClick={onToggle}
      >
        <td className="py-2 px-2 font-mono text-xs text-muted">
          {formatDate(p.created_at)}
        </td>
        <td className="py-2 px-2">
          {p.prediction === "Malicious" ? (
            <Badge variant="malicious">
              <ShieldAlert className="h-3 w-3" />
              Malicious
            </Badge>
          ) : (
            <Badge variant="benign">
              <Shield className="h-3 w-3" />
              Benign
            </Badge>
          )}
        </td>
        <td className="py-2 px-2 text-xs font-mono">{p.model_used}</td>
        <td className="py-2 px-2 font-mono">{formatPercent(p.confidence, 2)}</td>
        <td className="py-2 px-2 font-mono text-xs">{formatLatencyMs(p.latency_ms)}</td>
        <td className="py-2 px-2 font-mono text-xs text-muted">{p.client_ip ?? "—"}</td>
      </tr>
      {expanded ? (
        <tr className="bg-background">
          <td colSpan={6} className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-muted uppercase tracking-wide mb-1">Raw features</div>
                <pre className="bg-surface-2 rounded p-3 overflow-auto max-h-60 font-mono">
                  {JSON.stringify(p.raw_features, null, 2)}
                </pre>
              </div>
              <div>
                <div className="text-muted uppercase tracking-wide mb-1">
                  Class probabilities
                </div>
                <pre className="bg-surface-2 rounded p-3 font-mono">
                  {JSON.stringify(p.class_probabilities, null, 2)}
                </pre>
                <div className="text-muted uppercase tracking-wide mt-3 mb-1">
                  Request id
                </div>
                <code className="text-primary">{p.request_id}</code>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
