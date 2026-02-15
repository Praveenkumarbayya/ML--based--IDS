"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Gauge, Radio, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatLatencyMs, formatPercent } from "@/lib/utils";
import { useAlertStream } from "@/lib/ws";

export default function DashboardPage() {
  const { alerts, status } = useAlertStream(50);
  const recent = useQuery({
    queryKey: ["audit", "recent"],
    queryFn: () => api.listPredictions({ limit: 50 }),
    refetchInterval: 5000,
  });

  const kpis = useMemo(() => {
    const preds = recent.data ?? [];
    const total = preds.length;
    const malicious = preds.filter((p) => p.prediction === "Malicious").length;
    const avgLatency = total ? preds.reduce((s, p) => s + p.latency_ms, 0) / total : 0;
    const meanConf =
      total ? preds.reduce((s, p) => s + p.confidence, 0) / total : 0;
    return { total, malicious, avgLatency, meanConf };
  }, [recent.data]);

  const wsColor =
    status === "open"
      ? "text-success"
      : status === "connecting"
      ? "text-warning animate-pulse-soft"
      : "text-danger";

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Live Security Operations</h1>
          <p className="text-sm text-muted">
            Real-time ML-driven classification of NSL-KDD network flows.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted">
          <Radio className={`h-3.5 w-3.5 ${wsColor}`} />
          WebSocket · {status}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi
          icon={<Gauge className="h-4 w-4" />}
          label="Recent predictions"
          value={kpis.total.toString()}
          sub="last 50"
        />
        <Kpi
          icon={<ShieldAlert className="h-4 w-4 text-danger" />}
          label="Malicious flagged"
          value={kpis.malicious.toString()}
          sub={kpis.total ? formatPercent(kpis.malicious / kpis.total) : "—"}
          accent={kpis.malicious > 0 ? "danger" : "neutral"}
        />
        <Kpi
          icon={<CheckCircle2 className="h-4 w-4 text-success" />}
          label="Mean confidence"
          value={formatPercent(kpis.meanConf, 1)}
        />
        <Kpi
          icon={<Gauge className="h-4 w-4" />}
          label="Mean latency"
          value={formatLatencyMs(kpis.avgLatency)}
          sub="SLA < 500ms"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Live alert stream</CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="text-sm text-muted py-12 text-center">
                No alerts yet. Send a malicious-looking flow via{" "}
                <code className="text-primary">/analyze</code> to see this feed activate.
              </div>
            ) : (
              <ul className="space-y-2">
                {alerts.map((a) => (
                  <li
                    key={a.alert_id}
                    className="animate-slide-in flex items-start gap-3 rounded-md border border-border bg-surface-2 p-3"
                  >
                    <AlertTriangle
                      className={
                        a.severity === "high"
                          ? "h-4 w-4 text-danger mt-0.5"
                          : "h-4 w-4 text-warning mt-0.5"
                      }
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="malicious">{a.prediction}</Badge>
                        <Badge variant={a.severity === "high" ? "malicious" : "warning"}>
                          {a.severity}
                        </Badge>
                        <Badge variant="info">{a.model_used}</Badge>
                        <span className="text-xs text-subtle">
                          conf {formatPercent(a.confidence, 2)} ·{" "}
                          {formatLatencyMs(a.latency_ms)}
                        </span>
                      </div>
                      <div className="text-xs text-muted truncate">
                        Top features:{" "}
                        {a.top_features
                          .map((f) => `${f.feature}=${f.value}`)
                          .join(" · ") || "—"}
                      </div>
                    </div>
                    <div className="text-[10px] text-subtle whitespace-nowrap">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent predictions</CardTitle>
          </CardHeader>
          <CardContent>
            {recent.isLoading ? (
              <div className="text-sm text-muted">Loading…</div>
            ) : (
              <ul className="space-y-1.5 text-xs">
                {(recent.data ?? []).slice(0, 10).map((p) => (
                  <li
                    key={p.id}
                    className="flex items-center justify-between py-1.5 border-b border-border last:border-0"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Badge variant={p.prediction === "Malicious" ? "malicious" : "benign"}>
                        {p.prediction}
                      </Badge>
                      <span className="font-mono text-subtle truncate">
                        {p.model_used}
                      </span>
                    </div>
                    <div className="text-subtle">
                      {formatPercent(p.confidence, 1)}
                    </div>
                  </li>
                ))}
                {recent.data?.length === 0 && (
                  <li className="text-muted py-6 text-center">No predictions recorded yet.</li>
                )}
              </ul>
            )}
            <Link
              href="/audit"
              className="block mt-4"
            >
              <Button variant="outline" size="sm" className="w-full">
                View full audit log →
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: "danger" | "neutral";
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between text-muted mb-2 text-xs uppercase tracking-wide">
          <span>{label}</span>
          {icon}
        </div>
        <div
          className={
            accent === "danger"
              ? "text-2xl font-semibold text-danger"
              : "text-2xl font-semibold"
          }
        >
          {value}
        </div>
        {sub ? <div className="text-xs text-subtle mt-1">{sub}</div> : null}
      </CardContent>
    </Card>
  );
}
