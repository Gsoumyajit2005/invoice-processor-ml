import React from "react";
import { cn } from "@/lib/format";

interface WorkspaceHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function WorkspaceHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: WorkspaceHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 pb-4 border-b border-border/60",
        className
      )}
    >
      <div>
        {eyebrow ? (
          <div className="flex items-center gap-2 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            <span className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              {eyebrow}
            </span>
          </div>
        ) : null}
        <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-2xl">
            {description}
          </p>
        ) : null}
      </div>

      {actions ? (
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
