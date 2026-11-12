"use client";

import { useEffect } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Globe,
  Info,
  ShieldCheck,
  Sparkles,
  UserPen,
  X,
} from "lucide-react";
import { cn, statusLabel } from "@/lib/format";
import type { InvoiceStatus } from "@/lib/types";

export function StatusBadge({
  status,
  className,
}: {
  status: InvoiceStatus | string;
  className?: string;
}) {
  const styles: Record<string, string> = {
    verified:
      "border-emerald-200 bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-600/10",
    extracted:
      "border-sky-200 bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-600/10",
    needs_review:
      "border-amber-200 bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-600/10",
    failed:
      "border-rose-200 bg-rose-50 text-rose-800 ring-1 ring-inset ring-rose-600/10",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        styles[status] ?? "border-slate-200 bg-slate-100 text-slate-700",
        className,
      )}
    >
      {status === "verified" ? (
        <ShieldCheck className="h-3.5 w-3.5" />
      ) : status === "needs_review" ? (
        <AlertTriangle className="h-3.5 w-3.5" />
      ) : status === "failed" ? (
        <AlertCircle className="h-3.5 w-3.5" />
      ) : (
        <CheckCircle2 className="h-3.5 w-3.5" />
      )}
      {statusLabel(status)}
    </span>
  );
}

export function ExtractorBadge({
  extractor,
}: {
  extractor: string | null | undefined;
}) {
  if (!extractor) return null;
  const isCloud = extractor.toLowerCase().includes("cloud");
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium",
        isCloud
          ? "border-violet-200 bg-violet-50 text-violet-800"
          : "border-indigo-200 bg-indigo-50 text-indigo-800",
      )}
      title={`Extracted via ${extractor}`}
    >
      {isCloud ? (
        <Globe className="h-3 w-3" />
      ) : (
        <Cpu className="h-3 w-3" />
      )}
      {extractor}
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
        className="inline-flex items-center gap-1 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/15"
        title={hasBbox ? "Matched to OCR bounding box" : "Matched in OCR text"}
      >
        <CheckCircle2 className="h-2.5 w-2.5" />
        OCR grounded
      </span>
    );
  }
  if (source === "user_edited") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 ring-1 ring-inset ring-sky-600/15">
        <UserPen className="h-2.5 w-2.5" />
        Edited
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10">
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
    error: "border-rose-200 bg-rose-50 text-rose-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    info: "border-sky-200 bg-sky-50 text-sky-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
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
        <div className={title ? "mt-0.5 text-xs leading-relaxed opacity-90" : "text-xs leading-relaxed"}>
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
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        onCancel();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      onClick={() => !busy && onCancel()}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h3
            id="confirm-modal-title"
            className="text-base font-semibold text-slate-900"
          >
            {title}
          </h3>
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          {description}
        </p>
        <div className="mt-6 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={cn(
              "rounded-lg px-3.5 py-2 text-sm font-semibold text-white shadow-xs disabled:opacity-60",
              confirmVariant === "danger"
                ? "bg-rose-600 hover:bg-rose-700"
                : "bg-indigo-600 hover:bg-indigo-700",
            )}
          >
            {busy ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
