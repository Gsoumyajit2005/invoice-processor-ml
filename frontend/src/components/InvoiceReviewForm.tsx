"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Code2,
  Copy,
  Loader2,
  MapPin,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  cn,
  computeReconciliation,
  formatCurrency,
  formatDateTime,
  formatLatency,
} from "@/lib/format";
import type {
  BoundingBox,
  DocumentType,
  FieldProvenance,
  InvoiceDetail,
  InvoicePatchPayload,
  LineItem,
} from "@/lib/types";
import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import { OcrInspectorControl } from "@/components/liquid-glass/OcrInspectorControl";
import { AlertBanner } from "@/components/ui";

interface EditableLineItem {
  localKey: string;
  description: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  bbox: BoundingBox | null;
}

export interface ReviewFormState {
  document_type: DocumentType;
  vendor: string;
  vendor_address: string;
  receipt_number: string;
  date: string;
  due_date: string;
  currency: string;
  bill_to: string;
  subtotal: string;
  tax_amount: string;
  discount_amount: string;
  total_amount: string;
  line_items: EditableLineItem[];
}

function toStr(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function buildInitialState(invoice: InvoiceDetail): ReviewFormState {
  return {
    document_type: invoice.document_type ?? "invoice",
    vendor: toStr(invoice.vendor),
    vendor_address: toStr(invoice.vendor_address),
    receipt_number: toStr(invoice.receipt_number),
    date: toStr(invoice.date),
    due_date: toStr(invoice.due_date),
    currency: toStr(invoice.currency),
    bill_to: toStr(invoice.bill_to),
    subtotal: toStr(invoice.subtotal),
    tax_amount: toStr(invoice.tax_amount),
    discount_amount: toStr(invoice.discount_amount),
    total_amount: toStr(invoice.total_amount),
    line_items: (invoice.line_items ?? []).map((item, idx) => ({
      localKey: item.id ?? `row-${idx}`,
      description: item.description ?? "",
      quantity: toStr(item.quantity),
      unit_price: toStr(item.unit_price),
      total_price: toStr(item.total_price),
      bbox: item.bbox ?? null,
    })),
  };
}

function parseOptionalNumber(
  raw: string,
): { ok: true; value: number | null } | { ok: false } {
  const trimmed = raw.trim();
  if (!trimmed) return { ok: true, value: null };
  const cleaned = trimmed.replace(/,/g, "");
  const parsed = Number(cleaned);
  if (!Number.isFinite(parsed)) return { ok: false };
  return { ok: true, value: parsed };
}

function cleanOptionalText(raw: string): string | null {
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function GroundedTextField({
  fieldKey,
  label,
  value,
  placeholder,
  maxLength,
  inputMode,
  inputClassName,
  containerClassName,
  provenance,
  activeTargetKey,
  onChange,
  onFocusTarget,
  showPageHint,
}: {
  fieldKey: string;
  label: string;
  value: string;
  placeholder?: string;
  maxLength?: number;
  inputMode?: "text" | "decimal";
  inputClassName?: string;
  containerClassName?: string;
  provenance?: FieldProvenance;
  activeTargetKey: string | null;
  onChange: (value: string) => void;
  onFocusTarget: (targetKey: string | null, bboxPage?: number) => void;
  showPageHint?: boolean;
}) {
  const inputId = `review-field-${fieldKey}`;
  const targetKey = `field:${fieldKey}`;
  const isHighlighted = activeTargetKey === targetKey;

  return (
    <div
      className={cn(
        "grounded-field",
        isHighlighted &&
          "bg-stone-50/70 ring-1 ring-stone-300 dark:bg-stone-950/50 dark:ring-stone-700",
        containerClassName,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <label htmlFor={inputId} className="text-xs font-medium text-stone-700 dark:text-stone-300">
          {label}
        </label>
        <div className="review-field-meta">
          {provenance ? <OcrInspectorControl label={label} provenance={provenance} onLocate={() => onFocusTarget(targetKey, provenance.bbox?.page)} /> : null}
          {provenance ? <span className="source-kind">{provenance.source === "ocr_matched" ? "OCR" : provenance.source === "user_edited" ? "Edited" : "VLM"}{showPageHint && provenance.bbox ? ` · p.${provenance.bbox.page}` : ""}</span> : null}
        </div>
      </div>
      <input
        id={inputId}
        type="text"
        inputMode={inputMode}
        maxLength={maxLength}
        value={value}
        data-ground-key={targetKey}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onMouseEnter={() => onFocusTarget(targetKey, provenance?.bbox?.page)}
        onFocus={() => onFocusTarget(targetKey, provenance?.bbox?.page)}
        onMouseLeave={() => onFocusTarget(null)}
        className={cn(
          "mt-1 w-full rounded-lg border border-stone-200/80 bg-white px-3 py-1.5 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-white/12 dark:bg-stone-950 dark:text-stone-100 dark:placeholder:text-stone-500",
          inputClassName,
        )}
      />
    </div>
  );
}

export function InvoiceReviewForm({
  invoice,
  activeTargetKey,
  focusRequestCounter,
  saving,
  saveError,
  saveSuccess,
  onFocusTarget,
  onSave,
  onRequestDelete,
}: {
  invoice: InvoiceDetail;
  activeTargetKey: string | null;
  focusRequestCounter: number;
  saving: boolean;
  saveError: string | null;
  saveSuccess: string | null;
  onFocusTarget: (targetKey: string | null, bboxPage?: number) => void;
  onSave: (payload: InvoicePatchPayload, markVerified: boolean) => Promise<void>;
  onRequestDelete: () => void;
}) {
  const [form, setForm] = useState<ReviewFormState>(() =>
    buildInitialState(invoice),
  );
  const [dirty, setDirty] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showRawOcr, setShowRawOcr] = useState(false);

  const rowSeqRef = useRef(1000);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!focusRequestCounter || !activeTargetKey) return;
    const container = containerRef.current;
    if (!container) return;
    const targetNode = Array.from(
      container.querySelectorAll<HTMLElement>("[data-ground-key]"),
    ).find((el) => el.dataset.groundKey === activeTargetKey);

    if (targetNode) {
      targetNode.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "center" });
      if (targetNode.tagName === "INPUT") {
        targetNode.focus();
      } else {
        targetNode.querySelector<HTMLInputElement>("input")?.focus();
      }
    }
  }, [focusRequestCounter, activeTargetKey]);

  const parsedLineItems: LineItem[] = useMemo(() => {
    return form.line_items.map((row) => {
      const q = parseOptionalNumber(row.quantity);
      const u = parseOptionalNumber(row.unit_price);
      const t = parseOptionalNumber(row.total_price);
      return {
        description: row.description,
        quantity: q.ok ? q.value : null,
        unit_price: u.ok ? u.value : null,
        total_price: t.ok ? t.value : null,
        bbox: row.bbox,
      };
    });
  }, [form.line_items]);

  const reconciliation = useMemo(() => {
    const sub = parseOptionalNumber(form.subtotal);
    const tax = parseOptionalNumber(form.tax_amount);
    const disc = parseOptionalNumber(form.discount_amount);
    const tot = parseOptionalNumber(form.total_amount);
    return computeReconciliation(
      parsedLineItems,
      sub.ok ? sub.value : null,
      tax.ok ? tax.value : null,
      disc.ok ? disc.value : null,
      tot.ok ? tot.value : null,
    );
  }, [
    parsedLineItems,
    form.subtotal,
    form.tax_amount,
    form.discount_amount,
    form.total_amount,
  ]);

  const updateScalar = <K extends keyof ReviewFormState>(
    key: K,
    value: ReviewFormState[K],
  ) => {
    setDirty(true);
    setValidationError(null);
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const updateLineItem = (
    index: number,
    patch: Partial<EditableLineItem>,
  ) => {
    setDirty(true);
    setValidationError(null);
    setForm((prev) => ({
      ...prev,
      line_items: prev.line_items.map((item, idx) =>
        idx === index ? { ...item, ...patch } : item,
      ),
    }));
  };

  const addLineItem = () => {
    rowSeqRef.current += 1;
    setDirty(true);
    setForm((prev) => ({
      ...prev,
      line_items: [
        ...prev.line_items,
        {
          localKey: `new-${rowSeqRef.current}`,
          description: "",
          quantity: "1",
          unit_price: "",
          total_price: "",
          bbox: null,
        },
      ],
    }));
  };

  const removeLineItem = (index: number) => {
    setDirty(true);
    setForm((prev) => ({
      ...prev,
      line_items: prev.line_items.filter((_, idx) => idx !== index),
    }));
  };

  const handleSubmit = async (markVerified: boolean) => {
    setValidationError(null);

    const sub = parseOptionalNumber(form.subtotal);
    const tax = parseOptionalNumber(form.tax_amount);
    const disc = parseOptionalNumber(form.discount_amount);
    const tot = parseOptionalNumber(form.total_amount);

    if (!sub.ok || !tax.ok || !disc.ok || !tot.ok) {
      setValidationError(
        "Subtotal, Tax, Discount, and Total must be valid numbers or left blank.",
      );
      return;
    }

    const serializedItems: NonNullable<InvoicePatchPayload["line_items"]> = [];
    for (let idx = 0; idx < form.line_items.length; idx += 1) {
      const row = form.line_items[idx];
      const desc = row.description.trim();
      const q = parseOptionalNumber(row.quantity);
      const u = parseOptionalNumber(row.unit_price);
      const t = parseOptionalNumber(row.total_price);

      if (!q.ok || !u.ok || !t.ok) {
        setValidationError(
          `Line item #${idx + 1} has an invalid numeric value.`,
        );
        return;
      }
      if (!desc) {
        if (q.value !== null || u.value !== null || t.value !== null) {
          setValidationError(
            `Line item #${idx + 1} needs a description (or remove the row).`,
          );
          return;
        }
        continue;
      }

      serializedItems.push({
        description: desc,
        quantity: q.value,
        unit_price: u.value,
        total_price: t.value,
        bbox: row.bbox,
      });
    }

    const payload: InvoicePatchPayload = {
      document_type: form.document_type,
      vendor: cleanOptionalText(form.vendor),
      vendor_address: cleanOptionalText(form.vendor_address),
      receipt_number: cleanOptionalText(form.receipt_number),
      date: cleanOptionalText(form.date),
      due_date: cleanOptionalText(form.due_date),
      currency: cleanOptionalText(form.currency)?.toUpperCase() ?? null,
      bill_to: cleanOptionalText(form.bill_to),
      subtotal: sub.value,
      tax_amount: tax.value,
      discount_amount: disc.value,
      total_amount: tot.value,
      line_items: serializedItems,
      mark_verified: markVerified,
    };

    await onSave(payload, markVerified);
    setDirty(false);
  };

  const currencyCode = cleanOptionalText(form.currency) ?? invoice.currency;

  return (
    <div ref={containerRef} className="review-form">
        <div className="review-details-heading"><h2>Document details</h2><span>{Object.values(invoice.provenance ?? {}).filter(entry => entry.bbox).length + invoice.line_items.filter(item => item.bbox).length} source-linked values</span></div>
        <p className="source-help">Focus a field or use its source control to inspect the original evidence.</p>

      {(invoice.duplicate_of_id || invoice.validation_warnings.length > 0) ? <details className="review-notices"><summary>Review notes{invoice.validation_warnings.length > 0 ? ` (${invoice.validation_warnings.length} warnings)` : " · possible duplicate"}</summary>
      {/* Duplicate & Validation Banners */}
      {invoice.duplicate_of_id ? (
        <AlertBanner variant="warning" title="Duplicate Document Notice">
          <div className="flex flex-wrap items-center gap-1.5">
            <Copy className="h-3.5 w-3.5" />
            <span>Content or semantic signature matches another record.</span>
            <Link
              href={`/invoices/${invoice.duplicate_of_id}`}
              className="font-semibold underline"
            >
              Open original invoice →
            </Link>
          </div>
        </AlertBanner>
      ) : null}

      {invoice.validation_warnings.length > 0 ? (
        <AlertBanner variant="warning" title="Extraction Warnings">
          {invoice.validation_warnings.join(" · ")}
        </AlertBanner>
      ) : null}

      </details> : null}
      {validationError || saveError ? (
        <AlertBanner variant="error">
          {validationError || saveError}
        </AlertBanner>
      ) : null}

      {saveSuccess ? (
        <AlertBanner variant="success">{saveSuccess}</AlertBanner>
      ) : null}

      <section className="review-details">
        <h3 className="review-group-title">Identification</h3>
        <div className="review-field-grid">
          <GroundedTextField
            fieldKey="vendor"
            label="Vendor / Merchant"
            value={form.vendor}
            placeholder="Vendor name"
            containerClassName="sm:col-span-2"
            provenance={invoice.provenance?.vendor}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("vendor", val)}
            onFocusTarget={onFocusTarget}
            showPageHint
          />

<div className="review-type-field">
            <label className="block text-xs font-medium text-stone-700 dark:text-stone-300">
              Document Type
            </label>
            <select
              aria-label="Document type"
              value={form.document_type}
              onChange={(e) =>
                updateScalar("document_type", e.target.value as DocumentType)
              }
              className="lg-select w-full"
            >
              <option value="invoice">Invoice</option>
              <option value="receipt">Receipt</option>
              <option value="credit_note">Credit Note</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>

          <GroundedTextField
            fieldKey="receipt_number"
            label="Receipt / Invoice #"
            value={form.receipt_number}
            placeholder="e.g. INV-2025-001"

            provenance={invoice.provenance?.receipt_number}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("receipt_number", val)}
            onFocusTarget={onFocusTarget}
          />

          <GroundedTextField
            fieldKey="currency"
            label="Currency (ISO Code)"
            value={form.currency}
            maxLength={8}
            placeholder="USD, EUR, MYR, INR..."
            inputClassName="uppercase"
            provenance={invoice.provenance?.currency}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("currency", val)}
            onFocusTarget={onFocusTarget}
          />
        </div>
        <h3 className="review-group-title">Dates &amp; parties</h3>
        <div className="review-field-grid">
          <GroundedTextField
            fieldKey="date"
            label="Issue Date"
            value={form.date}
            placeholder="YYYY-MM-DD"
            provenance={invoice.provenance?.date}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("date", val)}
            onFocusTarget={onFocusTarget}
          />

          <GroundedTextField
            fieldKey="due_date"
            label="Due Date"
            value={form.due_date}
            placeholder="YYYY-MM-DD"
            provenance={invoice.provenance?.due_date}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("due_date", val)}
            onFocusTarget={onFocusTarget}
          />

          <GroundedTextField
            fieldKey="bill_to"
            containerClassName="sm:col-span-2"
            label="Bill To / Customer"
            value={form.bill_to}
            placeholder="Recipient / company"
            provenance={invoice.provenance?.bill_to}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("bill_to", val)}
            onFocusTarget={onFocusTarget}
          />

          <GroundedTextField
            fieldKey="vendor_address"
            label="Vendor Address"
            value={form.vendor_address}
            placeholder="Street, city, postal code"
            containerClassName="sm:col-span-2"
            provenance={invoice.provenance?.vendor_address}
            activeTargetKey={activeTargetKey}
            onChange={(val) => updateScalar("vendor_address", val)}
            onFocusTarget={onFocusTarget}
          />
        </div>
        <h3 className="review-group-title">Financial summary</h3>
        {/* Financial Amounts Row */}
        <div className="review-amount-grid">
          {(
            [
              ["subtotal", "Subtotal"],
              ["tax_amount", "Tax"],
              ["discount_amount", "Discount"],
              ["total_amount", "Total Amount"],
            ] as const
          ).map(([fieldKey, label]) => (
            <GroundedTextField
              key={fieldKey}
              fieldKey={fieldKey}
              label={label}
              value={form[fieldKey]}
              inputMode="decimal"
              placeholder="0.00"
              containerClassName={fieldKey === "total_amount" ? "amount-field amount-total" : "amount-field"}
              inputClassName={cn(
                "px-2.5 text-right tabular-nums",
                fieldKey === "total_amount" &&
                  "border-stone-300 font-semibold dark:border-stone-600",
              )}
              provenance={invoice.provenance?.[fieldKey]}
              activeTargetKey={activeTargetKey}
              onChange={(val) => updateScalar(fieldKey, val)}
              onFocusTarget={onFocusTarget}
            />
          ))}
        </div>
        <details className="reconciliation-details"><summary>{reconciliation.itemsMatchSubtotal === false || reconciliation.totalsReconcile === false ? "Reconciliation needs attention" : reconciliation.totalsReconcile === true ? "Totals balanced" : "Reconciliation details"}</summary>
      {/* Live Math Reconciliation Banner */}
      <div
        className={cn(
          "review-reconciliation rounded-2xl border p-4 text-xs",
          reconciliation.itemsMatchSubtotal === false ||
            reconciliation.totalsReconcile === false
            ? "border-amber-200/80 bg-amber-50/70 text-amber-950 dark:border-amber-400/25 dark:bg-amber-500/12 dark:text-amber-200"
            : reconciliation.totalsReconcile === true
              ? "border-emerald-200/80 bg-emerald-50/70 text-emerald-950 dark:border-emerald-400/25 dark:bg-emerald-500/12 dark:text-emerald-200"
              : "glass-surface text-stone-700 dark:text-stone-300",
        )}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-semibold">
            {reconciliation.itemsMatchSubtotal === false ||
            reconciliation.totalsReconcile === false ? (
              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            )}
            <span>Live Math Reconciliation</span>
          </div>
          {dirty ? (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-900 dark:bg-amber-900/60 dark:text-amber-200">
              Unsaved edits
            </span>
          ) : null}
        </div>

        <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="flex items-center justify-between gap-2 rounded-xl bg-white px-3 py-2 ring-1 ring-stone-200/70 dark:bg-stone-950/55 dark:ring-white/10">
            <div>
              <span className="text-stone-500 dark:text-stone-400">
                Line items sum
              </span>
              <p className="tabular-nums font-semibold text-stone-900 dark:text-stone-100">
                {reconciliation.hasLineItems
                  ? formatCurrency(reconciliation.lineItemsSum, currencyCode)
                  : "No item amounts"}
              </p>
            </div>
            {reconciliation.itemsMatchSubtotal === false &&
            reconciliation.hasLineItems ? (
              <button
                type="button"
                onClick={() =>
                  updateScalar(
                    "subtotal",
                    reconciliation.lineItemsSum.toFixed(2),
                  )
                }
                className="rounded-lg bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-900 hover:bg-amber-200 dark:bg-amber-900/60 dark:text-amber-200 dark:hover:bg-amber-900"
              >
                Apply to Subtotal
              </button>
            ) : reconciliation.itemsMatchSubtotal === true ? (
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                Matches Subtotal
              </span>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-2 rounded-xl bg-white px-3 py-2 ring-1 ring-stone-200/70 dark:bg-stone-950/55 dark:ring-white/10">
            <div>
              <span className="text-stone-500 dark:text-stone-400">
                Expected total (sub + tax − disc)
              </span>
              <p className="tabular-nums font-semibold text-stone-900 dark:text-stone-100">
                {reconciliation.expectedTotal !== null
                  ? formatCurrency(reconciliation.expectedTotal, currencyCode)
                  : "—"}
              </p>
            </div>
            {reconciliation.totalsReconcile === false &&
            reconciliation.expectedTotal !== null ? (
              <button
                type="button"
                onClick={() =>
                  updateScalar(
                    "total_amount",
                    reconciliation.expectedTotal!.toFixed(2),
                  )
                }
                className="rounded-lg bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-900 hover:bg-amber-200 dark:bg-amber-900/60 dark:text-amber-200 dark:hover:bg-amber-900"
              >
                Apply to Total
              </button>
            ) : reconciliation.totalsReconcile === true ? (
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                Balanced
              </span>
            ) : null}
          </div>
        </div>
      </div>

        </details>
      </section>

      {/* Editable Line Items Table */}
      <section className="review-items">
        <div className="flex items-center justify-between border-b border-stone-200/70 pb-3 dark:border-white/10">
          <div>
            <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100">
              Line Items ({form.line_items.length})
            </h2>
            <p className="text-[11px] text-stone-500 dark:text-stone-400">
              Hover or focus a row to locate it on the scanned page.
            </p>
          </div>
          <button
            type="button"
            onClick={addLineItem}
            className="inline-flex items-center gap-1 rounded-lg border border-stone-200/80 bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-600 hover:bg-stone-50 dark:border-white/12 dark:bg-white/8 dark:text-stone-300 dark:hover:bg-stone-500/20"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Row
          </button>
        </div>

        <details className="line-item-editor" open>
          <summary>Edit quantities, prices and source-linked rows</summary>
        <div className="review-items-table">
          <table className="min-w-full divide-y divide-stone-200 text-xs dark:divide-stone-800">
            <thead>
              <tr className="text-left font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
                <th className="py-2 pr-2">#</th>
                <th className="py-2 pr-2">Description</th>
                <th className="w-20 py-2 pr-2 text-right">Qty</th>
                <th className="w-24 py-2 pr-2 text-right">Unit Price</th>
                <th className="w-24 py-2 pr-2 text-right">Line Total</th>
                <th className="w-8 py-2 text-right" />
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 dark:divide-stone-800/80">
              {form.line_items.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="py-6 text-center text-xs text-stone-500 dark:text-stone-400"
                  >
                    No line items yet. Click &ldquo;Add Row&rdquo; to insert one.
                  </td>
                </tr>
              ) : (
                form.line_items.map((item, idx) => {
                  const targetKey = `item:${idx}`;
                  const isHighlighted = activeTargetKey === targetKey;
                  return (
                    <tr
                      key={item.localKey}
                      data-ground-key={targetKey}
                      onMouseEnter={() =>
                        onFocusTarget(targetKey, item.bbox?.page)
                      }
                      onFocus={() => onFocusTarget(targetKey, item.bbox?.page)}
                      onMouseLeave={() => onFocusTarget(null)}
                      className={cn(
                        "transition",
                        isHighlighted && "bg-stone-50/70 dark:bg-stone-950/40",
                      )}
                    >
                      <td className="py-2 pr-2 tabular-nums text-stone-400 dark:text-stone-500">
                        <div className="flex items-center gap-1">
                          <span>{idx + 1}</span>
                          {item.bbox ? (
                            <MapPin
                              className="h-3 w-3 text-stone-600 dark:text-stone-400"
                              aria-label={`Grounded on page ${item.bbox.page}`}
                            />
                          ) : null}
                        </div>
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) =>
                            updateLineItem(idx, {
                              description: e.target.value,
                            })
                          }
                          placeholder="Item description"
                          className="w-full rounded-lg border border-stone-200/80 bg-white px-2.5 py-1.5 text-xs text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-white/12 dark:bg-stone-950 dark:text-stone-100 dark:placeholder:text-stone-500"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={item.quantity}
                          onChange={(e) =>
                            updateLineItem(idx, { quantity: e.target.value })
                          }
                          placeholder="—"
                          className="w-full rounded-lg border border-stone-200/80 bg-white px-2 py-1.5 text-right tabular-nums text-xs text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-white/12 dark:bg-stone-950 dark:text-stone-100 dark:placeholder:text-stone-500"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={item.unit_price}
                          onChange={(e) =>
                            updateLineItem(idx, { unit_price: e.target.value })
                          }
                          placeholder="—"
                          className="w-full rounded-lg border border-stone-200/80 bg-white px-2 py-1.5 text-right tabular-nums text-xs text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-white/12 dark:bg-stone-950 dark:text-stone-100 dark:placeholder:text-stone-500"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={item.total_price}
                          onChange={(e) =>
                            updateLineItem(idx, {
                              total_price: e.target.value,
                            })
                          }
                          placeholder="0.00"
                          className="w-full rounded-lg border border-stone-200/80 bg-white px-2 py-1.5 text-right tabular-nums text-xs font-medium text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none dark:border-white/12 dark:bg-stone-950 dark:text-stone-100 dark:placeholder:text-stone-500"
                        />
                      </td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          onClick={() => removeLineItem(idx)}
                          className="rounded p-1 text-stone-400 hover:bg-rose-50/80 hover:text-rose-600 dark:text-stone-500 dark:hover:bg-rose-500/15 dark:hover:text-rose-400"
                          aria-label={`Remove line item ${idx + 1}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        </details>
      </section>

      {/* Collapsible Raw OCR & Audit Metadata */}
      <section className="review-additional">
        <button
          type="button"
          onClick={() => setShowRawOcr((prev) => !prev)}
          className="flex w-full items-center justify-between px-4 py-3 text-left text-xs font-semibold text-stone-700 dark:text-stone-200"
        >
          <span className="inline-flex items-center gap-2">
            <Code2 className="h-4 w-4 text-stone-500 dark:text-stone-400" />
            Audit Metadata & Raw Indra OCR Output
          </span>
          {showRawOcr ? (
            <ChevronUp className="h-4 w-4 text-stone-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-stone-400" />
          )}
        </button>

        {showRawOcr ? (
          <div className="space-y-3 border-t border-stone-200/70 px-4 py-3 text-xs dark:border-white/10">
            <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-stone-500 dark:text-stone-400">
                  Created / Updated
                </dt>
                <dd className="font-medium text-stone-800 dark:text-stone-200">
                  {formatDateTime(invoice.created_at)} · Updated{" "}
                  {formatDateTime(invoice.updated_at)}
                </dd>
              </div>
              <div>
                <dt className="text-stone-500 dark:text-stone-400">
                  Extractor Latency
                </dt>
                <dd className="font-medium text-stone-800 dark:text-stone-200">
                  {invoice.extractor_used || "—"} (
                  {formatLatency(invoice.extraction_latency_ms)})
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-stone-500 dark:text-stone-400">
                  SHA-256 Content Hash
                </dt>
                <dd className="truncate font-mono text-[11px] text-stone-700 dark:text-stone-300">
                  {invoice.file_hash}
                </dd>
              </div>
            </dl>
            <div>
              <p className="mb-1.5 font-medium text-stone-600 dark:text-stone-400">
                Normalized OCR Text
              </p>
              <pre className="glass-subtle max-h-56 overflow-auto rounded-xl border border-stone-200/70 p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-stone-700 dark:border-white/10 dark:text-stone-300">
                {invoice.raw_ocr_markdown || "No raw OCR text captured."}
              </pre>
            </div>
          </div>
        ) : null}
      </section>
      {/* Action Bar */}
      <GlassSurface material="chrome" radius={999} className="review-actions">
        <GlassButton
          type="button"
          disabled={saving}
          onClick={onRequestDelete}
          tone="danger"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </GlassButton>

        <div className="flex flex-wrap items-center gap-2.5">
          <GlassButton
            type="button"
            disabled={saving}
            onClick={() => void handleSubmit(false)}
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            Save Draft
          </GlassButton>

          <GlassButton
            type="button"
            disabled={saving}
            onClick={() => void handleSubmit(true)}
            tone="primary"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5" />
            )}
            Save & Verify
          </GlassButton>
        </div>
      </GlassSurface>

    </div>
  );
}
