"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
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
    <div className="review-page">
      {/* Breadcrumb & Summary Header */}
      <div className="review-page-heading">
        <div className="min-w-0">
          <Link
            href="/invoices"
            className="inline-flex items-center gap-1 text-xs font-medium text-stone-500 hover:text-stone-600 dark:text-stone-400 dark:hover:text-stone-400"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Invoice Ledger
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-2.5">
            <h1 className="review-page-title">
              {invoice.document_type === "receipt" ? "Review receipt" : invoice.document_type === "credit_note" ? "Review credit note" : "Review invoice"}
            </h1>
            <StatusBadge status={invoice.status} />

          </div>
          <p className="mt-0.5 text-xs text-stone-500 dark:text-stone-400">
            {invoice.vendor || invoice.filename} · {invoice.receipt_number || "No reference"} · {invoice.page_count} page
            {invoice.page_count > 1 ? "s" : ""} ·{" "}
            {formatLatency(invoice.extraction_latency_ms)}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <div className="text-right">
            <span className="text-[11px] font-medium uppercase tracking-wider text-stone-400 dark:text-stone-500">
              Document Total
            </span>
            <p className="tabular-nums text-lg font-semibold text-stone-900 dark:text-stone-100">
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
            className="inline-flex items-center gap-1.5 rounded-xl border border-stone-200/80 bg-white/75 px-3 py-2 text-xs font-medium text-stone-700 backdrop-blur-md hover:bg-white dark:border-white/12 dark:bg-white/8 dark:text-stone-200 dark:hover:bg-white/14"
            title="Download single-invoice JSON"
          >
            <Download className="h-3.5 w-3.5" />
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
          />
        </div>
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
