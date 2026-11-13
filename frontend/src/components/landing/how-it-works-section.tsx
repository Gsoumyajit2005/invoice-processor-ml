"use client";

import { useEffect, useRef, useState } from "react";

const steps = [
  {
    number: "I",
    title: "Ingest & Normalize",
    subtitle: "Multiformat Intake",
    description:
      "Upload invoices and receipts in PDF, PNG, JPG, or WebP. Automatic coordinate normalization and DPI scaling prepare high-resolution scans for OCR passes.",
    code: `// Multi-page PDF or scan intake via FastAPI
const formData = new FormData();
formData.append("file", invoiceFile);
formData.append("mode", "auto"); // "local" first, "cloud" fallback

const res = await fetch("/api/v1/extract", {
  method: "POST",
  body: formData
});
const { invoice_id, extraction } = await res.json();`,
  },
  {
    number: "II",
    title: "Inference & Grounding",
    subtitle: "Vision-Language Grounding",
    description:
      "Fine-tuned Qwen3.5-0.8B LoRA extracts semantic structures while Indra OCR 1.1 calculates exact bounding coordinates in normalized [0..1000] polygon space.",
    code: `// Verified extraction DTO with [0..1000] provenance
{
  "vendor": "Acme Supplies Ltd",
  "receipt_number": "INV-2026-894",
  "currency": "EUR",
  "total_amount": 1420.50,
  "items_match_subtotal": true,
  "totals_reconcile": true,
  "provenance": {
    "total_amount": {
      "bbox": { "page": 1, "x1": 680, "y1": 890, "x2": 920, "y2": 930 },
      "source": "ocr_matched"
    }
  }
}`,
  },
  {
    number: "III",
    title: "Verify & Persist",
    subtitle: "Human-in-the-Loop Audit",
    description:
      "Operators inspect highlighted coordinates side-by-side with extracted values. Verified records persist to PostgreSQL with complete provenance and audit logs.",
    code: `// Audit verification & structured ledger export
await fetch(\`/api/v1/invoices/\${invoice_id}/review\`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ status: "verified" })
});

// Download ledger export: CSV, raw JSON, or HTML
window.open("/api/v1/invoices/export/csv");`,
  },
];

export function HowItWorksSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-foreground text-background overflow-hidden"
    >
      {/* Subtle diagonal lines pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        aria-hidden="true"
      >
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `repeating-linear-gradient(
              -45deg,
              transparent,
              transparent 40px,
              currentColor 40px,
              currentColor 41px
            )`,
          }}
        />
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-16 lg:mb-20">
          <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-background/60 mb-4">
            <span className="w-8 h-px bg-background/30" />
            Extraction Workflow
          </span>
          <h2
            className={`text-4xl lg:text-6xl font-display tracking-tight transition-all duration-700 ${
              isVisible
                ? "opacity-100 translate-y-0"
                : "opacity-0 translate-y-4"
            }`}
          >
            Three stages.
            <br />
            <span className="text-background/50">Zero manual transcription.</span>
          </h2>
        </div>

        {/* Interactive Steps Layout */}
        <div className="grid lg:grid-cols-12 gap-10 lg:gap-14 items-start">
          {/* Step Selector List */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            {steps.map((step, idx) => (
              <button
                key={step.number}
                type="button"
                onClick={() => setActiveStep(idx)}
                className={`text-left p-6 rounded-2xl border transition-all duration-300 cursor-pointer ${
                  activeStep === idx
                    ? "bg-background/10 border-background/30 shadow-lg translate-x-2"
                    : "bg-transparent border-background/10 hover:border-background/20 opacity-70 hover:opacity-100"
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-background/20 text-background">
                    STEP {step.number}
                  </span>
                  <span className="text-xs font-mono text-background/60">
                    {step.subtitle}
                  </span>
                </div>
                <h3 className="text-xl font-display font-semibold text-background mb-2">
                  {step.title}
                </h3>
                <p className="text-xs lg:text-sm text-background/70 leading-relaxed">
                  {step.description}
                </p>
              </button>
            ))}
          </div>

          {/* Code & Data Preview Panel */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-background/20 bg-background/5 p-6 lg:p-8 backdrop-blur-md">
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-background/10 font-mono text-xs text-background/60">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  invoflow-pipeline.ts // stage_{activeStep + 1}
                </span>
                <span>TypeScript</span>
              </div>
              <pre className="font-mono text-xs lg:text-sm text-background/90 leading-relaxed overflow-x-auto whitespace-pre p-2">
                <code>{steps[activeStep].code}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
