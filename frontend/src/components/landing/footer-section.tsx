"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { AnimatedWave } from "./animated-wave";

const footerLinks = {
  Workstation: [
    { name: "Document Extraction", href: "/extract" },
    { name: "Invoices Ledger", href: "/invoices" },
    { name: "Batch Reconciliation", href: "/batch" },
    { name: "Liquid Glass Material Lab", href: "/liquid-glass-lab" },
  ],
  Architecture: [
    { name: "Indra OCR 1.1 Grounding", href: "#features" },
    { name: "Qwen3.5-0.8B LoRA", href: "#features" },
    { name: "Empirical Benchmarks", href: "#benchmarks" },
    { name: "LiteLLM Router Gateway", href: "#architecture" },
  ],
  Pipeline: [
    { name: "Modal Serverless", href: "#developers" },
    { name: "Hugging Face ZeroGPU", href: "#developers" },
    { name: "FastAPI REST API", href: "#developers" },
    { name: "CORD & SROIE Ablation", href: "#benchmarks" },
  ],
};

export function FooterSection() {
  return (
    <footer className="relative border-t border-border overflow-hidden">
      {/* Animated wave background */}
      <div
        className="absolute inset-0 h-72 opacity-25 pointer-events-none overflow-hidden"
        aria-hidden="true"
      >
        <AnimatedWave />
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Main Footer */}
        <div className="py-16 lg:py-24">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-10 lg:gap-12">
            {/* Brand Column */}
            <div className="col-span-2">
              <Link href="/" className="inline-flex items-center gap-2.5 mb-5">
                <div
                  className="w-7 h-7 rounded-lg bg-foreground text-background flex items-center justify-center font-bold text-xs"
                  aria-hidden="true"
                >
                  i.
                </div>
                <span className="text-xl font-display font-semibold text-foreground">
                  InvoFlow AI
                </span>
              </Link>

              <p className="text-xs lg:text-sm text-muted-foreground leading-relaxed mb-6 max-w-sm">
                Multimodal financial document intelligence powered by fine-tuned
                local vision models, coordinate grounding, and verifiable
                human-in-the-loop review.
              </p>

              <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Local VLM & FastAPI Ready
                </span>
              </div>
            </div>

            {/* Link Columns */}
            {Object.entries(footerLinks).map(([title, links]) => (
              <div key={title}>
                <h3 className="text-xs font-mono uppercase tracking-wider text-foreground font-semibold mb-4">
                  {title}
                </h3>
                <ul className="space-y-3">
                  {links.map((link) => (
                    <li key={link.name}>
                      <Link
                        href={link.href}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1 group"
                      >
                        <span>{link.name}</span>
                        {link.href.startsWith("http") ? (
                          <ArrowUpRight className="w-3 h-3 opacity-60 group-hover:opacity-100 transition-opacity" />
                        ) : null}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="py-6 border-t border-border/70 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground font-mono">
          <p>© {new Date().getFullYear()} InvoFlow AI. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/extract" className="hover:text-foreground transition-colors">
              Workspace
            </Link>
            <Link href="/invoices" className="hover:text-foreground transition-colors">
              Ledger
            </Link>
            <Link href="/liquid-glass-lab" className="hover:text-foreground transition-colors">
              Material Lab
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
