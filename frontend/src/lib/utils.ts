import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatPercent(v: number, digits = 1): string {
  return `${(v * 100).toFixed(digits)}%`;
}

export function formatLatencyMs(v: number): string {
  if (v < 1) return `${v.toFixed(2)} ms`;
  if (v < 1000) return `${v.toFixed(1)} ms`;
  return `${(v / 1000).toFixed(2)} s`;
}
