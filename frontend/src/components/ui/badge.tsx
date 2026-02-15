import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-border-strong bg-surface-2 text-foreground",
        benign: "border-success/40 bg-success-subtle text-success",
        malicious: "border-danger/40 bg-danger-subtle text-danger",
        warning: "border-warning/40 bg-warning-subtle text-warning",
        info: "border-primary/40 bg-primary/10 text-primary",
        outline: "border-border-strong bg-transparent text-muted",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
