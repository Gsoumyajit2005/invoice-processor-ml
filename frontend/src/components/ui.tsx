"use client";

import { useEffect, useId, useRef, useSyncExternalStore } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Globe,
  Info,
  Moon,
  ShieldCheck,
  Sparkles,
  Sun,
  UserPen,
  X,
} from "lucide-react";
import { cn, statusLabel } from "@/lib/format";
import {
  getThemeServerSnapshot,
  getThemeSnapshot,
  subscribeTheme,
  toggleThemeMode,
} from "@/lib/theme";
import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import "@/components/liquid-glass/overlays.css";
import type { InvoiceStatus } from "@/lib/types";

export function ThemeToggle({ className }: { className?: string }) {
  const theme = useSyncExternalStore(
    subscribeTheme,
    getThemeSnapshot,
    getThemeServerSnapshot,
  );
  const isDark = theme === "dark";

  return (
    <GlassButton
      type="button"
      onClick={() => toggleThemeMode()}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={className}
    >
      {isDark ? (
        <>
          <Sun className="h-3.5 w-3.5 text-amber-400" />
          <span className="hidden sm:inline">Light</span>
        </>
      ) : (
        <>
          <Moon className="h-3.5 w-3.5 text-stone-600" />
          <span className="hidden sm:inline">Dark</span>
        </>
      )}
    </GlassButton>
  );
}

export function StatusBadge({
  status,
  className,
}: {
  status: InvoiceStatus | string;
  className?: string;
}) {
  const styles: Record<string, string> = {
    verified:
      "border-emerald-200/80 bg-emerald-50/80 text-emerald-800 ring-1 ring-inset ring-emerald-600/10 dark:border-emerald-400/25 dark:bg-emerald-500/12 dark:text-emerald-300 dark:ring-emerald-400/15",
    extracted:
      "border-stone-200/80 bg-stone-50/80 text-stone-800 ring-1 ring-inset ring-stone-600/10 dark:border-stone-400/25 dark:bg-stone-500/12 dark:text-stone-300 dark:ring-stone-400/15",
    needs_review:
      "border-amber-200/80 bg-amber-50/80 text-amber-800 ring-1 ring-inset ring-amber-600/10 dark:border-amber-400/25 dark:bg-amber-500/12 dark:text-amber-300 dark:ring-amber-400/15",
    failed:
      "border-rose-200/80 bg-rose-50/80 text-rose-800 ring-1 ring-inset ring-rose-600/10 dark:border-rose-400/25 dark:bg-rose-500/12 dark:text-rose-300 dark:ring-rose-400/15",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium",
        styles[status] ??
          "border-stone-200/80 bg-stone-100/80 text-stone-700 dark:border-white/12 dark:bg-white/8 dark:text-stone-300",
        className,
      )}
    >
      {status === "verified" ? (
        <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
      ) : status === "needs_review" ? (
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      ) : status === "failed" ? (
        <AlertCircle className="h-3.5 w-3.5 shrink-0" />
      ) : (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
      )}
      {statusLabel(status)}
    </span>
  );
}

export function ExtractorBadge({
  extractor,
  compact = false,
  className,
}: {
  extractor: string | null | undefined;
  compact?: boolean;
  className?: string;
}) {
  if (!extractor) return null;
  const isCloud = extractor.toLowerCase().includes("cloud");
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium",
        isCloud
          ? "border-stone-200/80 bg-stone-50/80 text-stone-800 dark:border-stone-400/25 dark:bg-stone-500/12 dark:text-stone-300"
          : "border-stone-200/80 bg-stone-50/80 text-stone-800 dark:border-stone-400/25 dark:bg-stone-500/12 dark:text-stone-300",
        compact && "max-w-[210px]",
        className,
      )}
      title={`Extracted via ${extractor}`}
    >
      {isCloud ? (
        <Globe className="h-3 w-3 shrink-0" />
      ) : (
        <Cpu className="h-3 w-3 shrink-0" />
      )}
      <span className={compact ? "truncate" : undefined}>{extractor}</span>
    </span>
  );
}

export function ProvenancePill({
  source,
  hasBbox,
}: {
  source: "ocr_matched" | "vlm_inferred" | "user_edited" | undefined;
  hasBbox?: boolean;
}) {
  if (!source) return null;
  if (source === "ocr_matched") {
    return (
      <span
        className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded bg-emerald-50/80 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/15 dark:bg-emerald-500/14 dark:text-emerald-300 dark:ring-emerald-400/25"
        title={hasBbox ? "Matched to OCR bounding box" : "Matched in OCR text"}
      >
        <CheckCircle2 className="h-2.5 w-2.5" />
        OCR grounded
      </span>
    );
  }
  if (source === "user_edited") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded bg-stone-50/80 px-1.5 py-0.5 text-[10px] font-medium text-stone-700 ring-1 ring-inset ring-stone-600/15 dark:bg-stone-500/14 dark:text-stone-300 dark:ring-stone-400/25">
        <UserPen className="h-2.5 w-2.5" />
        Edited
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded bg-stone-100/80 px-1.5 py-0.5 text-[10px] font-medium text-stone-600 ring-1 ring-inset ring-stone-500/10 dark:bg-white/8 dark:text-stone-300 dark:ring-white/15">
      <Sparkles className="h-2.5 w-2.5" />
      VLM
    </span>
  );
}

export function AlertBanner({
  variant = "info",
  title,
  children,
  className,
}: {
  variant?: "error" | "warning" | "info" | "success";
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const palette = {
    error:
      "border-rose-200/80 bg-rose-50/75 text-rose-900 dark:border-rose-400/25 dark:bg-rose-500/12 dark:text-rose-200",
    warning:
      "border-amber-200/80 bg-amber-50/75 text-amber-900 dark:border-amber-400/25 dark:bg-amber-500/12 dark:text-amber-200",
    info: "border-stone-200/80 bg-stone-50/75 text-stone-900 dark:border-stone-400/25 dark:bg-stone-500/12 dark:text-stone-200",
    success:
      "border-emerald-200/80 bg-emerald-50/75 text-emerald-900 dark:border-emerald-400/25 dark:bg-emerald-500/12 dark:text-emerald-200",
  }[variant];

  const Icon = {
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
    success: CheckCircle2,
  }[variant];

  return (
    <div
      className={cn(
        "flex items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm",
        palette,
        className,
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div
          className={
            title
              ? "mt-0.5 text-xs leading-relaxed opacity-90"
              : "text-xs leading-relaxed"
          }
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  confirmVariant = "danger",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmVariant?: "danger" | "primary";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const cancelButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) { node.showModal(); cancelButton.current?.focus(); }
    if (!open && node.open) node.close();
  }, [open]);

  return <dialog ref={dialog} className="lg-dialog" aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}
    onClick={event => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
    <GlassSurface material="panel" radius={24} className="lg-dialog-surface">
      <div className="flex items-start justify-between gap-3">
        <h2 id={titleId} className="text-base font-semibold">{title}</h2>
        <GlassButton onClick={onCancel} disabled={busy} aria-label="Close modal"><X aria-hidden="true" className="h-4 w-4" /></GlassButton>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-300">{description}</p>
      <div className="mt-6 flex items-center justify-end gap-2.5">
        <GlassButton ref={cancelButton} onClick={onCancel} disabled={busy}>Cancel</GlassButton>
        <GlassButton onClick={onConfirm} disabled={busy} tone={confirmVariant === "danger" ? "danger" : "primary"}>
          {busy ? "Working…" : confirmLabel}
        </GlassButton>
      </div>
    </GlassSurface>
  </dialog>;
}
