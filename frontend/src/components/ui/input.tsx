import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-9 w-full rounded-md border border-border-strong bg-surface-2 px-3 text-sm text-foreground " +
          "placeholder:text-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 " +
          "disabled:opacity-50 transition-colors",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-md border border-border-strong bg-surface-2 px-3 py-2 text-sm text-foreground font-mono " +
          "placeholder:text-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 " +
          "disabled:opacity-50 transition-colors",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "h-9 rounded-md border border-border-strong bg-surface-2 px-3 text-sm text-foreground " +
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-colors",
        className,
      )}
      {...props}
    />
  ),
);
Select.displayName = "Select";
