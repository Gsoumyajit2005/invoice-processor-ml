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
  return <section className="recent-documents" id="recent-documents" aria-labelledby="recent-heading">
    <div className="recent-heading"><h2 id="recent-heading">Continue where you left off</h2><Link href="/invoices">View all invoices</Link></div>
    <div className="glass-surface recent-list">
      {failed ? <p className="recent-empty">Recent documents couldn’t be loaded. <Link href="/invoices">Open the ledger to retry.</Link></p> : documents === null ? <p className="recent-empty" role="status">Loading recent documents…</p> : documents.length === 0 ? <div className="recent-empty"><FileText aria-hidden="true" size={22} /><p>Your documents will appear here after the first extraction.</p></div> : <>
        <div className="recent-row recent-labels" aria-hidden="true"><span>Document</span><span>Issued</span><span>Status</span><span>Amount</span></div>
        <ul>{documents.map(document => <li key={document.id}>
          <Link href={`/invoices/${document.id}`} className="recent-row">
            <span className="min-w-0"><strong>{document.vendor || document.filename}</strong><small>{document.receipt_number || document.filename}</small></span>
            <span className="recent-date">{document.date || "No issue date"}</span><StatusBadge status={document.status} /><strong className="tabular-nums recent-amount">{formatCurrency(document.total_amount, document.currency)}</strong>
          </Link>
        </li>)}</ul>
      </>}
    </div>
  </section>;
}
