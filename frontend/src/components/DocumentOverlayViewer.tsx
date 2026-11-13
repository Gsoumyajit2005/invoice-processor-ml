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
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import "@/components/liquid-glass/document-viewer.css";
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
    <div className="document-viewer">
      <div className="document-viewer-meta font-mono text-xs text-muted-foreground border-b border-border/60 pb-3 mb-2">
        <span className="truncate font-semibold text-foreground" title={filename}>{filename}</span>
        <span className="shrink-0">Page {activePage} of {pageCount} · {boxesOnPage.length} linked areas</span>
      </div>
      {/* Document Canvas */}
      <div className="document-stage">
      <div className="document-scroll" tabIndex={0} role="region" aria-label={`${filename} document canvas`}>
        {!currentUrl ? (
          <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-stone-300 bg-white text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-400">
            No rendered document page image available.
          </div>
        ) : imageError ? (
          <div className="flex h-80 flex-col items-center justify-center gap-2 rounded-xl border border-rose-200 bg-rose-50 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
            <p>Unable to load document page image.</p>
            <button
              type="button"
              onClick={() => setImageError(false)}
              className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-rose-800 ring-1 ring-rose-200 hover:bg-rose-100 dark:bg-stone-900 dark:text-rose-200 dark:ring-rose-800 dark:hover:bg-rose-950"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="flex min-h-full items-start justify-center">
            <div
              className="relative mx-auto inline-block shrink-0 overflow-hidden rounded-xl border border-border bg-white shadow-xl dark:border-white/15 dark:shadow-2xl ring-1 ring-black/5"
              style={{
                width: `${zoom.scale * 100}%`,
                maxWidth: zoom.scale === 1 ? "100%" : "none",
              }}
            >
              {imageLoadedUrl !== currentUrl ? (
                <div className="flex h-64 items-center justify-center gap-2 text-xs text-stone-500 dark:bg-stone-900 dark:text-stone-400">
                  <Loader2 className="h-4 w-4 animate-spin text-stone-600 dark:text-stone-400" />
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
                        box.kind === "field" ? "#8a6b42" : "#766252";
                      const stroke = isActive ? "var(--primary)" : baseStroke;
                      const fill = isActive
                        ? "rgba(217, 119, 87, 0.22)"
                        : box.kind === "field"
                          ? "rgba(138, 107, 66, 0.08)"
                          : "rgba(118, 98, 82, 0.08)";

                      return (
                        <rect
                          key={box.key}
                          tabIndex={0}
                          role="button"
                          aria-label={box.label}
                          onFocus={() => onHoverTarget(box.key)}
                          onBlur={() => onHoverTarget(null)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectTarget(box.key); }
                          }}
                          x={box.bbox.x1}
                          y={box.bbox.y1}
                          width={width}
                          height={height}
                          rx={3}
                          fill={fill}
                          stroke={stroke}
                          strokeWidth={isActive ? 3.5 : 1.75}
                          vectorEffect="non-scaling-stroke"
                          className={cn(
                            "pointer-events-auto cursor-pointer transition-all duration-150",
                            isActive && "filter drop-shadow-[0_0_8px_rgba(217,119,87,0.6)]"
                          )}
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
                      className="pointer-events-none absolute z-10 -translate-y-full rounded-full px-2.5 py-0.5 text-[10px] font-mono font-semibold shadow-md action-primary ring-1 ring-white/20"
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

      <div className="document-float">
      <GlassSurface material="chrome" className="document-toolbar" radius={999} role="group" aria-label="Document controls">
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            disabled={activePage <= 1}
            onClick={() => onPageChange(activePage - 1)}
            className="document-btn"
            aria-label="Previous page"
            title="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="tabular-nums px-1 font-mono text-xs text-foreground select-none shrink-0">
            <span className="hidden sm:inline">Page </span>{activePage}/{pageCount}
          </span>
          <button
            type="button"
            disabled={activePage >= pageCount}
            onClick={() => onPageChange(activePage + 1)}
            className="document-btn"
            aria-label="Next page"
            title="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>

          {pageCount > 1 ? (
            <div className="document-pages flex items-center gap-0.5">
              {pageImageUrls.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  aria-label={`Go to page ${idx + 1}`}
                  aria-current={activePage === idx + 1 ? "page" : undefined}
                  onClick={() => onPageChange(idx + 1)}
                  className={cn(
                    "document-page-btn",
                    activePage === idx + 1 && "is-active",
                  )}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="h-3.5 w-px bg-border/60 mx-0.5 shrink-0" aria-hidden="true" />

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            aria-pressed={showBoxes}
            onClick={() => setShowBoxes((prev) => !prev)}
            className={cn(
              "document-btn flex items-center gap-1.5 px-2",
              showBoxes && "document-btn-active",
            )}
            title={showBoxes ? "Hide bounding boxes" : "Show bounding boxes"}
          >
            {showBoxes ? (
              <Eye className="h-3.5 w-3.5" />
            ) : (
              <EyeOff className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">Boxes ({boxesOnPage.length})</span>
            <span className="sm:hidden font-mono text-[11px]">{boxesOnPage.length}</span>
          </button>

          <div className="h-3.5 w-px bg-border/60 mx-0.5 shrink-0" aria-hidden="true" />

          <div className="document-zoom flex items-center gap-0.5 shrink-0">
            <button
              type="button"
              disabled={zoomIndex === 0}
              onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}
              className="document-btn"
              aria-label="Zoom out"
              title="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="tabular-nums min-w-[34px] sm:min-w-[40px] text-center font-mono text-[11px] font-medium text-foreground select-none shrink-0">
              {zoom.label}
            </span>
            <button
              type="button"
              disabled={zoomIndex === ZOOM_LEVELS.length - 1}
              onClick={() =>
                setZoomIndex((z) => Math.min(ZOOM_LEVELS.length - 1, z + 1))
              }
              className="document-btn"
              aria-label="Zoom in"
              title="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </GlassSurface>
      </div>


      </div>

      {/* Footer Legend */}
      <div className="document-legend flex flex-wrap items-center justify-between gap-2 px-3.5 pt-3 text-[11px] font-mono text-muted-foreground border-t border-border/60">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-xs border border-[#8a6b42] bg-[#8a6b42]/20" />
            Header Field
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-xs border border-stone-500 bg-stone-500/20" />
            Line Item
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-xs border-2 border-accent bg-accent/30" />
            Active Target
          </span>
        </div>
        <span className="text-muted-foreground/75 hidden sm:inline">
          Click any box or field to ground evidence
        </span>
      </div>
    </div>
  );
}
