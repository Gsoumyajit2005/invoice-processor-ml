"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Eye,
  EyeOff,
  FileText,
  Globe,
  KeyRound,
  Loader2,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import {
  ApiError,
  extractBatch,
  extractSingle,
  getHealth,
} from "@/lib/api-client";
import {
  CLOUD_PROVIDER_DEFAULTS,
  clearCloudConfig,
  getCloudConfigRaw,
  parseCloudConfigRaw,
  saveCloudConfig,
  saveLatestBatch,
  subscribeSessionStore,
  type CloudKeyConfig,
} from "@/lib/cloud-settings";
import {
  cn,
  formatCurrency,
  formatFileSize,
  formatLatency,
} from "@/lib/format";
import type {
  CloudProvider,
  ExtractMode,
  ExtractionResponse,
  HealthResponse,
} from "@/lib/types";
import { RecentDocuments } from "@/components/RecentDocuments";
import { WorkspaceHeader } from "@/components/WorkspaceHeader";
import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import "@/components/liquid-glass/overlays.css";
import { AlertBanner, ExtractorBadge, StatusBadge } from "@/components/ui";

const ALLOWED_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".webp", ".pdf"]);
const MAX_BATCH_FILES = 20;

const MODE_OPTIONS: Array<{
  value: ExtractMode;
  title: string;
  subtitle: string;
  icon: typeof Sparkles;
}> = [
  {
    value: "auto",
    title: "Automatic",
    subtitle: "Local GPU first, cloud escalation on failure",
    icon: Sparkles,
  },
  {
    value: "local",
    title: "Local GPU",
    subtitle: "Private Indra OCR 1.1 + Qwen3.5-0.8B LoRA",
    icon: Cpu,
  },
  {
    value: "cloud",
    title: "Cloud",
    subtitle: "LiteLLM Gemini / OpenAI / OpenRouter",
    icon: Globe,
  },
];

function isAllowedFile(file: File): boolean {
  const lower = file.name.toLowerCase();
  const dot = lower.lastIndexOf(".");
  if (dot === -1) return false;
  return ALLOWED_EXTENSIONS.has(lower.slice(dot));
}

