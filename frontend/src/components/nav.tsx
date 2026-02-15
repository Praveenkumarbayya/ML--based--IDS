"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, Database, FlaskConical, LineChart, Shield } from "lucide-react";

import { cn } from "@/lib/utils";

const routes = [
  { href: "/", label: "Dashboard", icon: Activity },
  { href: "/analyze", label: "Analyze Flow", icon: FlaskConical },
  { href: "/metrics", label: "Model Metrics", icon: LineChart },
  { href: "/audit", label: "Audit Log", icon: Database },
  { href: "/models", label: "Models", icon: Bot },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex h-screen w-60 flex-col border-r border-border bg-surface sticky top-0">
      <div className="p-5 border-b border-border flex items-center gap-2">
        <Shield className="h-5 w-5 text-primary" />
        <div>
          <div className="text-sm font-bold tracking-wide">IDS Console</div>
          <div className="text-[10px] uppercase text-subtle">NSL-KDD · v2.0</div>
        </div>
      </div>
      <nav className="flex-1 p-3 flex flex-col gap-1">
        {routes.map((r) => {
          const Icon = r.icon;
          const active = pathname === r.href;
          return (
            <Link
              key={r.href}
              href={r.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:text-foreground hover:bg-surface-2",
              )}
            >
              <Icon className="h-4 w-4" />
              {r.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border text-xs text-subtle">
        <div>Capstone · BSc Computing</div>
        <div>2025-2026</div>
      </div>
    </aside>
  );
}
