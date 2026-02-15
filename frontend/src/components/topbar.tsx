"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleDot } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export function Topbar() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 5000,
  });

  const status = data?.status ?? (isLoading ? "loading" : "error");

  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-10">
      <div className="flex items-center justify-between px-6 h-14">
        <div className="flex items-center gap-3">
          <CircleDot
            className={
              status === "ok"
                ? "h-3 w-3 text-success animate-pulse-soft"
                : status === "degraded"
                ? "h-3 w-3 text-warning"
                : "h-3 w-3 text-danger"
            }
          />
          <span className="text-sm text-muted">
            Backend:{" "}
            <span className="text-foreground font-medium">
              {status === "ok" ? "online" : status === "degraded" ? "degraded" : "offline"}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted">
          {data?.models_loaded?.length ? (
            <>
              <span>Models loaded:</span>
              {data.models_loaded.map((m) => (
                <Badge key={m} variant="info">
                  {m}
                </Badge>
              ))}
            </>
          ) : (
            <Badge variant="warning">No models loaded — run `python main.py train`</Badge>
          )}
        </div>
      </div>
    </header>
  );
}
