"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FilterX,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import {
  ApiError,
  deleteInvoice,
  downloadBulkReport,
  listInvoices,
} from "@/lib/api-client";
import { cn, formatCurrency } from "@/lib/format";
import type { InvoiceStatus, InvoiceSummary } from "@/lib/types";
import {
  AlertBanner,
  ConfirmModal,
  ExtractorBadge,
  StatusBadge,
} from "@/components/ui";

const PAGE_SIZE = 25;

export default function InvoicesLedgerPage() {
  const [items, setItems] = useState<InvoiceSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [noticeMsg, setNoticeMsg] = useState<string | null>(null);

  // Filters
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [status, setStatus] = useState<InvoiceStatus | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Multi-select & modals
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<InvoiceSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [reloadNonce, setReloadNonce] = useState(0);

  useEffect(() => {
    let active = true;
    listInvoices({
      search: appliedSearch,
      status,
      date_from: dateFrom,
      date_to: dateTo,
      limit: PAGE_SIZE,
      offset,
    })
      .then((res) => {
        if (!active) return;
        setItems(res.items);
        setTotal(res.total);
        setSelectedIds(new Set());
        setErrorMsg(null);
      })
      .catch((error) => {
        if (!active) return;
        setErrorMsg(
          error instanceof ApiError
            ? error.detail
            : "Failed to fetch invoices.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [appliedSearch, status, dateFrom, dateTo, offset, reloadNonce]);

  // Debounce search text
  useEffect(() => {
    if (searchInput === appliedSearch) return;
    const timer = setTimeout(() => {
      setLoading(true);
      setOffset(0);
      setAppliedSearch(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, appliedSearch]);

  const resetFilters = () => {
    setLoading(true);
    setSearchInput("");
    setAppliedSearch("");
    setStatus("");
    setDateFrom("");
    setDateTo("");
    setOffset(0);
  };

  const toggleAllVisible = () => {
    if (selectedIds.size === items.length && items.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((item) => item.id)));
    }
  };

  const toggleOne = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExportSelected = async (format: "csv" | "json" | "html") => {
    const ids = Array.from(selectedIds);
    if (!ids.length) return;
    setExporting(true);
    setErrorMsg(null);
    setNoticeMsg(null);
    try {
      const filename = await downloadBulkReport({
        invoice_ids: ids,
        format,
      });
      setNoticeMsg(`Downloaded ${filename} (${ids.length} selected).`);
    } catch (error) {
      setErrorMsg(
        error instanceof ApiError ? error.detail : "Failed to export report.",
      );
    } finally {
      setExporting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setErrorMsg(null);
    try {
      await deleteInvoice(deleteTarget.id);
      setNoticeMsg(
        `Deleted "${deleteTarget.vendor || deleteTarget.filename}".`,
      );
      setDeleteTarget(null);
      setLoading(true);
      setReloadNonce((n) => n + 1);
    } catch (error) {
      setErrorMsg(
        error instanceof ApiError ? error.detail : "Failed to delete invoice.",
      );
    } finally {
      setDeleting(false);
    }
  };

  const hasFilters = Boolean(appliedSearch || status || dateFrom || dateTo);
  const startRow = total === 0 ? 0 : offset + 1;
  const endRow = Math.min(offset + items.length, total);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Invoice Ledger
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Search extracted documents, inspect reconciliation flags, open HITL
            review, or export filtered sets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/batch"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Batch Summary
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Extraction
          </Link>
        </div>
      </div>

      {/* Filters Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          <div className="relative md:col-span-5">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search vendor, receipt #, or filename..."
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>

          <div className="md:col-span-3">
            <select
              value={status}
              onChange={(e) => {
                setLoading(true);
                setOffset(0);
                setStatus(e.target.value as InvoiceStatus | "");
              }}
              aria-label="Filter by status"
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="needs_review">Needs Review</option>
              <option value="extracted">Extracted</option>
              <option value="verified">Verified</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="flex items-center gap-2 md:col-span-4">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setLoading(true);
                setOffset(0);
                setDateFrom(e.target.value);
              }}
              aria-label="Issue date from"
              className="w-full rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-800 focus:border-indigo-500 focus:outline-none"
            />
            <span className="text-xs text-slate-400">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setLoading(true);
                setOffset(0);
                setDateTo(e.target.value);
              }}
              aria-label="Issue date to"
              className="w-full rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-800 focus:border-indigo-500 focus:outline-none"
            />
            {hasFilters ? (
              <button
                type="button"
                onClick={resetFilters}
                title="Clear all filters"
                className="shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-2 text-slate-600 hover:bg-slate-100"
              >
                <FilterX className="h-4 w-4" />
              </button>
            ) : null}
          </div>
        </div>

        {/* Multi-select Contextual Bar */}
        {selectedIds.size > 0 ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-200 bg-indigo-50/70 px-3.5 py-2 text-xs">
            <span className="font-semibold text-indigo-950">
              {selectedIds.size} invoice{selectedIds.size > 1 ? "s" : ""}{" "}
              selected
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("csv")}
                className="inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 font-medium text-slate-800 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5" />
                CSV
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("json")}
                className="inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 font-medium text-slate-800 ring-1 ring-slate-200 hover:bg-slate-50 disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5" />
                JSON
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("html")}
                className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5" />
                HTML Report
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {errorMsg ? <AlertBanner variant="error">{errorMsg}</AlertBanner> : null}
      {noticeMsg ? <AlertBanner variant="success">{noticeMsg}</AlertBanner> : null}

      {/* Ledger Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={
                      items.length > 0 && selectedIds.size === items.length
                    }
                    onChange={toggleAllVisible}
                    aria-label="Select all visible invoices"
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                </th>
                <th className="px-4 py-3">Vendor / Document</th>
                <th className="px-4 py-3">Receipt #</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3">Math</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Extractor</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx}>
                    <td colSpan={9} className="px-4 py-4">
                      <div className="h-5 animate-pulse rounded bg-slate-100" />
                    </td>
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="px-4 py-12 text-center text-sm text-slate-500"
                  >
                    {hasFilters
                      ? "No invoices match these filters."
                      : "No invoices processed yet. Upload your first document to begin."}
                  </td>
                </tr>
              ) : (
                items.map((inv) => {
                  const mathOk =
                    inv.items_match_subtotal !== false &&
                    inv.totals_reconcile !== false;
                  const mathChecked =
                    inv.items_match_subtotal !== null ||
                    inv.totals_reconcile !== null;

                  return (
                    <tr
                      key={inv.id}
                      className={cn(
                        "transition hover:bg-slate-50/80",
                        selectedIds.has(inv.id) && "bg-indigo-50/40",
                      )}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(inv.id)}
                          onChange={() => toggleOne(inv.id)}
                          aria-label={`Select ${inv.vendor || inv.filename}`}
                          className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0">
                            <Link
                              href={`/invoices/${inv.id}`}
                              className="block truncate font-semibold text-slate-900 hover:text-indigo-600"
                            >
                              {inv.vendor || "Unknown Vendor"}
                            </Link>
                            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                              <span className="max-w-[200px] truncate">
                                {inv.filename}
                              </span>
                              <span>· {inv.page_count}p</span>
                              {inv.duplicate_of_id ? (
                                <Link
                                  href={`/invoices/${inv.duplicate_of_id}`}
                                  title="Duplicate detected — view original"
                                  className="inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800 ring-1 ring-amber-600/15 hover:bg-amber-100"
                                >
                                  <Copy className="h-2.5 w-2.5" />
                                  Duplicate
                                </Link>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">
                        {inv.receipt_number || "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 tabular-nums text-xs text-slate-700">
                        {inv.date || "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums font-semibold text-slate-900">
                        {formatCurrency(inv.total_amount, inv.currency)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {!mathChecked ? (
                          <span className="text-xs text-slate-400">—</span>
                        ) : mathOk ? (
                          <span
                            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700"
                            title="Line items & totals reconcile"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            OK
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 text-xs font-medium text-amber-700"
                            title="Discrepancy detected in subtotal/totals"
                          >
                            <AlertTriangle className="h-3.5 w-3.5" />
                            Check
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <ExtractorBadge extractor={inv.extractor_used} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <Link
                            href={`/invoices/${inv.id}`}
                            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-700"
                          >
                            Review
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(inv)}
                            className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                            aria-label={`Delete ${inv.vendor || inv.filename}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 bg-slate-50/70 px-4 py-3 text-xs text-slate-600 sm:flex-row">
          <span>
            Showing <span className="font-semibold">{startRow}</span>–
            <span className="font-semibold">{endRow}</span> of{" "}
            <span className="font-semibold">{total}</span> invoices
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={offset === 0 || loading}
              onClick={() => {
                setLoading(true);
                setOffset((prev) => Math.max(0, prev - PAGE_SIZE));
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </button>
            <button
              type="button"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => {
                setLoading(true);
                setOffset((prev) => prev + PAGE_SIZE);
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={deleteTarget !== null}
        title="Delete invoice permanently?"
        description={
          deleteTarget
            ? `This will remove "${deleteTarget.vendor || deleteTarget.filename}" (${deleteTarget.filename}) and all stored page assets from Postgres and object storage.`
            : ""
        }
        confirmLabel="Delete Invoice"
        busy={deleting}
        onCancel={() => !deleting && setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}
