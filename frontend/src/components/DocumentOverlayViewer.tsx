"use client";

import { useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Loader2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { cn } from "@/lib/format";
import type { BoundingBox, FieldProvenance, LineItem } from "@/lib/types";

export interface OverlayBoxItem {
  key: string;
  label: string;
  bbox: BoundingBox;
  kind: "field" | "item";
  source?: FieldProvenance["source"];
}

const FIELD_LABELS: Record<string, string> = {
  vendor: "Vendor",
  vendor_address: "Vendor Address",
  receipt_number: "Document #",
  date: "Issue Date",
  due_date: "Due Date",
  currency: "Currency",
  subtotal: "Subtotal",
  tax_amount: "Tax",
  discount_amount: "Discount",
  total_amount: "Total",
  bill_to: "Bill To",
};

const ZOOM_LEVELS = [
  { label: "Fit", scale: 1 },
  { label: "125%", scale: 1.25 },
  { label: "150%", scale: 1.5 },
  { label: "200%", scale: 2 },
] as const;

export function DocumentOverlayViewer({
  filename,
  pageImageUrls,
  activePage,
  onPageChange,
  provenance,
  lineItems,
  activeTargetKey,
  onHoverTarget,
  onSelectTarget,
}: {
  filename: string;
  pageImageUrls: string[];
  activePage: number;
  onPageChange: (page: number) => void;
  provenance: Record<string, FieldProvenance>;
  lineItems: LineItem[];
  activeTargetKey: string | null;
  onHoverTarget: (key: string | null) => void;
  onSelectTarget: (key: string) => void;
}) {
  const [showBoxes, setShowBoxes] = useState(true);
  const [zoomIndex, setZoomIndex] = useState(0);
  const [imageLoadedUrl, setImageLoadedUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);

  const pageCount = Math.max(1, pageImageUrls.length);
  const currentUrl = pageImageUrls[activePage - 1] ?? null;
  const zoom = ZOOM_LEVELS[zoomIndex];

  const boxesOnPage = useMemo(() => {
    const boxes: OverlayBoxItem[] = [];
    for (const [fieldKey, entry] of Object.entries(provenance ?? {})) {
      if (entry?.bbox && entry.bbox.page === activePage) {
        boxes.push({
          key: `field:${fieldKey}`,
          label: FIELD_LABELS[fieldKey] ?? fieldKey,
          bbox: entry.bbox,
          kind: "field",
          source: entry.source,
        });
      }
    }
    lineItems.forEach((item, index) => {
      if (item.bbox && item.bbox.page === activePage) {
        boxes.push({
          key: `item:${index}`,
          label: `Item #${index + 1}: ${item.description.slice(0, 28) || "Line"}`,
          bbox: item.bbox,
          kind: "item",
        });
      }
    });
    return boxes;
  }, [provenance, lineItems, activePage]);

  const activeBox =
    boxesOnPage.find((b) => b.key === activeTargetKey) ?? null;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled={activePage <= 1}
            onClick={() => onPageChange(activePage - 1)}
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="tabular-nums px-1.5 font-medium text-slate-700">
            Page {activePage} / {pageCount}
          </span>
          <button
            type="button"
            disabled={activePage >= pageCount}
            onClick={() => onPageChange(activePage + 1)}
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>

          {pageCount > 1 ? (
            <div className="ml-1 hidden items-center gap-1 sm:flex">
              {pageImageUrls.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onPageChange(idx + 1)}
                  className={cn(
                    "h-6 min-w-6 rounded px-1.5 text-[11px] font-medium transition",
                    activePage === idx + 1
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100",
                  )}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowBoxes((prev) => !prev)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-medium transition",
              showBoxes
                ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
            )}
          >
            {showBoxes ? (
              <Eye className="h-3.5 w-3.5" />
            ) : (
              <EyeOff className="h-3.5 w-3.5" />
            )}
            <span>Boxes ({boxesOnPage.length})</span>
          </button>

          <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white">
            <button
              type="button"
              disabled={zoomIndex === 0}
              onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}
              className="p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              aria-label="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="tabular-nums min-w-[44px] text-center font-medium text-slate-700">
              {zoom.label}
            </span>
            <button
              type="button"
              disabled={zoomIndex === ZOOM_LEVELS.length - 1}
              onClick={() =>
                setZoomIndex((z) => Math.min(ZOOM_LEVELS.length - 1, z + 1))
              }
              className="p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              aria-label="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Document Canvas */}
      <div className="relative flex-1 overflow-auto bg-slate-100/90 p-4">
        {!currentUrl ? (
          <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-sm text-slate-500">
            No rendered document page image available.
          </div>
        ) : imageError ? (
          <div className="flex h-80 flex-col items-center justify-center gap-2 rounded-xl border border-rose-200 bg-rose-50 text-sm text-rose-700">
            <p>Unable to load document page image.</p>
            <button
              type="button"
              onClick={() => setImageError(false)}
              className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-rose-800 ring-1 ring-rose-200 hover:bg-rose-100"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="flex min-h-full items-start justify-center">
            <div
              className="relative inline-block overflow-hidden rounded-lg border border-slate-300 bg-white shadow-md"
              style={{
                width: `${zoom.scale * 100}%`,
                maxWidth: zoom.scale === 1 ? "100%" : "none",
              }}
            >
              {imageLoadedUrl !== currentUrl ? (
                <div className="flex h-64 items-center justify-center gap-2 text-xs text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                  Loading page {activePage}...
                </div>
              ) : null}

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={currentUrl}
                alt={`${filename} page ${activePage}`}
                onLoad={() => {
                  setImageLoadedUrl(currentUrl);
                  setImageError(false);
                }}
                onError={() => {
                  setImageError(true);
                }}
                className={cn(
                  "block h-auto w-full select-none",
                  imageLoadedUrl !== currentUrl && "hidden",
                )}
              />

              {showBoxes && imageLoadedUrl === currentUrl ? (
                <>
                  <svg
                    viewBox="0 0 1000 1000"
                    preserveAspectRatio="none"
                    className="pointer-events-none absolute inset-0 h-full w-full"
                    aria-label="OCR bounding box overlay"
                  >
                    {boxesOnPage.map((box) => {
                      const isActive = activeTargetKey === box.key;
                      const width = Math.max(4, box.bbox.x2 - box.bbox.x1);
                      const height = Math.max(4, box.bbox.y2 - box.bbox.y1);
                      const baseStroke =
                        box.kind === "field" ? "#059669" : "#0284c7";
                      const stroke = isActive ? "#4f46e5" : baseStroke;
                      const fill = isActive
                        ? "rgba(79, 70, 229, 0.20)"
                        : box.kind === "field"
                          ? "rgba(16, 185, 129, 0.08)"
                          : "rgba(14, 165, 233, 0.08)";

                      return (
                        <rect
                          key={box.key}
                          x={box.bbox.x1}
                          y={box.bbox.y1}
                          width={width}
                          height={height}
                          rx={2}
                          fill={fill}
                          stroke={stroke}
                          strokeWidth={isActive ? 3 : 1.75}
                          vectorEffect="non-scaling-stroke"
                          className="pointer-events-auto cursor-pointer transition-colors"
                          onMouseEnter={() => onHoverTarget(box.key)}
                          onMouseLeave={() => onHoverTarget(null)}
                          onClick={() => onSelectTarget(box.key)}
                        >
                          <title>{box.label}</title>
                        </rect>
                      );
                    })}
                  </svg>

                  {activeBox ? (
                    <div
                      className="pointer-events-none absolute z-10 -translate-y-full rounded-md bg-indigo-600 px-2 py-0.5 text-[11px] font-semibold text-white shadow-sm"
                      style={{
                        left: `${Math.min(82, Math.max(0, activeBox.bbox.x1 / 10))}%`,
                        top: `${Math.max(4, activeBox.bbox.y1 / 10)}%`,
                      }}
                    >
                      {activeBox.label}
                    </div>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* Footer Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-slate-50 px-3.5 py-2 text-[11px] text-slate-600">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-xs border border-emerald-600 bg-emerald-500/20" />
            Header Field
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-xs border border-sky-600 bg-sky-500/20" />
            Line Item
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-xs border-2 border-indigo-600 bg-indigo-500/25" />
            Active Highlight
          </span>
        </div>
        <span className="text-slate-400">
          Hover or click any box to jump to field
        </span>
      </div>
    </div>
  );
}
