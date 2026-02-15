"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ModelEvalMetrics } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

const METRIC_COLORS: Record<string, string> = {
  accuracy: "#22d3ee",
  precision_macro: "#8b5cf6",
  recall_macro: "#f59e0b",
  f1_macro: "#10b981",
  roc_auc: "#ef4444",
};

export default function MetricsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["metrics", "models"],
    queryFn: () => api.modelsMetrics(),
  });
  const training = useQuery({
    queryKey: ["metrics", "training"],
    queryFn: () => api.trainingMetrics(),
  });

  const [evalSet, setEvalSet] = useState<"holdout" | "official_test">("holdout");

  if (isLoading) return <div className="text-sm text-muted">Loading metrics…</div>;
  if (!data || Object.keys(data).length === 0)
    return (
      <div className="text-sm text-muted">
        No evaluation data found. Run <code className="text-primary">python main.py evaluate</code>.
      </div>
    );

  const sets = Object.keys(data);
  const currentSet = data[evalSet] ?? data[sets[0]];
  const models = currentSet ? Object.keys(currentSet) : [];

  const chartData = models.map((name) => {
    const m = currentSet[name];
    return {
      model: name,
      accuracy: m.accuracy,
      precision: m.precision_macro,
      recall: m.recall_macro,
      f1: m.f1_macro,
      roc_auc: m.roc_auc ?? 0,
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Model Metrics</h1>
        <p className="text-sm text-muted">
          Precision, recall, F1, and ROC-AUC on {sets.length} evaluation set(s).
        </p>
      </div>

      <div className="flex gap-2">
        {sets.map((s) => (
          <button
            key={s}
            onClick={() => setEvalSet(s as "holdout" | "official_test")}
            className={
              evalSet === s
                ? "px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium"
                : "px-3 py-1.5 rounded-md bg-surface-2 text-muted text-xs font-medium hover:bg-border-strong"
            }
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Comparative metrics — {evalSet.replace("_", " ")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="model" stroke="#8b949e" tick={{ fill: "#8b949e", fontSize: 12 }} />
                <YAxis domain={[0, 1]} stroke="#8b949e" tick={{ fill: "#8b949e", fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "#11161f",
                    border: "1px solid #273345",
                    borderRadius: "8px",
                    color: "#e6edf3",
                  }}
                />
                <Legend />
                <Bar dataKey="accuracy" fill={METRIC_COLORS.accuracy} name="accuracy" />
                <Bar dataKey="precision" fill={METRIC_COLORS.precision_macro} name="precision" />
                <Bar dataKey="recall" fill={METRIC_COLORS.recall_macro} name="recall" />
                <Bar dataKey="f1" fill={METRIC_COLORS.f1_macro} name="f1" />
                <Bar dataKey="roc_auc" fill={METRIC_COLORS.roc_auc} name="roc_auc" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {models.map((name) => {
          const m = currentSet[name];
          const cm = m.confusion_matrix;
          return (
            <Card key={name}>
              <CardHeader>
                <CardTitle>{name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <MetricLine label="Accuracy" value={m.accuracy} />
                  <MetricLine label="F1 (macro)" value={m.f1_macro} />
                  <MetricLine label="Precision" value={m.precision_macro} />
                  <MetricLine label="Recall" value={m.recall_macro} />
                  <MetricLine label="ROC-AUC" value={m.roc_auc ?? 0} />
                </div>
                <ConfusionMatrix cm={cm} />
                <PerClass metrics={m} />
                {training.data?.[name]?.cv_score ? (
                  <div className="text-xs text-muted border-t border-border pt-2">
                    CV score (train): {formatPercent(training.data[name].cv_score!, 3)} · trained in{" "}
                    {training.data[name].train_time_seconds?.toFixed(1)}s
                  </div>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted text-xs">{label}</span>
      <span className="font-mono">{formatPercent(value, 3)}</span>
    </div>
  );
}

function ConfusionMatrix({ cm }: { cm: number[][] }) {
  const labels = ["Benign", "Malicious"];
  const max = Math.max(1, ...cm.flat());
  return (
    <div>
      <div className="text-xs text-muted uppercase tracking-wide mb-2">Confusion matrix</div>
      <div className="grid grid-cols-[auto_1fr_1fr] gap-1 text-xs">
        <div />
        {labels.map((l) => (
          <div key={l} className="text-center text-muted">
            pred: {l}
          </div>
        ))}
        {cm.map((row, i) => (
          <>
            <div key={`label-${i}`} className="text-muted pr-2 flex items-center">
              act: {labels[i]}
            </div>
            {row.map((v, j) => (
              <div
                key={`cell-${i}-${j}`}
                className="h-10 flex items-center justify-center rounded font-mono"
                style={{
                  background: i === j
                    ? `rgba(34,211,238,${0.18 + (0.5 * v) / max})`
                    : `rgba(239,68,68,${0.18 + (0.5 * v) / max})`,
                }}
              >
                {v}
              </div>
            ))}
          </>
        ))}
      </div>
    </div>
  );
}

function PerClass({ metrics }: { metrics: ModelEvalMetrics }) {
  const labels = Object.keys(metrics.f1_per_class ?? {});
  if (labels.length === 0) return null;
  return (
    <div>
      <div className="text-xs text-muted uppercase tracking-wide mb-2">Per-class F1</div>
      <div className="space-y-1">
        {labels.map((l) => (
          <div key={l} className="flex items-center gap-3 text-xs">
            <Badge variant={l === "Malicious" ? "malicious" : "benign"}>{l}</Badge>
            <div className="flex-1 h-1.5 bg-surface-2 rounded">
              <div
                className={l === "Malicious" ? "h-full bg-danger rounded" : "h-full bg-success rounded"}
                style={{ width: `${(metrics.f1_per_class[l] ?? 0) * 100}%` }}
              />
            </div>
            <span className="w-14 text-right font-mono">
              {formatPercent(metrics.f1_per_class[l] ?? 0, 3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
