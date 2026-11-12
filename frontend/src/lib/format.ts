import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { InvoiceStatus, LineItem } from "@/lib/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatNumber(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || !Number.isFinite(amount)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format an amount respecting the document's ISO currency without ever assuming "$".
 * If currency is null/blank, formats strictly without injecting an assumed symbol.
 */
export function formatCurrency(
  amount: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (amount === null || amount === undefined || !Number.isFinite(amount)) {
    return "—";
  }
  const code = (currency ?? "").trim().toUpperCase();
  if (/^[A-Z]{3}$/.test(code)) {
    try {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: code,
        currencyDisplay: "code",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch {
      return `${code} ${formatNumber(amount)}`;
    }
  }
  if (code) {
    return `${code} ${formatNumber(amount)}`;
  }
  return formatNumber(amount);
}

export interface CurrencyTotalBucket {
  currency: string;
  count: number;
  amountCount: number;
  total: number;
}

/**
 * Aggregate invoice totals strictly grouped by currency code.
 * Never sums different currencies into a combined number.
 */
export function groupCurrencyTotals(
  items: Array<{ currency: string | null; total_amount: number | null }>,
): CurrencyTotalBucket[] {
  const map = new Map<string, CurrencyTotalBucket>();
  for (const item of items) {
    const key = (item.currency ?? "").trim().toUpperCase() || "UNSPECIFIED";
    const existing = map.get(key) ?? {
      currency: key,
      count: 0,
      amountCount: 0,
      total: 0,
    };
    existing.count += 1;
    if (
      item.total_amount !== null &&
      item.total_amount !== undefined &&
      Number.isFinite(item.total_amount)
    ) {
      existing.amountCount += 1;
      existing.total += item.total_amount;
    }
    map.set(key, existing);
  }
  return Array.from(map.values()).sort((a, b) => {
    if (a.currency === "UNSPECIFIED") return 1;
    if (b.currency === "UNSPECIFIED") return -1;
    return b.count - a.count || a.currency.localeCompare(b.currency);
  });
}

export interface MathReconciliation {
  lineItemsSum: number;
  hasLineItems: boolean;
  itemsMatchSubtotal: boolean | null;
  subtotalDiff: number | null;
  expectedTotal: number | null;
  totalsReconcile: boolean | null;
  totalDiff: number | null;
}

const MATH_TOLERANCE = 0.05;

export function computeReconciliation(
  lineItems: LineItem[],
  subtotal: number | null,
  taxAmount: number | null,
  discountAmount: number | null,
  totalAmount: number | null,
): MathReconciliation {
  const validLineTotals = lineItems
    .map((item) => {
      if (item.total_price !== null && Number.isFinite(item.total_price)) {
        return item.total_price;
      }
      if (
        item.quantity !== null &&
        item.unit_price !== null &&
        Number.isFinite(item.quantity) &&
        Number.isFinite(item.unit_price)
      ) {
        return item.quantity * item.unit_price;
      }
      return null;
    })
    .filter((v): v is number => v !== null);

  const hasLineItems = validLineTotals.length > 0;
  const lineItemsSum = Number(
    validLineTotals.reduce((acc, v) => acc + v, 0).toFixed(2),
  );

  let itemsMatchSubtotal: boolean | null = null;
  let subtotalDiff: number | null = null;
  if (hasLineItems && subtotal !== null && Number.isFinite(subtotal)) {
    subtotalDiff = Number((lineItemsSum - subtotal).toFixed(2));
    itemsMatchSubtotal = Math.abs(subtotalDiff) <= MATH_TOLERANCE;
  }

  const baseForTotal =
    subtotal !== null && Number.isFinite(subtotal)
      ? subtotal
      : hasLineItems
        ? lineItemsSum
        : null;

  let expectedTotal: number | null = null;
  let totalsReconcile: boolean | null = null;
  let totalDiff: number | null = null;

  if (baseForTotal !== null) {
    expectedTotal = Number(
      (baseForTotal + (taxAmount ?? 0) - (discountAmount ?? 0)).toFixed(2),
    );
    if (totalAmount !== null && Number.isFinite(totalAmount)) {
      totalDiff = Number((expectedTotal - totalAmount).toFixed(2));
      totalsReconcile = Math.abs(totalDiff) <= MATH_TOLERANCE;
    }
  }

  return {
    lineItemsSum,
    hasLineItems,
    itemsMatchSubtotal,
    subtotalDiff,
    expectedTotal,
    totalsReconcile,
    totalDiff,
  };
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function statusLabel(status: InvoiceStatus | string): string {
  switch (status) {
    case "extracted":
      return "Extracted";
    case "needs_review":
      return "Needs Review";
    case "verified":
      return "Verified";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}
