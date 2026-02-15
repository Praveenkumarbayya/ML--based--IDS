"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Send, ShieldCheck, ShieldAlert } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { NetworkFlow, PredictionResponse } from "@/lib/types";
import { formatLatencyMs, formatPercent } from "@/lib/utils";

const EXAMPLES: Record<string, NetworkFlow> = {
  "Normal HTTP browsing": {
    protocol_type: "tcp",
    service: "http",
    flag: "SF",
    src_bytes: 491,
    dst_bytes: 0,
    count: 2,
    srv_count: 2,
    same_srv_rate: 1.0,
    logged_in: 1,
    dst_host_count: 150,
    dst_host_srv_count: 25,
  },
  "Neptune SYN flood": {
    protocol_type: "tcp",
    service: "private",
    flag: "REJ",
    src_bytes: 0,
    dst_bytes: 0,
    count: 229,
    srv_count: 10,
    rerror_rate: 1.0,
    srv_rerror_rate: 1.0,
    dst_host_count: 255,
    dst_host_rerror_rate: 1.0,
    dst_host_srv_rerror_rate: 1.0,
  },
  "Port scan (ipsweep)": {
    protocol_type: "icmp",
    service: "ecr_i",
    flag: "SF",
    src_bytes: 8,
    dst_bytes: 0,
    count: 1,
    srv_count: 1,
    diff_srv_rate: 1.0,
    dst_host_count: 255,
    dst_host_srv_count: 1,
    dst_host_diff_srv_rate: 1.0,
  },
  "FTP brute-force": {
    protocol_type: "tcp",
    service: "ftp",
    flag: "SF",
    src_bytes: 134,
    dst_bytes: 1234,
    num_failed_logins: 3,
    logged_in: 0,
    count: 1,
    srv_count: 1,
    same_srv_rate: 1.0,
  },
};

export default function AnalyzePage() {
  const meta = useQuery({ queryKey: ["metadata"], queryFn: () => api.metadata() });
  const [modelName, setModelName] = useState<string>("");
  const [jsonText, setJsonText] = useState<string>(
    JSON.stringify(EXAMPLES["Normal HTTP browsing"], null, 2),
  );
  const [parseError, setParseError] = useState<string | null>(null);

  const predict = useMutation({
    mutationFn: async (): Promise<PredictionResponse> => {
      let parsed: NetworkFlow;
      try {
        parsed = JSON.parse(jsonText);
      } catch (e) {
        throw new Error(`Invalid JSON: ${(e as Error).message}`);
      }
      return api.predict(parsed, modelName || undefined);
    },
  });

  function loadExample(name: string) {
    const data = EXAMPLES[name];
    setJsonText(JSON.stringify(data, null, 2));
    setParseError(null);
  }

  function validateJson(text: string) {
    setJsonText(text);
    try {
      JSON.parse(text);
      setParseError(null);
    } catch (e) {
      setParseError((e as Error).message);
    }
  }

  const result = predict.data;

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-semibold">Analyze Network Flow</h1>
        <p className="text-sm text-muted">
          Submit NSL-KDD flow features for on-demand classification.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Input</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <label className="text-xs text-muted w-20">Model</label>
              <Select
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="flex-1"
              >
                <option value="">Auto (best by CV score)</option>
                {meta.data?.available_models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-muted uppercase tracking-wide">Examples</div>
              <div className="flex flex-wrap gap-2">
                {Object.keys(EXAMPLES).map((name) => (
                  <Button
                    key={name}
                    variant="subtle"
                    size="sm"
                    onClick={() => loadExample(name)}
                  >
                    {name}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-muted uppercase tracking-wide">JSON payload</label>
              <Textarea
                rows={18}
                value={jsonText}
                onChange={(e) => validateJson(e.target.value)}
                className="mt-1"
              />
              {parseError ? (
                <p className="text-xs text-danger mt-1">{parseError}</p>
              ) : null}
            </div>

            <Button
              onClick={() => predict.mutate()}
              disabled={!!parseError || predict.isPending}
              className="w-full"
            >
              {predict.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Classify
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
          </CardHeader>
          <CardContent>
            {predict.isError ? (
              <div className="text-sm text-danger">
                {(predict.error as Error).message}
              </div>
            ) : !result ? (
              <div className="text-sm text-muted py-8 text-center">
                Results will appear here after classification.
              </div>
            ) : (
              <div className="space-y-5">
                <div
                  className={
                    result.prediction === "Malicious"
                      ? "rounded-lg border border-danger/50 bg-danger-subtle p-4"
                      : "rounded-lg border border-success/50 bg-success-subtle p-4"
                  }
                >
                  <div className="flex items-center gap-2">
                    {result.prediction === "Malicious" ? (
                      <ShieldAlert className="h-5 w-5 text-danger" />
                    ) : (
                      <ShieldCheck className="h-5 w-5 text-success" />
                    )}
                    <span className="text-lg font-semibold">{result.prediction}</span>
                    <Badge variant="info" className="ml-auto">
                      {result.model_used}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-muted">
                    Confidence:{" "}
                    <span className="text-foreground font-medium">
                      {formatPercent(result.confidence, 2)}
                    </span>{" "}
                    · Latency: {formatLatencyMs(result.latency_ms)}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-muted uppercase tracking-wide mb-2">
                    Class probabilities
                  </div>
                  <div className="space-y-1.5">
                    {Object.entries(result.class_probabilities).map(([label, p]) => (
                      <div key={label} className="flex items-center gap-3">
                        <div className="w-24 text-xs">{label}</div>
                        <div className="flex-1 h-2 rounded bg-surface-2 overflow-hidden">
                          <div
                            className={
                              label === "Malicious"
                                ? "h-full bg-danger"
                                : "h-full bg-success"
                            }
                            style={{ width: `${p * 100}%` }}
                          />
                        </div>
                        <div className="w-16 text-right font-mono text-xs">
                          {formatPercent(p, 3)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-muted uppercase tracking-wide mb-2">
                    Top contributing features
                  </div>
                  {result.top_features.length === 0 ? (
                    <div className="text-xs text-subtle">
                      No non-zero numeric features to highlight.
                    </div>
                  ) : (
                    <ul className="space-y-1.5">
                      {result.top_features.map((f) => (
                        <li
                          key={f.feature}
                          className="flex items-center justify-between text-xs"
                        >
                          <code className="text-primary">{f.feature}</code>
                          <span className="font-mono">{f.value}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="text-[10px] text-subtle border-t border-border pt-3">
                  Request: <code>{result.request_id}</code>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
