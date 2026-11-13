"use client";

import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { WorkspaceHeader } from "@/components/WorkspaceHeader";
import Link from "next/link";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileCode2,
  FileSpreadsheet,
  FileText,
  Layers,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  ApiError,
  downloadBulkReport,
  listInvoices,
} from "@/lib/api-client";
import {
  clearLatestBatch,
  getLatestBatchRaw,
  parseLatestBatchRaw,
  subscribeSessionStore,
} from "@/lib/cloud-settings";
import {
  formatCurrency,
  formatDateTime,
  formatLatency,
  groupCurrencyTotals,
} from "@/lib/format";
import type { InvoiceStatus, InvoiceSummary } from "@/lib/types";
import { AlertBanner, ExtractorBadge, StatusBadge } from "@/components/ui";

export default function BatchSummaryPage() {
  const latestBatchRaw = useSyncExternalStore(
    subscribeSessionStore,
    getLatestBatchRaw,
    () => "",
  );
  const latestRun = useMemo(
    () => parseLatestBatchRaw(latestBatchRaw),
    [latestBatchRaw],
  );

  const [ledgerItems, setLedgerItems] = useState<InvoiceSummary[]>([]);
  const [ledgerTotal, setLedgerTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");
  const [reloadNonce, setReloadNonce] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listInvoices({
      status: statusFilter,
      limit: 100,
      offset: 0,
    })
      .then((res) => {
        if (!active) return;
        setLedgerItems(res.items);
        setLedgerTotal(res.total);
        setErrorMsg(null);
      })
      .catch((error) => {
        if (!active) return;
        setErrorMsg(
          error instanceof ApiError
            ? error.detail
            : "Failed to load invoice summary from backend.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [statusFilter, reloadNonce]);

  const triggerReload = () => {
    setLoading(true);
    setReloadNonce((n) => n + 1);
  };

  const handleBulkExport = async (
    format: "csv" | "json" | "html",
    invoiceIds?: string[],
    label?: string,
  ) => {
    setExporting(`${label ?? "ledger"}-${format}`);
    setErrorMsg(null);
    setExportSuccess(null);
    try {
      const filename = await downloadBulkReport({
        format,
        invoice_ids: invoiceIds && invoiceIds.length ? invoiceIds : null,
        status: !invoiceIds?.length && statusFilter ? statusFilter : null,
      });
      setExportSuccess(`Downloaded ${filename}`);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMsg(error.detail);
      } else {
        setErrorMsg("Report export failed.");
      }
    } finally {
      setExporting(null);
    }
  };

  const latestSuccessIds =
    latestRun?.batch.items
      .filter((item) => item.ok && item.result)
      .map((item) => item.result!.invoice_id) ?? [];

  const latestCurrencyBuckets = latestRun
    ? groupCurrencyTotals(
        latestRun.batch.items
          .filter((i) => i.ok && i.result)
          .map((i) => ({
            currency: i.result!.extraction.currency,
            total_amount: i.result!.extraction.total_amount,
          })),
      )
    : [];

  const ledgerCurrencyBuckets = groupCurrencyTotals(ledgerItems);

  const statusCounts = ledgerItems.reduce(
    (acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  const reconciledCount = ledgerItems.filter(
    (item) => item.totals_reconcile === true,
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <WorkspaceHeader
        eyebrow="FINANCIAL RECONCILIATION // ISO 4217"
        title="Batch Summary & Bulk Exports"
        description="Totals are strictly grouped by ISO currency code (never mixed) and exportable as CSV, JSON, or standalone HTML reports."
        actions={
          <Link
            href="/extract"
            className="inline-flex items-center gap-2 rounded-full action-primary px-4 py-2 font-mono text-xs font-semibold text-white shadow-sm hover:shadow transition-all"
          >
            <Layers className="h-3.5 w-3.5" />
            Upload New Batch
          </Link>
        }
      />

      {errorMsg ? <AlertBanner variant="error">{errorMsg}</AlertBanner> : null}
      {exportSuccess ? (
        <AlertBanner variant="success">{exportSuccess}</AlertBanner>
      ) : null}

      {/* Latest Batch Session Card (if present) */}
      {latestRun ? (
        <section className="glass-surface rounded-2xl border border-border p-5">
          <div className="flex flex-col justify-between gap-3 border-b border-border pb-4 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-accent/15 px-2.5 py-0.5 font-mono text-xs font-semibold text-accent ring-1 ring-accent/30">
                  Latest Upload Run
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  {formatDateTime(latestRun.savedAt)}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-foreground">
                Processed{" "}
                <span className="font-mono font-semibold text-foreground">
                  {latestRun.batch.total}
                </span>{" "}
                files:{" "}
                <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                  {latestRun.batch.succeeded} succeeded
                </span>
                {latestRun.batch.failed > 0 ? (
                  <>
                    {" "}
                    ·{" "}
                    <span className="font-mono font-semibold text-rose-600 dark:text-rose-400">
                      {latestRun.batch.failed} failed
                    </span>
                  </>
                ) : null}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {latestSuccessIds.length > 0 ? (
                <>
                  <GlassButton
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("csv", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3 py-1.5 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 disabled:opacity-50 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5 text-muted-foreground" />
                    Batch CSV
                  </GlassButton>
                  <GlassButton
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("json", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3 py-1.5 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 disabled:opacity-50 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5 text-muted-foreground" />
                    Batch JSON
                  </GlassButton>
                  <GlassButton
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("html", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3 py-1.5 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 disabled:opacity-50 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5 text-muted-foreground" />
                    Batch HTML
                  </GlassButton>
                </>
              ) : null}
              <GlassButton
                type="button"
                onClick={() => clearLatestBatch()}
                className="inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 font-mono text-xs text-muted-foreground hover:bg-rose-500/15 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Dismiss
              </GlassButton>
            </div>
          </div>

          {latestCurrencyBuckets.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-3">
              {latestCurrencyBuckets.map((bucket) => (
                <div
                  key={bucket.currency}
                  className="glass-subtle rounded-xl border border-border px-3.5 py-2.5"
                >
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {bucket.currency} ({bucket.count} doc
                    {bucket.count > 1 ? "s" : ""})
                  </span>
                  <p className="tabular-nums mt-0.5 font-mono text-base font-semibold text-foreground">
                    {bucket.amountCount > 0
                      ? formatCurrency(
                          bucket.total,
                          bucket.currency === "UNSPECIFIED"
                            ? null
                            : bucket.currency,
                        )
                      : "—"}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="mt-4 divide-y divide-border/60 rounded-xl border border-border bg-card/50">
            {latestRun.batch.items.map((item, idx) => (
              <div
                key={`${idx}-${item.filename}`}
                className="flex flex-col justify-between gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  {item.ok && item.result ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
                  )}
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">
                      {item.ok && item.result
                        ? item.result.extraction.vendor || item.filename
                        : item.filename}
                    </p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {item.ok && item.result
                        ? `${item.filename} · ${formatLatency(item.result.latency_ms)}`
                        : item.error || "Extraction failed"}
                    </p>
                  </div>
                </div>

                {item.ok && item.result ? (
                  <div className="flex shrink-0 items-center gap-3">
                    <ExtractorBadge extractor={item.result.extractor_used} />
                    <StatusBadge status={item.result.status} />
                    <span className="tabular-nums font-mono font-semibold text-foreground">
                      {formatCurrency(
                        item.result.extraction.total_amount,
                        item.result.extraction.currency,
                      )}
                    </span>
                    <Link
                      href={`/invoices/${item.result.invoice_id}`}
                      className="rounded-full border border-border bg-card/80 px-2.5 py-1 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 transition-colors"
                    >
                      Review
                    </Link>
                  </div>
                ) : (
                  <StatusBadge status="failed" />
                )}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* Ledger Aggregate & Export Section */}
      <section className="glass-surface rounded-2xl border border-border p-5">
        <div className="flex flex-col justify-between gap-4 border-b border-border pb-4 md:flex-row md:items-center">
          <div>
            <h2 className="font-display text-xl font-semibold text-foreground">
              Ledger Summary & Export Controls
            </h2>
            <p className="font-mono text-xs text-muted-foreground mt-0.5">
              Showing {ledgerItems.length} of {ledgerTotal} stored records
              {ledgerTotal > ledgerItems.length ? " (top 100 loaded)" : ""}.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => {
                setLoading(true);
                setStatusFilter(e.target.value as InvoiceStatus | "");
              }}
              aria-label="Filter summary by status"
              className="lg-select w-full"
            >
              <option value="">All Statuses</option>
              <option value="verified">Verified</option>
              <option value="needs_review">Needs Review</option>
              <option value="extracted">Extracted</option>
              <option value="failed">Failed</option>
            </select>

            <GlassButton
              type="button"
              onClick={triggerReload}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-1.5 font-mono text-xs font-medium text-foreground hover:bg-card disabled:opacity-40 transition-colors"
            >
              <RefreshCw
                className={
                  loading ? "h-3.5 w-3.5 animate-spin text-accent" : "h-3.5 w-3.5 text-muted-foreground"
                }
              />
              Refresh
            </GlassButton>
          </div>
        </div>

        {/* Currency-grouped KPI cards */}
        <div className="mt-5">
          <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Totals by Currency
          </h3>
          {loading ? (
            <div className="mt-2 h-20 animate-pulse rounded-xl bg-muted/60" />
          ) : ledgerCurrencyBuckets.length > 0 ? (
            <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {ledgerCurrencyBuckets.map((bucket) => (
                <div
                  key={bucket.currency}
                  className="glass-subtle rounded-xl border border-border p-4"
                >
                  <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                    <span className="rounded-full bg-accent/15 px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-accent ring-1 ring-accent/25">
                      {bucket.currency}
                    </span>
                    <span>
                      {bucket.count} doc{bucket.count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <p className="tabular-nums mt-3 font-display text-2xl lg:text-3xl font-semibold text-foreground">
                    {bucket.amountCount > 0
                      ? formatCurrency(
                          bucket.total,
                          bucket.currency === "UNSPECIFIED"
                            ? null
                            : bucket.currency,
                        )
                      : "—"}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="glass-subtle mt-2 rounded-xl border border-border px-4 py-3 text-sm text-muted-foreground">
              No invoices match the current filter.
            </p>
          )}
        </div>

        {/* Status breakdown & reconciliation health */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="glass-subtle rounded-xl border border-border p-3.5">
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Verified
            </span>
            <p className="tabular-nums mt-1 font-mono text-xl font-bold text-emerald-600 dark:text-emerald-400">
              {statusCounts.verified ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-border p-3.5">
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Needs Review
            </span>
            <p className="tabular-nums mt-1 font-mono text-xl font-bold text-amber-600 dark:text-amber-400">
              {statusCounts.needs_review ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-border p-3.5">
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Extracted
            </span>
            <p className="tabular-nums mt-1 font-mono text-xl font-bold text-foreground">
              {statusCounts.extracted ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-border p-3.5">
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Failed
            </span>
            <p className="tabular-nums mt-1 font-mono text-xl font-bold text-rose-600 dark:text-rose-400">
              {statusCounts.failed ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-border p-3.5">
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Math Balanced
            </span>
            <p className="tabular-nums mt-1 font-mono text-xl font-bold text-foreground">
              {ledgerItems.length
                ? `${reconciledCount}/${ledgerItems.length}`
                : "0"}
            </p>
          </div>
        </div>

        {/* Bulk Export Action Bar */}
        <div className="glass-subtle mt-6 flex flex-col justify-between gap-3 rounded-2xl border border-border px-4 py-3.5 sm:flex-row sm:items-center">
          <div className="font-mono text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">
              Bulk Report Download
            </span>{" "}
            — exports{" "}
            {statusFilter
              ? `all "${statusFilter}" invoices`
              : "all ledger invoices"}
            .
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <GlassButton
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("csv")}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-2 font-mono text-xs font-semibold text-foreground hover:bg-card hover:border-accent/40 disabled:opacity-50 transition-colors"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Export CSV
            </GlassButton>
            <GlassButton
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("json")}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-2 font-mono text-xs font-semibold text-foreground hover:bg-card hover:border-accent/40 disabled:opacity-50 transition-colors"
            >
              <FileCode2 className="h-4 w-4 text-muted-foreground" />
              Export JSON
            </GlassButton>
            <GlassButton
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("html")}
              className="inline-flex items-center gap-1.5 rounded-full action-primary px-4 py-2 font-mono text-xs font-semibold text-white shadow-sm hover:shadow disabled:opacity-50 transition-all"
            >
              <FileText className="h-4 w-4" />
              Export HTML Report
            </GlassButton>
          </div>
        </div>
      </section>
    </div>
  );
}
