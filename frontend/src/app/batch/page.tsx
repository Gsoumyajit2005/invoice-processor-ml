"use client";

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
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Batch Summary & Bulk Exports
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Totals are strictly grouped by ISO currency code (never mixed) and
            exportable as CSV, JSON, or standalone HTML reports.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-500/25 transition hover:from-indigo-500 hover:to-violet-500"
        >
          <Layers className="h-4 w-4" />
          Upload New Batch
        </Link>
      </div>

      {errorMsg ? <AlertBanner variant="error">{errorMsg}</AlertBanner> : null}
      {exportSuccess ? (
        <AlertBanner variant="success">{exportSuccess}</AlertBanner>
      ) : null}

      {/* Latest Batch Session Card (if present) */}
      {latestRun ? (
        <section className="glass-surface rounded-2xl border-indigo-300/60 p-5 dark:border-indigo-400/25">
          <div className="flex flex-col justify-between gap-3 border-b border-slate-200/70 pb-4 dark:border-white/10 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-indigo-500/12 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-500/20 dark:bg-indigo-400/15 dark:text-indigo-300 dark:ring-indigo-400/25">
                  Latest Upload Run
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {formatDateTime(latestRun.savedAt)}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-slate-700 dark:text-slate-300">
                Processed{" "}
                <span className="font-semibold text-slate-900 dark:text-slate-100">
                  {latestRun.batch.total}
                </span>{" "}
                files:{" "}
                <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                  {latestRun.batch.succeeded} succeeded
                </span>
                {latestRun.batch.failed > 0 ? (
                  <>
                    {" "}
                    ·{" "}
                    <span className="font-semibold text-rose-700 dark:text-rose-400">
                      {latestRun.batch.failed} failed
                    </span>
                  </>
                ) : null}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {latestSuccessIds.length > 0 ? (
                <>
                  <button
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("csv", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md hover:bg-white disabled:opacity-50 dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Batch CSV
                  </button>
                  <button
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("json", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md hover:bg-white disabled:opacity-50 dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Batch JSON
                  </button>
                  <button
                    type="button"
                    disabled={exporting !== null}
                    onClick={() =>
                      void handleBulkExport("html", latestSuccessIds, "latest")
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md hover:bg-white disabled:opacity-50 dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Batch HTML
                  </button>
                </>
              ) : null}
              <button
                type="button"
                onClick={() => clearLatestBatch()}
                className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-200/60 hover:text-rose-600 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-rose-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Dismiss
              </button>
            </div>
          </div>

          {latestCurrencyBuckets.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-3">
              {latestCurrencyBuckets.map((bucket) => (
                <div
                  key={bucket.currency}
                  className="glass-subtle rounded-xl border border-slate-200/70 px-3.5 py-2.5 dark:border-white/10"
                >
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    {bucket.currency} ({bucket.count} doc
                    {bucket.count > 1 ? "s" : ""})
                  </span>
                  <p className="tabular-nums mt-0.5 text-base font-semibold text-slate-900 dark:text-slate-100">
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

          <div className="mt-4 divide-y divide-slate-200/70 rounded-xl border border-slate-200/75 bg-white/45 backdrop-blur-sm dark:divide-white/10 dark:border-white/10 dark:bg-slate-950/35">
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
                    <p className="truncate font-medium text-slate-900 dark:text-slate-100">
                      {item.ok && item.result
                        ? item.result.extraction.vendor || item.filename
                        : item.filename}
                    </p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">
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
                    <span className="tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                      {formatCurrency(
                        item.result.extraction.total_amount,
                        item.result.extraction.currency,
                      )}
                    </span>
                    <Link
                      href={`/invoices/${item.result.invoice_id}`}
                      className="rounded-lg border border-slate-200/80 bg-white/75 px-2.5 py-1 text-xs font-medium text-indigo-600 backdrop-blur-sm hover:bg-indigo-50 dark:border-white/12 dark:bg-white/8 dark:text-indigo-300 dark:hover:bg-indigo-500/20"
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
      <section className="glass-surface rounded-2xl p-5">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-200/70 pb-4 dark:border-white/10 md:flex-row md:items-center">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Ledger Summary & Export Controls
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
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
              className="rounded-lg border border-slate-200/80 bg-white/75 px-3 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md focus:border-indigo-500 focus:outline-none dark:border-white/12 dark:bg-slate-950/60 dark:text-slate-200"
            >
              <option value="">All Statuses</option>
              <option value="verified">Verified</option>
              <option value="needs_review">Needs Review</option>
              <option value="extracted">Extracted</option>
              <option value="failed">Failed</option>
            </select>

            <button
              type="button"
              onClick={triggerReload}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/75 px-3 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md hover:bg-white dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
            >
              <RefreshCw
                className={
                  loading ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"
                }
              />
              Refresh
            </button>
          </div>
        </div>

        {/* Currency-grouped KPI cards */}
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Totals by Currency
          </h3>
          {loading ? (
            <div className="mt-2 h-20 animate-pulse rounded-xl bg-slate-200/60 dark:bg-white/10" />
          ) : ledgerCurrencyBuckets.length > 0 ? (
            <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {ledgerCurrencyBuckets.map((bucket) => (
                <div
                  key={bucket.currency}
                  className="glass-subtle rounded-xl border border-slate-200/70 p-4 dark:border-white/10"
                >
                  <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      {bucket.currency}
                    </span>
                    <span>
                      {bucket.count} doc{bucket.count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <p className="tabular-nums mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
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
            <p className="glass-subtle mt-2 rounded-xl border border-slate-200/70 px-4 py-3 text-sm text-slate-500 dark:border-white/10 dark:text-slate-400">
              No invoices match the current filter.
            </p>
          )}
        </div>

        {/* Status breakdown & reconciliation health */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="glass-subtle rounded-xl border border-slate-200/70 p-3.5 dark:border-white/10">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Verified
            </span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-emerald-700 dark:text-emerald-400">
              {statusCounts.verified ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-slate-200/70 p-3.5 dark:border-white/10">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Needs Review
            </span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-amber-700 dark:text-amber-400">
              {statusCounts.needs_review ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-slate-200/70 p-3.5 dark:border-white/10">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Extracted
            </span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-sky-700 dark:text-sky-400">
              {statusCounts.extracted ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-slate-200/70 p-3.5 dark:border-white/10">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Failed
            </span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-rose-700 dark:text-rose-400">
              {statusCounts.failed ?? 0}
            </p>
          </div>
          <div className="glass-subtle rounded-xl border border-slate-200/70 p-3.5 dark:border-white/10">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Math Balanced
            </span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
              {ledgerItems.length
                ? `${reconciledCount}/${ledgerItems.length}`
                : "0"}
            </p>
          </div>
        </div>

        {/* Bulk Export Action Bar */}
        <div className="glass-subtle mt-6 flex flex-col justify-between gap-3 rounded-xl border border-slate-200/70 px-4 py-3.5 dark:border-white/10 sm:flex-row sm:items-center">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-900 dark:text-slate-100">
              Bulk Report Download
            </span>{" "}
            — exports{" "}
            {statusFilter
              ? `all "${statusFilter}" invoices`
              : "all ledger invoices"}
            .
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("csv")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/75 px-3.5 py-2 text-xs font-semibold text-slate-800 backdrop-blur-md shadow-2xs hover:bg-white disabled:opacity-50 dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Export CSV
            </button>
            <button
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("json")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/75 px-3.5 py-2 text-xs font-semibold text-slate-800 backdrop-blur-md shadow-2xs hover:bg-white disabled:opacity-50 dark:border-white/12 dark:bg-white/8 dark:text-slate-200 dark:hover:bg-white/14"
            >
              <FileCode2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              Export JSON
            </button>
            <button
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("html")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-500/20 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50"
            >
              <FileText className="h-4 w-4" />
              Export HTML Report
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
