"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { listInvoices } from "@/lib/api-client";
import { formatCurrency } from "@/lib/format";
import type { InvoiceSummary } from "@/lib/types";
import { StatusBadge } from "./ui";

export function RecentDocuments() {
  const [documents, setDocuments] = useState<InvoiceSummary[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    listInvoices({ limit: 4 }).then(result => { if (active) setDocuments(result.items); }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);
  return (
    <section
      className="recent-documents mt-12 pt-8 border-t border-border/70"
      id="recent-documents"
      aria-labelledby="recent-heading"
    >
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              ACTIVITY HISTORY
            </span>
          </div>
          <h2
            id="recent-heading"
            className="font-display text-xl sm:text-2xl font-semibold text-foreground"
          >
            Continue where you left off
          </h2>
        </div>
        <Link
          href="/invoices"
          className="text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          View all invoices →
        </Link>
      </div>

      <div className="glass-surface recent-list rounded-2xl border border-border overflow-hidden shadow-xs">
        {failed ? (
          <p className="recent-empty p-8 text-center text-xs text-muted-foreground">
            Recent documents couldn’t be loaded.{" "}
            <Link href="/invoices" className="underline text-foreground">
              Open the ledger to retry.
            </Link>
          </p>
        ) : documents === null ? (
          <p className="recent-empty p-8 text-center text-xs text-muted-foreground font-mono" role="status">
            Loading recent documents…
          </p>
        ) : documents.length === 0 ? (
          <div className="recent-empty p-8 text-center flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <FileText aria-hidden="true" size={24} className="text-muted-foreground/60" />
            <p>Your documents will appear here after the first extraction.</p>
          </div>
        ) : (
          <>
            <div
              className="recent-row recent-labels font-mono text-[11px] uppercase tracking-wider text-muted-foreground bg-muted/40 border-b border-border/60"
              aria-hidden="true"
            >
              <span>Document</span>
              <span>Issued</span>
              <span>Status</span>
              <span>Amount</span>
            </div>
            <ul className="divide-y divide-border/60">
              {documents.map((document) => (
                <li key={document.id}>
                  <Link
                    href={`/invoices/${document.id}`}
                    className="recent-row hover:bg-muted/30 transition-colors"
                  >
                    <span className="min-w-0">
                      <strong className="text-foreground block truncate">
                        {document.vendor || document.filename}
                      </strong>
                      <small className="font-mono text-[11px] text-muted-foreground block truncate">
                        {document.receipt_number || document.filename}
                      </small>
                    </span>
                    <span className="recent-date font-mono text-xs text-muted-foreground">
                      {document.date || "—"}
                    </span>
                    <div>
                      <StatusBadge status={document.status} />
                    </div>
                    <strong className="tabular-nums recent-amount text-sm font-semibold text-foreground">
                      {formatCurrency(document.total_amount, document.currency)}
                    </strong>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}
