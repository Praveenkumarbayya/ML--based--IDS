"use client";

import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/utils";

export default function ModelsPage() {
  const meta = useQuery({ queryKey: ["metadata"], queryFn: () => api.metadata() });
  const training = useQuery({
    queryKey: ["metrics", "training"],
    queryFn: () => api.trainingMetrics(),
  });

  const available = meta.data?.available_models ?? [];
  const def = meta.data?.default_model ?? null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Trained Models</h1>
        <p className="text-sm text-muted">
          Inventory of models loaded into the inference registry, with training
          metadata.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {available.map((name) => {
          const t = training.data?.[name];
          const isDefault = name === def;
          return (
            <Card key={name} className={isDefault ? "border-primary/50" : ""}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 normal-case text-base tracking-normal text-foreground font-semibold">
                  {name}
                  {isDefault ? (
                    <Badge variant="info">
                      <Trophy className="h-3 w-3" />
                      default
                    </Badge>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {t ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-muted">CV score</span>
                      <span className="font-mono">
                        {t.cv_score !== null && t.cv_score !== undefined
                          ? formatPercent(t.cv_score, 3)
                          : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Train time</span>
                      <span className="font-mono">
                        {t.train_time_seconds !== null && t.train_time_seconds !== undefined
                          ? `${t.train_time_seconds.toFixed(1)} s`
                          : "—"}
                      </span>
                    </div>
                    <div>
                      <div className="text-muted uppercase text-xs tracking-wide mb-1">
                        Best hyperparameters
                      </div>
                      <pre className="bg-surface-2 rounded p-3 text-xs font-mono overflow-auto">
                        {JSON.stringify(t.best_params, null, 2)}
                      </pre>
                    </div>
                  </>
                ) : (
                  <div className="text-muted text-xs">
                    Training metadata not available — run{" "}
                    <code className="text-primary">python main.py train</code>.
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {available.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted">
            No trained models loaded. Run{" "}
            <code className="text-primary">python main.py train</code> and refresh.
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
