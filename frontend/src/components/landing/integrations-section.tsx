"use client";

import { useEffect, useState, useRef } from "react";

const integrationsRow1 = [
  { name: "PostgreSQL", category: "ACID Database" },
  { name: "Supabase", category: "Cloud Postgres" },
  { name: "Qwen3.5 VLM", category: "Vision-Language" },
  { name: "Indra OCR 1.1", category: "Coordinate Grounding" },
  { name: "LiteLLM", category: "Provider Fallback" },
  { name: "Hugging Face", category: "Model Weights" },
];

const integrationsRow2 = [
  { name: "QuickBooks", category: "Accounting Export" },
  { name: "Xero", category: "Ledger Sync" },
  { name: "SAP ERP", category: "Enterprise Connector" },
  { name: "Stripe", category: "Payment Receipts" },
  { name: "AWS S3 / R2", category: "Document Storage" },
  { name: "Ollama", category: "Local LLM Runtime" },
];

export function IntegrationsSection() {
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
      id="integrations"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden border-b border-border"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div
          className={`text-center max-w-3xl mx-auto mb-16 lg:mb-20 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
            <span className="w-8 h-px bg-foreground/30" />
            Integrations & Pipeline
            <span className="w-8 h-px bg-foreground/30" />
          </span>
          <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-4">
            Connects seamlessly with
            <br />
            your accounting stack.
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground">
            From local open weights and relational ledgers to enterprise ERP
            and accounting exports.
          </p>
        </div>
      </div>

      {/* Row 1: Forward Marquee */}
      <div className="w-full mb-5 overflow-hidden">
        <div className="flex gap-5 marquee">
          {[...Array(2)].map((_, setIdx) => (
            <div key={setIdx} className="flex gap-5 shrink-0">
              {integrationsRow1.map((item) => (
                <div
                  key={`${item.name}-${setIdx}`}
                  className="shrink-0 px-7 py-5 glass-surface rounded-2xl border border-border hover:border-accent/40 transition-colors duration-200 group"
                >
                  <div className="text-base font-semibold text-foreground group-hover:text-accent transition-colors">
                    {item.name}
                  </div>
                  <div className="text-xs font-mono text-muted-foreground mt-0.5">
                    {item.category}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Row 2: Reverse Marquee */}
      <div className="w-full overflow-hidden">
        <div className="flex gap-5 marquee-reverse">
          {[...Array(2)].map((_, setIdx) => (
            <div key={setIdx} className="flex gap-5 shrink-0">
              {integrationsRow2.map((item) => (
                <div
                  key={`${item.name}-${setIdx}`}
                  className="shrink-0 px-7 py-5 glass-surface rounded-2xl border border-border hover:border-accent/40 transition-colors duration-200 group"
                >
                  <div className="text-base font-semibold text-foreground group-hover:text-accent transition-colors">
                    {item.name}
                  </div>
                  <div className="text-xs font-mono text-muted-foreground mt-0.5">
                    {item.category}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
