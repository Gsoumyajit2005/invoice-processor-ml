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
import type {
  InvoiceStatus,
  InvoiceSummary,
} from "@/lib/types";
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
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Batch Summary & Bulk Exports
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Totals are strictly grouped by ISO currency code (never mixed) and
            exportable as CSV, JSON, or standalone HTML reports.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-xs transition hover:bg-indigo-700"
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
        <section className="rounded-2xl border border-indigo-200 bg-white p-5 shadow-xs">
          <div className="flex flex-col justify-between gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                  Latest Upload Run
                </span>
                <span className="text-xs text-slate-500">
                  {formatDateTime(latestRun.savedAt)}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-slate-700">
                Processed{" "}
                <span className="font-semibold text-slate-900">
                  {latestRun.batch.total}
                </span>{" "}
                files:{" "}
                <span className="font-semibold text-emerald-700">
                  {latestRun.batch.succeeded} succeeded
                </span>
                {latestRun.batch.failed > 0 ? (
                  <>
                    {" "}
                    ·{" "}
                    <span className="font-semibold text-rose-700">
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
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
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
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
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
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Batch HTML
                  </button>
                </>
              ) : null}
              <button
                type="button"
                onClick={() => clearLatestBatch()}
                className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-100 hover:text-rose-600"
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
                  className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5"
                >
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {bucket.currency} ({bucket.count} doc
                    {bucket.count > 1 ? "s" : ""})
                  </span>
                  <p className="tabular-nums mt-0.5 text-base font-semibold text-slate-900">
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

          <div className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-200">
            {latestRun.batch.items.map((item, idx) => (
              <div
                key={`${idx}-${item.filename}`}
                className="flex flex-col justify-between gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  {item.ok && item.result ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
                  )}
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-900">
                      {item.ok && item.result
                        ? item.result.extraction.vendor || item.filename
                        : item.filename}
                    </p>
                    <p className="truncate text-xs text-slate-500">
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
                    <span className="tabular-nums font-semibold text-slate-900">
                      {formatCurrency(
                        item.result.extraction.total_amount,
                        item.result.extraction.currency,
                      )}
                    </span>
                    <Link
                      href={`/invoices/${item.result.invoice_id}`}
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
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
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-100 pb-4 md:flex-row md:items-center">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Ledger Summary & Export Controls
            </h2>
            <p className="text-xs text-slate-500">
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
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 focus:border-indigo-500 focus:outline-none"
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
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw
                className={loading ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"}
              />
              Refresh
            </button>
          </div>
        </div>

        {/* Currency-grouped KPI cards */}
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Totals by Currency
          </h3>
          {loading ? (
            <div className="mt-2 h-20 animate-pulse rounded-xl bg-slate-100" />
          ) : ledgerCurrencyBuckets.length > 0 ? (
            <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {ledgerCurrencyBuckets.map((bucket) => (
                <div
                  key={bucket.currency}
                  className="rounded-xl border border-slate-200 bg-slate-50/70 p-4"
                >
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold uppercase tracking-wider text-slate-700">
                      {bucket.currency}
                    </span>
                    <span>
                      {bucket.count} doc{bucket.count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <p className="tabular-nums mt-2 text-xl font-semibold text-slate-900">
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
            <p className="mt-2 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-500">
              No invoices match the current filter.
            </p>
          )}
        </div>

        {/* Status breakdown & reconciliation health */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="rounded-xl border border-slate-200 bg-white p-3.5">
            <span className="text-xs text-slate-500">Verified</span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-emerald-700">
              {statusCounts.verified ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3.5">
            <span className="text-xs text-slate-500">Needs Review</span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-amber-700">
              {statusCounts.needs_review ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3.5">
            <span className="text-xs text-slate-500">Extracted</span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-sky-700">
              {statusCounts.extracted ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3.5">
            <span className="text-xs text-slate-500">Failed</span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-rose-700">
              {statusCounts.failed ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3.5">
            <span className="text-xs text-slate-500">Math Balanced</span>
            <p className="tabular-nums mt-1 text-lg font-semibold text-slate-900">
              {ledgerItems.length
                ? `${reconciledCount}/${ledgerItems.length}`
                : "0"}
            </p>
          </div>
        </div>

        {/* Bulk Export Action Bar */}
        <div className="mt-6 flex flex-col justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 sm:flex-row sm:items-center">
          <div className="text-xs text-slate-600">
            <span className="font-semibold text-slate-900">
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
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 shadow-2xs hover:bg-slate-50 disabled:opacity-50"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
              Export CSV
            </button>
            <button
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("json")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 shadow-2xs hover:bg-slate-50 disabled:opacity-50"
            >
              <FileCode2 className="h-4 w-4 text-indigo-600" />
              Export JSON
            </button>
            <button
              type="button"
              disabled={!ledgerItems.length || exporting !== null}
              onClick={() => void handleBulkExport("html")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-slate-800 disabled:opacity-50"
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
