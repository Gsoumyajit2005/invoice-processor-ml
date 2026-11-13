"use client";

import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { WorkspaceHeader } from "@/components/WorkspaceHeader";
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
      <WorkspaceHeader
        eyebrow="RELATIONAL LEDGER // AUDIT TRAILS"
        title="Invoices"
        description="Search extracted documents, inspect reconciliation flags, open HITL review, or export filtered sets."
        actions={
          <>
            <Link
              href="/batch"
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-2 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 transition-colors shadow-xs"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
              Batch Summary
            </Link>
            <Link
              href="/extract"
              className="inline-flex items-center gap-1.5 rounded-full action-primary px-4 py-2 font-mono text-xs font-semibold text-white shadow-sm hover:shadow transition-all"
            >
              <Plus className="h-3.5 w-3.5" />
              New Extraction
            </Link>
          </>
        }
      />

      {/* Filters Card */}
      <div className="glass-surface invoice-filters rounded-2xl p-4 border border-border">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          <div className="relative md:col-span-5">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search vendor, receipt #, or filename..."
              className="w-full rounded-xl border border-border bg-card/90 py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
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
              className="lg-select w-full"
            >
              <option value="">All Statuses</option>
              <option value="needs_review">Needs Review</option>
              <option value="extracted">Extracted</option>
              <option value="verified">Verified</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="invoice-date-range flex items-center gap-2 md:col-span-4">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setLoading(true);
                setOffset(0);
                setDateFrom(e.target.value);
              }}
              aria-label="Issue date from"
              className="w-full rounded-xl border border-border bg-card/90 px-2.5 py-2 text-xs font-mono text-foreground focus:border-accent focus:outline-none"
            />
            <span className="text-xs font-mono text-muted-foreground">
              to
            </span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setLoading(true);
                setOffset(0);
                setDateTo(e.target.value);
              }}
              aria-label="Issue date to"
              className="w-full rounded-xl border border-border bg-card/90 px-2.5 py-2 text-xs font-mono text-foreground focus:border-accent focus:outline-none"
            />
            {hasFilters ? (
              <GlassButton
                type="button"
                onClick={resetFilters}
                title="Clear all filters"
                className="shrink-0 rounded-xl border border-border bg-card/80 p-2 text-muted-foreground hover:text-foreground hover:bg-card"
              >
                <FilterX className="h-4 w-4" />
              </GlassButton>
            ) : null}
          </div>
        </div>

        {/* Multi-select Contextual Bar */}
        {selectedIds.size > 0 ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-accent/10 px-3.5 py-2 text-xs">
            <span className="font-mono font-medium text-foreground">
              {selectedIds.size} invoice{selectedIds.size > 1 ? "s" : ""}{" "}
              selected
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <GlassButton
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("csv")}
                className="inline-flex items-center gap-1 rounded-full border border-border bg-card/90 px-2.5 py-1 font-mono text-xs font-medium text-foreground hover:bg-card disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5 text-muted-foreground" />
                CSV
              </GlassButton>
              <GlassButton
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("json")}
                className="inline-flex items-center gap-1 rounded-full border border-border bg-card/90 px-2.5 py-1 font-mono text-xs font-medium text-foreground hover:bg-card disabled:opacity-50"
              >
                <Download className="h-3.5 w-3.5 text-muted-foreground" />
                JSON
              </GlassButton>
              <GlassButton
                type="button"
                disabled={exporting}
                onClick={() => void handleExportSelected("html")}
                className="inline-flex items-center gap-1 rounded-full action-primary px-3 py-1 font-mono text-xs font-medium disabled:opacity-50 text-white"
              >
                <Download className="h-3.5 w-3.5" />
                HTML Report
              </GlassButton>
            </div>
          </div>
        ) : null}
      </div>

      {errorMsg ? <AlertBanner variant="error">{errorMsg}</AlertBanner> : null}
      {noticeMsg ? (
        <AlertBanner variant="success">{noticeMsg}</AlertBanner>
      ) : null}

      {/* Ledger Table */}
      <div className="glass-surface overflow-hidden rounded-2xl border border-border">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-muted/40 text-left font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="w-10 px-3 py-3">
                  <input
                    type="checkbox"
                    checked={
                      items.length > 0 && selectedIds.size === items.length
                    }
                    onChange={toggleAllVisible}
                    aria-label="Select all visible invoices"
                    className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                  />
                </th>
                <th className="px-3 py-3">Vendor / Document</th>
                <th className="px-3 py-3">Receipt #</th>
                <th className="px-3 py-3">Date</th>
                <th className="px-3 py-3 text-right">Total</th>
                <th className="px-3 py-3">Math</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Extractor</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {loading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx}>
                    <td colSpan={9} className="px-4 py-4">
                      <div className="h-5 animate-pulse rounded bg-muted/60" />
                    </td>
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="px-4 py-12 text-center text-sm text-muted-foreground"
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
                        "transition-colors hover:bg-muted/30",
                        selectedIds.has(inv.id) &&
                          "bg-accent/10 hover:bg-accent/15",
                      )}
                    >
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(inv.id)}
                          onChange={() => toggleOne(inv.id)}
                          aria-label={`Select ${inv.vendor || inv.filename}`}
                          className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                        />
                      </td>
                      <td className="max-w-[230px] px-3 py-3">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0">
                            <Link
                              href={`/invoices/${inv.id}`}
                              className="block truncate font-medium text-foreground hover:text-accent transition-colors"
                            >
                              {inv.vendor || "Unknown Vendor"}
                            </Link>
                            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 font-mono text-xs text-muted-foreground">
                              <span className="max-w-[165px] truncate">
                                {inv.filename}
                              </span>
                              <span>· {inv.page_count}p</span>
                              {inv.duplicate_of_id ? (
                                <Link
                                  href={`/invoices/${inv.duplicate_of_id}`}
                                  title="Duplicate detected — view original"
                                  className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-amber-700 dark:text-amber-300 ring-1 ring-amber-500/25 hover:bg-amber-500/25"
                                >
                                  <Copy className="h-2.5 w-2.5" />
                                  Duplicate
                                </Link>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-muted-foreground">
                        {inv.receipt_number || "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-muted-foreground">
                        {inv.date || "—"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-right font-mono font-semibold text-foreground">
                        {formatCurrency(inv.total_amount, inv.currency)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3">
                        {!mathChecked ? (
                          <span className="font-mono text-xs text-muted-foreground">
                            —
                          </span>
                        ) : mathOk ? (
                          <span
                            className="inline-flex items-center gap-1 font-mono text-xs font-medium text-emerald-600 dark:text-emerald-400"
                            title="Line items & totals reconcile"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            OK
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 font-mono text-xs font-medium text-amber-600 dark:text-amber-400"
                            title="Discrepancy detected in subtotal/totals"
                          >
                            <AlertTriangle className="h-3.5 w-3.5" />
                            Check
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-3">
                        <ExtractorBadge extractor={inv.extractor_used} compact />
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <Link
                            href={`/invoices/${inv.id}`}
                            className="inline-flex items-center gap-1 rounded-full border border-border bg-card/80 px-2.5 py-1 font-mono text-xs font-medium text-foreground hover:border-accent/40 hover:bg-card transition-colors"
                          >
                            Review
                            <ExternalLink className="h-3 w-3 text-muted-foreground" />
                          </Link>
                          <GlassButton
                            type="button"
                            onClick={() => setDeleteTarget(inv)}
                            className="rounded-full p-1.5 text-muted-foreground hover:bg-rose-500/15 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
                            aria-label={`Delete ${inv.vendor || inv.filename}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </GlassButton>
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
        <div className="flex flex-col items-center justify-between gap-3 border-t border-border bg-muted/20 px-4 py-3 font-mono text-xs text-muted-foreground sm:flex-row">
          <span>
            Showing <span className="font-semibold text-foreground">{startRow}</span>–
            <span className="font-semibold text-foreground">{endRow}</span> of{" "}
            <span className="font-semibold text-foreground">{total}</span> invoices
          </span>
          <div className="flex items-center gap-2">
            <GlassButton
              type="button"
              disabled={offset === 0 || loading}
              onClick={() => {
                setLoading(true);
                setOffset((prev) => Math.max(0, prev - PAGE_SIZE));
              }}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-card/80 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-card disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </GlassButton>
            <GlassButton
              type="button"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => {
                setLoading(true);
                setOffset((prev) => prev + PAGE_SIZE);
              }}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-card/80 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-card disabled:opacity-40 transition-colors"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </GlassButton>
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