export default function UploadExtractPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState<ExtractMode>("auto");
  const [showKeyDrawer, setShowKeyDrawer] = useState(false);
  const [showApiKeyValue, setShowApiKeyValue] = useState(false);
  const cloudConfigRaw = useSyncExternalStore(
    subscribeSessionStore,
    getCloudConfigRaw,
    () => "",
  );
  const cloudConfig = useMemo(
    () => parseCloudConfigRaw(cloudConfigRaw),
    [cloudConfigRaw],
  );
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractionResponse | null>(null);

  useEffect(() => {
    let active = true;
    getHealth()
      .then((h) => {
        if (active) setHealth(h);
      })
      .catch(() => {
        if (active) setHealth(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const maxUploadMb = health?.limits.max_upload_mb ?? 20;
  const maxPdfPages = health?.limits.max_pdf_pages ?? 20;

  const appendFiles = (incoming: FileList | File[]) => {
    setErrorMsg(null);
    const rejected: string[] = [];
    const maxBytes = maxUploadMb * 1024 * 1024;
    const accepted: File[] = [];

    for (const f of Array.from(incoming)) {
      if (!isAllowedFile(f)) {
        rejected.push(`${f.name} (unsupported format)`);
        continue;
      }
      if (f.size === 0) {
        rejected.push(`${f.name} (empty file)`);
        continue;
      }
      if (f.size > maxBytes) {
        rejected.push(`${f.name} (exceeds ${maxUploadMb} MB limit)`);
        continue;
      }
      accepted.push(f);
    }

    setFiles((prev) => {
      const seen = new Set(prev.map((p) => `${p.name}:${p.size}`));
      const merged = [...prev];
      for (const f of accepted) {
        const sig = `${f.name}:${f.size}`;
        if (!seen.has(sig)) {
          seen.add(sig);
          merged.push(f);
        }
      }
      if (merged.length > MAX_BATCH_FILES) {
        rejected.push(
          `Batch limited to ${MAX_BATCH_FILES} files (${merged.length - MAX_BATCH_FILES} omitted)`,
        );
        return merged.slice(0, MAX_BATCH_FILES);
      }
      return merged;
    });

    if (rejected.length) {
      setErrorMsg(`Skipped: ${rejected.join(", ")}`);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files?.length) {
      appendFiles(event.dataTransfer.files);
    }
  };

  const updateCloudField = (patch: Partial<CloudKeyConfig>) => {
    saveCloudConfig({ ...cloudConfig, ...patch });
  };

  const handleProviderChange = (provider: CloudProvider) => {
    updateCloudField({
      provider,
      model: CLOUD_PROVIDER_DEFAULTS[provider].defaultModel,
    });
  };

  const handleClearKey = () => {
    clearCloudConfig();
  };

  const handleSubmit = async () => {
    if (!files.length || submitting) return;
    setErrorMsg(null);
    setResult(null);
    setSubmitting(true);

    try {
      if (files.length === 1) {
        const extraction = await extractSingle(files[0], mode, cloudConfig);
        setResult(extraction);
      } else {
        const batch = await extractBatch(files, mode, cloudConfig);
        saveLatestBatch(batch);
        router.push("/batch");
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMsg(error.detail);
      } else {
        setErrorMsg("Extraction failed due to an unexpected network error.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const cloudNeedsKeyNotice =
    mode === "cloud" &&
    !cloudConfig.apiKey.trim() &&
    health !== null &&
    !health.cloud_default_configured;

  return (
    <div className="extract-page">
      <WorkspaceHeader
        eyebrow="DOCUMENT INTAKE // WORKSTATION"
        title="Extract documents"
        description="Drop invoices and receipts into one place. Verify every field against its source."
        actions={
          <a
            href="#recent-documents"
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            Recent Documents ↓
          </a>
        }
      />
      <div className="extract-grid">
        {/* Left Column: Dropzone + Controls */}
        <div className="extract-upload">
          <div className="glass-surface upload-card">
            {/* Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              className={cn(
                "extract-dropzone",
                dragging
                  ? "border-stone-500 bg-stone-500/10 dark:border-stone-400 dark:bg-stone-500/15"
                  : "border-stone-300/80 bg-white/40 hover:border-stone-400 hover:bg-stone-500/5 dark:border-white/15 dark:bg-white/[0.03] dark:hover:border-stone-400/60 dark:hover:bg-stone-500/10",
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.webp,.pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) {
                    appendFiles(e.target.files);
                    e.target.value = "";
                  }
                }}
              />
              <div className="drop-icon flex h-12 w-12 items-center justify-center rounded-2xl bg-card text-foreground shadow-xs ring-1 ring-border">
                <UploadCloud className="h-6 w-6 text-accent" />
              </div>
              <p className="mt-3 text-sm font-semibold text-foreground">
                Your documents go here
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Drag files into this space, or choose them from your computer.
              </p>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground shadow-2xs hover:bg-muted transition-colors mt-4" aria-hidden="true">Choose files</span>
              <div className="flex flex-wrap justify-center gap-2 mt-4 text-[11px] font-mono text-muted-foreground">
                <span className="px-2.5 py-0.5 rounded-full border border-border bg-muted/60">JPG · PNG · WEBP · PDF</span>
                <span className="px-2.5 py-0.5 rounded-full border border-border bg-muted/60">Up to {MAX_BATCH_FILES} documents</span>
                <span className="px-2.5 py-0.5 rounded-full border border-border bg-muted/60">{maxUploadMb} MB / file · {maxPdfPages} PDF pages</span>
              </div>
            </div>

            {/* Queued Files */}
            {files.length > 0 ? (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs font-medium text-stone-600 dark:text-stone-400">
                  <span>
                    {files.length} file{files.length > 1 ? "s" : ""} queued
                  </span>
                  <button
                    type="button"
                    onClick={() => setFiles([])}
                    className="inline-flex items-center gap-1 text-stone-500 hover:text-rose-600 dark:text-stone-400 dark:hover:text-rose-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Clear all
                  </button>
                </div>
                <ul className="max-h-52 divide-y divide-stone-200/70 overflow-y-auto rounded-xl border border-stone-200/75 bg-white/55 dark:divide-white/10 dark:border-white/10 dark:bg-stone-950/45">
                  {files.map((file, index) => (
                    <li
                      key={`${file.name}-${file.size}-${index}`}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <FileText className="h-4 w-4 shrink-0 text-stone-400 dark:text-stone-500" />
                        <span className="truncate font-medium text-stone-800 dark:text-stone-200">
                          {file.name}
                        </span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="tabular-nums text-xs text-stone-500 dark:text-stone-400">
                          {formatFileSize(file.size)}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            setFiles((prev) =>
                              prev.filter((_, i) => i !== index),
                            )
                          }
                          className="rounded p-1 text-stone-400 hover:bg-stone-200/60 hover:text-stone-700 dark:text-stone-500 dark:hover:bg-white/10 dark:hover:text-stone-200"
                          aria-label={`Remove ${file.name}`}
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Extraction Mode Selector */}
            <div className="processing-method">
              <p className="text-xs font-semibold text-stone-500 dark:text-stone-400">
                Processing method
              </p>
              <GlassSurface material="panel" radius={20} className="extraction-modes mt-2" role="group" aria-label="Extraction pipeline mode">
                {MODE_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const active = mode === opt.value;
                  return (
                    <GlassButton
                      key={opt.value}
                      type="button"
                      aria-pressed={active}
                      title={opt.subtitle}
                      onClick={() => setMode(opt.value)}
                    >
                      <div className="flex items-center gap-1.5">
                        <Icon
                          className={cn(
                            "h-4 w-4",
                            active
                              ? "text-stone-600 dark:text-stone-400"
                              : "text-stone-500 dark:text-stone-400",
                          )}
                        />
                        <span
                          className={cn(
                            "text-sm font-semibold",
                            active
                              ? "text-stone-950 dark:text-stone-200"
                              : "text-stone-900 dark:text-stone-100",
                          )}
                        >
                          {opt.title}
                        </span>
                      </div>
                    </GlassButton>
                  );
                })}
              </GlassSurface>
            </div>

            {/* Ephemeral BYO Cloud Key Drawer */}
            <div className="cloud-settings" id="cloud-settings">
              <button
                type="button"
                onClick={() => setShowKeyDrawer((prev) => !prev)}
                className="flex w-full items-center justify-between px-3.5 py-2.5 text-left text-xs font-medium text-stone-700 dark:text-stone-300"
              >
                <span className="flex items-center gap-2">
                  <KeyRound className="h-3.5 w-3.5 text-stone-500 dark:text-stone-400" />
                  Advanced cloud settings (optional session key)
                  {cloudConfig.apiKey.trim() ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300">
                      Key Active ({cloudConfig.provider})
                    </span>
                  ) : null}
                </span>
                {showKeyDrawer ? (
                  <ChevronUp className="h-4 w-4 text-stone-400 dark:text-stone-500" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-stone-400 dark:text-stone-500" />
                )}
              </button>

              {showKeyDrawer ? (
                <div className="space-y-3 border-t border-stone-200/70 px-3.5 py-3 text-xs dark:border-white/10">
                  <p className="text-stone-600 dark:text-stone-400">
                    Sent per-request via{" "}
                    <code className="rounded bg-white/80 px-1 py-0.5 font-mono text-[11px] ring-1 ring-stone-200/80 dark:bg-white/10 dark:text-stone-200 dark:ring-white/15">
                      X-LLM-*
                    </code>{" "}
                    headers through our server proxy. Held in browser{" "}
                    <span className="font-semibold text-stone-800 dark:text-stone-200">
                      sessionStorage
                    </span>{" "}
                    only (never saved to database or localStorage).
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block font-medium text-stone-700 dark:text-stone-300">
                        Provider
                      </label>
                      <select
                        value={cloudConfig.provider}
                        onChange={(e) =>
                          handleProviderChange(e.target.value as CloudProvider)
                        }
                        className="lg-select w-full"
                      >
                        {(
                          Object.keys(
                            CLOUD_PROVIDER_DEFAULTS,
                          ) as CloudProvider[]
                        ).map((key) => (
                          <option key={key} value={key}>
                            {CLOUD_PROVIDER_DEFAULTS[key].label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block font-medium text-stone-700 dark:text-stone-300">
                        LiteLLM Model
                      </label>
                      <input
                        type="text"
                        value={cloudConfig.model}
                        onChange={(e) =>
                          updateCloudField({ model: e.target.value })
                        }
                        placeholder={
                          CLOUD_PROVIDER_DEFAULTS[cloudConfig.provider]
                            .defaultModel
                        }
                        className="mt-1 w-full rounded-lg border border-stone-200/80 bg-white/80 px-2.5 py-1.5 font-mono text-xs text-stone-900 focus:border-stone-500 focus:outline-none dark:border-white/15 dark:bg-stone-950/65 dark:text-stone-100"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between">
                      <label className="font-medium text-stone-700 dark:text-stone-300">
                        API Key
                      </label>
                      {cloudConfig.apiKey ? (
                        <button
                          type="button"
                          onClick={handleClearKey}
                          className="text-[11px] font-medium text-rose-600 hover:underline dark:text-rose-400"
                        >
                          Clear Key
                        </button>
                      ) : null}
                    </div>
                    <div className="relative mt-1">
                      <input
                        type={showApiKeyValue ? "text" : "password"}
                        value={cloudConfig.apiKey}
                        onChange={(e) =>
                          updateCloudField({ apiKey: e.target.value })
                        }
                        placeholder={
                          CLOUD_PROVIDER_DEFAULTS[cloudConfig.provider]
                            .placeholder
                        }
                        autoComplete="off"
                        className="w-full rounded-lg border border-stone-200/80 bg-white/80 py-1.5 pl-2.5 pr-8 font-mono text-xs text-stone-900 focus:border-stone-500 focus:outline-none dark:border-white/15 dark:bg-stone-950/65 dark:text-stone-100"
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKeyValue((prev) => !prev)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600 dark:text-stone-500 dark:hover:text-stone-300"
                        aria-label={
                          showApiKeyValue ? "Hide API key" : "Show API key"
                        }
                      >
                        {showApiKeyValue ? (
                          <EyeOff className="h-3.5 w-3.5" />
                        ) : (
                          <Eye className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            {cloudNeedsKeyNotice ? (
              <AlertBanner variant="warning" className="mt-4">
                No server default cloud API key is configured. Expand the{" "}
                <button
                  type="button"
                  onClick={() => setShowKeyDrawer(true)}
                  className="font-semibold underline"
                >
                  BYO Cloud VLM Key drawer
                </button>{" "}
                above to provide a session key, or switch to Auto / Local GPU.
              </AlertBanner>
            ) : null}

            {errorMsg ? (
              <AlertBanner variant="error" className="mt-4">
                {errorMsg}
              </AlertBanner>
            ) : null}

            {/* Primary Submit Button */}
            <div className="upload-bottom">
              <p className="text-xs text-stone-500 dark:text-stone-400">
                {files.length <= 1
                  ? "Single document mode: shows grounded preview immediately."
                  : `Batch mode: processes all ${files.length} files & opens Batch Summary.`}
              </p>
              <GlassButton tone="primary"
                type="button"
                disabled={!files.length || submitting}
                onClick={() => void handleSubmit()}
                className="shrink-0"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Extracting...
                  </>
                ) : files.length > 1 ? (
                  <>
                    Run Batch ({files.length})
                    <ArrowRight className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    Extract Document
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </GlassButton>
            </div>
          </div>
        </div>

        {/* Right Column: Instant Extraction Result or Pipeline Overview */}
        <div className="extract-evidence">
          {result ? (
            <div className="glass-surface rounded-2xl p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={result.status} />
                    <ExtractorBadge extractor={result.extractor_used} />
                  </div>
                  <h2 className="mt-2.5 text-lg font-semibold text-stone-900 dark:text-stone-100">
                    {result.extraction.vendor || "Unknown Vendor"}
                  </h2>
                  <p className="text-xs text-stone-500 dark:text-stone-400">
                    {result.filename} · {result.page_count} page
                    {result.page_count > 1 ? "s" : ""} ·{" "}
                    {formatLatency(result.latency_ms)}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">
                    Total
                  </span>
                  <p className="tabular-nums text-xl font-semibold text-stone-900 dark:text-stone-100">
                    {formatCurrency(
                      result.extraction.total_amount,
                      result.extraction.currency,
                    )}
                  </p>
                </div>
              </div>

              {result.duplicate_of_id ? (
                <AlertBanner
                  variant="warning"
                  title="Possible Duplicate Document"
                  className="mt-4"
                >
                  Matches an existing record in the ledger.{" "}
                  <Link
                    href={`/invoices/${result.duplicate_of_id}`}
                    className="font-semibold underline"
                  >
                    Compare existing invoice →
                  </Link>
                </AlertBanner>
              ) : null}

              {result.needs_escalation ||
              result.extraction.validation_warnings.length > 0 ? (
                <AlertBanner
                  variant="warning"
                  title="Review Recommended"
                  className="mt-4"
                >
                  {result.extraction.validation_warnings.length
                    ? result.extraction.validation_warnings.join(" · ")
                    : "Subtotal or total reconciliation check flagged differences."}
                </AlertBanner>
              ) : null}

              {/* Key Fields Summary */}
              <dl className="glass-subtle mt-4 grid grid-cols-2 gap-3 rounded-xl border border-stone-200/70 p-3.5 text-xs dark:border-white/10">
                <div>
                  <dt className="text-stone-500 dark:text-stone-400">
                    Document No.
                  </dt>
                  <dd className="mt-0.5 font-medium text-stone-900 dark:text-stone-100">
                    {result.extraction.receipt_number || "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500 dark:text-stone-400">
                    Issue Date
                  </dt>
                  <dd className="mt-0.5 font-medium text-stone-900 dark:text-stone-100">
                    {result.extraction.date || "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500 dark:text-stone-400">
                    Subtotal
                  </dt>
                  <dd className="tabular-nums mt-0.5 font-medium text-stone-900 dark:text-stone-100">
                    {formatCurrency(
                      result.extraction.subtotal,
                      result.extraction.currency,
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500 dark:text-stone-400">Tax</dt>
                  <dd className="tabular-nums mt-0.5 font-medium text-stone-900 dark:text-stone-100">
                    {formatCurrency(
                      result.extraction.tax_amount,
                      result.extraction.currency,
                    )}
                  </dd>
                </div>
              </dl>

              {/* Reconciliation status */}
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium",
                    result.items_match_subtotal === false
                      ? "bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                      : result.items_match_subtotal === true
                        ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                        : "bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300",
                  )}
                >
                  {result.items_match_subtotal === false ? (
                    <AlertTriangle className="h-3.5 w-3.5" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  )}
                  Items vs Subtotal:{" "}
                  {result.items_match_subtotal === null
                    ? "N/A"
                    : result.items_match_subtotal
                      ? "Matched"
                      : "Mismatch"}
                </span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium",
                    result.totals_reconcile === false
                      ? "bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                      : result.totals_reconcile === true
                        ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                        : "bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300",
                  )}
                >
                  {result.totals_reconcile === false ? (
                    <AlertTriangle className="h-3.5 w-3.5" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  )}
                  Totals Math:{" "}
                  {result.totals_reconcile === null
                    ? "N/A"
                    : result.totals_reconcile
                      ? "Balanced"
                      : "Mismatch"}
                </span>
              </div>

              {/* Line Items Preview */}
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
                  Extracted Line Items ({result.extraction.line_items.length})
                </p>
                {result.extraction.line_items.length > 0 ? (
                  <ul className="mt-2 max-h-44 divide-y divide-stone-200/70 overflow-y-auto rounded-xl border border-stone-200/75 bg-white/55 text-xs dark:divide-white/10 dark:border-white/10 dark:bg-stone-950/40">
                    {result.extraction.line_items.map((item, idx) => (
                      <li
                        key={`${idx}-${item.description}`}
                        className="flex items-center justify-between gap-2 px-3 py-2"
                      >
                        <span className="truncate font-medium text-stone-800 dark:text-stone-200">
                          {item.description}
                        </span>
                        <span className="tabular-nums shrink-0 text-stone-600 dark:text-stone-400">
                          {formatCurrency(
                            item.total_price,
                            result.extraction.currency,
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="glass-subtle mt-2 rounded-xl border border-stone-200/70 px-3 py-2 text-xs text-stone-500 dark:border-white/10 dark:text-stone-400">
                    No individual line items extracted.
                  </p>
                )}
              </div>

              {/* Primary CTA */}
              <div className="mt-5 flex items-center gap-2.5">
                <Link
                  href={`/invoices/${result.invoice_id}`}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl action-primary px-4 py-2.5 text-sm font-semibold text-white shadow-md transition"
                >
                  Open Review Studio
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    setResult(null);
                    setFiles([]);
                  }}
                  className="rounded-xl border border-stone-200/80 bg-white/75 px-3.5 py-2.5 text-sm font-medium text-stone-700 hover:bg-white dark:border-white/12 dark:bg-white/8 dark:text-stone-200 dark:hover:bg-white/14"
                >
                  New
                </button>
              </div>
            </div>
          ) : (
            <aside className="glass-surface pipeline-card rounded-2xl border border-border p-6 lg:p-7 shadow-xs">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  MULTIMODAL PIPELINE
                </span>
              </div>
              <h2 className="font-display text-xl font-semibold text-foreground">From document to data</h2>
              <p className="pipeline-intro text-xs text-muted-foreground mt-1">Review the original evidence alongside structured fields, dates and amounts.</p>
              <ol className="pipeline-steps my-6 space-y-4">
                <li className="flex gap-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-muted font-mono text-xs font-bold text-accent shrink-0">1</span>
                  <div><h3 className="text-xs font-semibold text-foreground mb-0.5">Read the document</h3><p className="text-xs text-muted-foreground">Prepare pages and locate text without altering the source.</p></div>
                </li>
                <li className="flex gap-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-muted font-mono text-xs font-bold text-accent shrink-0">2</span>
                  <div><h3 className="text-xs font-semibold text-foreground mb-0.5">Structure the information</h3><p className="text-xs text-muted-foreground">Identify parties, dates, line items and financial amounts.</p></div>
                </li>
                <li className="flex gap-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-muted font-mono text-xs font-bold text-accent shrink-0">3</span>
                  <div><h3 className="text-xs font-semibold text-foreground mb-0.5">Verify with evidence</h3><p className="text-xs text-muted-foreground">Inspect source-linked values and reconcile totals before saving.</p></div>
                </li>
              </ol>
              <details className="pipeline-details border-t border-border/70 pt-3 text-xs text-muted-foreground">
                <summary className="font-mono text-xs cursor-pointer hover:text-foreground transition-colors mb-2">How processing works</summary>
                <p className="leading-relaxed">Uploads are hashed for duplicates. Indra OCR 1.1 grounds text in normalized coordinates, then Qwen3.5-0.8B LoRA or the configured cloud model extracts structured values. Math checks flag discrepancies for review.</p>
                <p className="leading-relaxed mt-2">{health?.local_vlm.weights_present ? "Local model weights are available." : "Local model readiness is reported by the processing engine."} Cloud settings remain optional and are held for this session.</p>
              </details>
              <div className="pipeline-footer flex items-center justify-between border-t border-border/70 pt-4 mt-4 text-xs font-mono">
                <button type="button" onClick={() => setShowKeyDrawer(true)} className="text-muted-foreground hover:text-foreground cursor-pointer">Advanced settings</button>
                <Link href="/batch" className="text-accent hover:underline">Batch exports →</Link>
              </div>
            </aside>
          )}
        </div>
      </div>
      <RecentDocuments />
    </div>
  );
}
