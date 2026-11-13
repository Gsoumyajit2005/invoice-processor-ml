"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Download, Loader2, Save, ShieldCheck, Trash2 } from "lucide-react";
import {
  ApiError,
  deleteInvoice,
  downloadBulkReport,
  getInvoice,
  patchInvoice,
} from "@/lib/api-client";
import { formatCurrency, formatLatency } from "@/lib/format";
import type { InvoiceDetail, InvoicePatchPayload } from "@/lib/types";
import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import { DocumentOverlayViewer } from "@/components/DocumentOverlayViewer";
import { InvoiceReviewForm } from "@/components/InvoiceReviewForm";
import {
  AlertBanner,
  ConfirmModal,
  StatusBadge,
} from "@/components/ui";

export default function InvoiceDetailReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const invoiceId = typeof params?.id === "string" ? params.id : "";

  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activePage, setActivePage] = useState(1);
  const [activeTargetKey, setActiveTargetKey] = useState<string | null>(null);
  const [focusRequestCounter, setFocusRequestCounter] = useState(0);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const formSubmitRef = useRef<((markVerified: boolean) => Promise<void>) | null>(null);

  const linkedAreasOnPage = useMemo(() => {
    if (!invoice) return 0;
    let count = 0;
    for (const entry of Object.values(invoice.provenance ?? {})) {
      if (entry?.bbox && entry.bbox.page === activePage) count++;
    }
    invoice.line_items.forEach((item) => {
      if (item.bbox && item.bbox.page === activePage) count++;
    });
    return count;
  }, [invoice, activePage]);

  const targetLabel = useMemo(() => {
    if (!activeTargetKey) return null;
    const cleanKey = activeTargetKey.startsWith("field:") ? activeTargetKey.replace("field:", "") : activeTargetKey;
    const labels: Record<string, string> = {
      vendor: "Vendor",
      vendor_address: "Vendor Address",
      receipt_number: "Receipt #",
      date: "Issue Date",
      due_date: "Due Date",
      currency: "Currency",
      subtotal: "Subtotal",
      tax_amount: "Tax Amount",
      discount_amount: "Discount",
      total_amount: "Total Amount",
      bill_to: "Bill To",
    };
    if (labels[cleanKey]) return labels[cleanKey];
    if (cleanKey.startsWith("item:")) {
      const idx = parseInt(cleanKey.replace("item:", ""), 10);
      return `Item #${idx + 1}`;
    }
    return cleanKey;
  }, [activeTargetKey]);

  useEffect(() => {
    if (!invoiceId) return;
    let active = true;
    getInvoice(invoiceId)
      .then((data) => {
        if (!active) return;
        setInvoice(data);
        setActivePage(1);
        setLoadError(null);
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(
          error instanceof ApiError
            ? error.detail
            : "Unable to load invoice record.",
        );
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [invoiceId]);

  const handleFormFocusTarget = (
    targetKey: string | null,
    bboxPage?: number,
  ) => {
    setActiveTargetKey(targetKey);
    if (
      bboxPage &&
      invoice &&
      bboxPage >= 1 &&
      bboxPage <= invoice.page_count &&
      bboxPage !== activePage
    ) {
      setActivePage(bboxPage);
    }
  };

  const handleOverlaySelect = (targetKey: string) => {
    setActiveTargetKey(targetKey);
    setFocusRequestCounter((c) => c + 1);
  };

  const handleSave = async (
    payload: InvoicePatchPayload,
    markVerified: boolean,
  ) => {
    if (!invoice) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      const updated = await patchInvoice(invoice.id, payload);
      setInvoice(updated);
      setSaveSuccess(
        markVerified
          ? "Changes saved and invoice marked Verified."
          : "Draft changes saved.",
      );
    } catch (error) {
      setSaveError(
        error instanceof ApiError
          ? error.detail
          : "Failed to save invoice changes.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!invoice) return;
    setDeleting(true);
    setSaveError(null);
    try {
      await deleteInvoice(invoice.id);
      router.push("/invoices");
    } catch (error) {
      setDeleting(false);
      setDeleteModalOpen(false);
      setSaveError(
        error instanceof ApiError
          ? error.detail
          : "Failed to delete invoice.",
      );
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center gap-2.5 text-sm text-stone-600 dark:text-stone-400">
        <Loader2 className="h-5 w-5 animate-spin text-stone-600 dark:text-stone-400" />
        Loading HITL Review Studio...
      </div>
    );
  }

  if (loadError || !invoice) {
    return (
      <div className="space-y-4">
        <Link
          href="/invoices"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Ledger
        </Link>
        <AlertBanner variant="error" title="Could not open invoice">
          {loadError || "Invoice not found."}
        </AlertBanner>
      </div>
    );
  }

  return (
    <div className="review-page relative">
      {/* Studio Ambient Illumination Backdrop */}
      <div className="review-ambient-canvas" aria-hidden="true">
        <div className="review-ambient-glow-left" />
        <div className="review-ambient-glow-right" />
      </div>

      {/* Breadcrumb & Summary Header */}
      <div className="review-page-heading mb-6 pb-4 border-b border-border/60">
        <div className="min-w-0">
          <Link
            href="/invoices"
            className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            BACK TO INVOICE LEDGER
          </Link>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="review-page-title font-display text-3xl sm:text-4xl font-semibold tracking-tight text-foreground">
              {invoice.document_type === "receipt" ? "Review receipt" : invoice.document_type === "credit_note" ? "Review credit note" : "Review invoice"}
            </h1>
            <StatusBadge status={invoice.status} />
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {invoice.vendor || invoice.filename} · {invoice.receipt_number || "No reference"} · {invoice.page_count} page
            {invoice.page_count > 1 ? "s" : ""} ·{" "}
            {formatLatency(invoice.extraction_latency_ms)}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-4">
          <div className="text-right">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Document Total
            </span>
            <p className="tabular-nums font-display text-2xl font-semibold text-foreground">
              {formatCurrency(invoice.total_amount, invoice.currency)}
            </p>
          </div>
          <GlassButton
            type="button"
            onClick={() =>
              void downloadBulkReport({
                invoice_ids: [invoice.id],
                format: "json",
              })
            }
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3.5 py-2 font-mono text-xs font-medium text-foreground hover:bg-card hover:border-accent/40 transition-colors shadow-xs"
            title="Download single-invoice JSON"
          >
            <Download className="h-3.5 w-3.5 text-muted-foreground" />
            JSON
          </GlassButton>
        </div>
      </div>

      {/* Split-Screen HITL Studio */}
      <div className="review-workspace">
        {/* Left: Sticky Document Viewer + Bounding Box Overlay */}
        <div className="review-viewer-pane">
          <DocumentOverlayViewer
            filename={invoice.filename}
            pageImageUrls={invoice.page_image_urls}
            activePage={activePage}
            onPageChange={setActivePage}
            provenance={invoice.provenance}
            lineItems={invoice.line_items}
            activeTargetKey={activeTargetKey}
            onHoverTarget={(key) => setActiveTargetKey(key)}
            onSelectTarget={handleOverlaySelect}
          />
        </div>

        {/* Right: Editable Fields, Line Items, Live Reconciliation */}
        <div className="review-editor-pane">
          <InvoiceReviewForm
            key={`${invoice.id}:${invoice.updated_at}`}
            invoice={invoice}
            activeTargetKey={activeTargetKey}
            focusRequestCounter={focusRequestCounter}
            saving={saving}
            saveError={saveError}
            saveSuccess={saveSuccess}
            onFocusTarget={handleFormFocusTarget}
            onSave={handleSave}
            onRequestDelete={() => setDeleteModalOpen(true)}
            onBindSubmit={(fn) => {
              formSubmitRef.current = fn;
            }}
          />
        </div>
      </div>

      {/* Master Studio Floating Dock */}
      <div className="review-dock-wrapper pointer-events-auto">
        <GlassSurface material="chrome" radius={999} className="review-studio-dock">
          {/* Left: Active Grounding Target Pill */}
          <div className="flex items-center gap-1.5">
            {activeTargetKey ? (
              <button
                type="button"
                onClick={() => setFocusRequestCounter((c) => c + 1)}
                className="dock-target-pill flex items-center gap-1.5 rounded-full bg-accent/15 px-2.5 py-1 font-mono text-xs text-foreground hover:bg-accent/25 transition-colors cursor-pointer"
                title="Click to center on document and focus field"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse shrink-0" />
                <span className="text-muted-foreground uppercase text-[10px] tracking-wider hidden sm:inline">Target:</span>
                <span className="font-semibold truncate max-w-[130px] sm:max-w-[170px]">{targetLabel}</span>
                <span className="text-muted-foreground text-[10px]">p.{activePage}</span>
              </button>
            ) : (
              <div className="dock-target-pill flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-xs text-muted-foreground">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="truncate max-w-[170px] sm:max-w-none">
                  <span className="hidden sm:inline">{linkedAreasOnPage} linked targets · p.{activePage}</span>
                  <span className="sm:hidden">{linkedAreasOnPage} targets</span>
                </span>
              </div>
            )}
          </div>

          <div className="h-4 w-px bg-border/80 mx-1 hidden sm:block shrink-0" />

          {/* Right: Studio Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <GlassButton
              type="button"
              disabled={saving}
              onClick={() => setDeleteModalOpen(true)}
              tone="danger"
              className="rounded-full p-2 sm:px-3 sm:py-1.5 text-xs font-mono"
              title="Delete invoice"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Delete</span>
            </GlassButton>

            <GlassButton
              type="button"
              disabled={saving}
              onClick={() => void formSubmitRef.current?.(false)}
              className="rounded-full px-2.5 sm:px-3.5 py-1.5 text-xs font-mono font-medium text-foreground hover:border-accent/40"
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              <span className="hidden sm:inline">Save Draft</span>
              <span className="sm:hidden">Draft</span>
            </GlassButton>

            <GlassButton
              type="button"
              disabled={saving}
              onClick={() => void formSubmitRef.current?.(true)}
              tone="primary"
              className="rounded-full px-3 sm:px-4 py-1.5 text-xs font-mono font-semibold"
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">Save &amp; Verify</span>
              <span className="sm:hidden">Verify</span>
            </GlassButton>
          </div>
        </GlassSurface>
      </div>

      <ConfirmModal
        open={deleteModalOpen}
        title="Delete invoice permanently?"
        description={`This will permanently remove "${invoice.vendor || invoice.filename}" and its rendered page images.`}
        confirmLabel="Delete Invoice"
        busy={deleting}
        onCancel={() => !deleting && setDeleteModalOpen(false)}
        onConfirm={() => void handleDeleteConfirm()}
      />
    </div>
  );
}
