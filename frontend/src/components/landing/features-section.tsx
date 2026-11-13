"use client";

import { useEffect, useRef, useState } from "react";

const features = [
  {
    number: "01",
    title: "Multimodal VLM Extraction",
    tagline: "Fine-Tuned Qwen3.5-0.8B",
    description:
      "Direct vision-language inference extracts complex tabular items, invoice metadata, payment terms, and vendor details without brittle regular expressions.",
    visual: "vlm",
  },
  {
    number: "02",
    title: "Indra OCR Coordinate Grounding",
    tagline: "Verifiable [0..1000] Bounding Boxes",
    description:
      "Every single line item and field is visually grounded back to its exact coordinate slice on the original scan. Click any field to inspect its bounding polygon.",
    visual: "grounding",
  },
  {
    number: "03",
    title: "Dual-Engine Architecture",
    tagline: "Local GPU First, Cloud Fallback",
    description:
      "Process sensitive invoices completely air-gapped on your private GPU. Escalate to LiteLLM (Gemini, OpenAI, OpenRouter) seamlessly when confidence thresholds require it.",
    visual: "pipeline",
  },
  {
    number: "04",
    title: "Financial Reconciliation",
    tagline: "Multi-Currency & Tax Audit",
    description:
      "Currencies are never mixed. Built-in math checks verify subtotal + tax = total discrepancies instantly before persisting to PostgreSQL or exporting to CSV/JSON.",
    visual: "reconcile",
  },
];

function VLMVisual() {
  return (
    <svg viewBox="0 0 200 160" className="w-full h-full text-foreground/80">
      <rect
        x="30"
        y="20"
        width="140"
        height="120"
        rx="8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
      <rect
        x="45"
        y="35"
        width="60"
        height="8"
        rx="2"
        fill="currentColor"
        opacity="0.3"
      />
      <rect
        x="45"
        y="50"
        width="110"
        height="6"
        rx="2"
        fill="currentColor"
        opacity="0.15"
      />
      <rect
        x="45"
        y="62"
        width="95"
        height="6"
        rx="2"
        fill="currentColor"
        opacity="0.15"
      />

      {/* Target highlight */}
      <rect
        x="45"
        y="80"
        width="110"
        height="26"
        rx="4"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.5"
      >
        <animate
          attributeName="stroke-opacity"
          values="0.3;1;0.3"
          dur="2.5s"
          repeatCount="indefinite"
        />
      </rect>
      <text
        x="55"
        y="97"
        fontSize="10"
        fontFamily="monospace"
        fill="var(--accent)"
        fontWeight="bold"
      >
        TOTAL €1,450.00
      </text>
    </svg>
  );
}

function GroundingVisual() {
  return (
    <svg viewBox="0 0 200 160" className="w-full h-full text-foreground/80">
      {/* Target page */}
      <rect
        x="40"
        y="20"
        width="120"
        height="120"
        rx="6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      {/* Coordinate lines */}
      <line
        x1="40"
        y1="75"
        x2="160"
        y2="75"
        stroke="currentColor"
        strokeWidth="1"
        strokeDasharray="2 2"
        opacity="0.25"
      />
      <line
        x1="100"
        y1="20"
        x2="100"
        y2="140"
        stroke="currentColor"
        strokeWidth="1"
        strokeDasharray="2 2"
        opacity="0.25"
      />

      {/* Coordinate polygon box */}
      <rect
        x="60"
        y="60"
        width="80"
        height="30"
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <animate
          attributeName="transform"
          type="scale"
          values="1;1.03;1"
          dur="3s"
          repeatCount="indefinite"
        />
      </rect>

      {/* Reticle corners */}
      <circle cx="60" cy="60" r="2.5" fill="var(--accent)" />
      <circle cx="140" cy="60" r="2.5" fill="var(--accent)" />
      <circle cx="60" cy="90" r="2.5" fill="var(--accent)" />
      <circle cx="140" cy="90" r="2.5" fill="var(--accent)" />

      <text
        x="72"
        y="78"
        fontSize="9"
        fontFamily="monospace"
        fill="currentColor"
        opacity="0.8"
      >
        [284, 150, 780]
      </text>
    </svg>
  );
}

function PipelineVisual() {
  return (
    <svg viewBox="0 0 200 160" className="w-full h-full text-foreground/80">
      {/* Local GPU node */}
      <rect
        x="25"
        y="60"
        width="55"
        height="40"
        rx="6"
        fill="currentColor"
        opacity="0.08"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <text
        x="36"
        y="84"
        fontSize="9"
        fontFamily="monospace"
        fontWeight="bold"
        fill="currentColor"
      >
        GPU: 0
      </text>

      {/* Cloud Node */}
      <rect
        x="120"
        y="60"
        width="55"
        height="40"
        rx="6"
        fill="currentColor"
        opacity="0.08"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <text
        x="131"
        y="84"
        fontSize="9"
        fontFamily="monospace"
        fontWeight="bold"
        fill="currentColor"
      >
        CLOUD
      </text>

      {/* Connector with moving dot */}
      <line
        x1="80"
        y1="80"
        x2="120"
        y2="80"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="3 3"
      />
      <circle cx="100" cy="80" r="3" fill="var(--accent)">
        <animate
          attributeName="cx"
          values="80;120;80"
          dur="2.5s"
          repeatCount="indefinite"
        />
      </circle>
    </svg>
  );
}

function ReconcileVisual() {
  return (
    <svg viewBox="0 0 200 160" className="w-full h-full text-foreground/80">
      <rect
        x="35"
        y="30"
        width="130"
        height="100"
        rx="8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      {/* Check status mark */}
      <circle
        cx="145"
        cy="50"
        r="10"
        fill="var(--success, #416d50)"
        opacity="0.2"
      />
      <path
        d="M141 50l3 3 5-5"
        fill="none"
        stroke="var(--success, #416d50)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      <text
        x="50"
        y="55"
        fontSize="10"
        fontFamily="monospace"
        fontWeight="bold"
        fill="currentColor"
      >
        SUBTOTAL: $800.00
      </text>
      <text
        x="50"
        y="75"
        fontSize="10"
        fontFamily="monospace"
        fill="currentColor"
        opacity="0.7"
      >
        TAX (8%):  $64.00
      </text>
      <line
        x1="50"
        y1="88"
        x2="150"
        y2="88"
        stroke="currentColor"
        strokeWidth="1"
      />
      <text
        x="50"
        y="108"
        fontSize="11"
        fontFamily="monospace"
        fontWeight="bold"
        fill="currentColor"
      >
        TOTAL:    $864.00
      </text>
    </svg>
  );
}

export function FeaturesSection() {
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
      id="features"
      ref={sectionRef}
      className="relative py-24 lg:py-32 border-t border-border"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Section Header */}
        <div
          className={`max-w-3xl mb-16 lg:mb-24 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
            <span className="w-8 h-px bg-foreground/30" />
            Core Capabilities
          </span>
          <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-6">
            Engineered for precision.
            <br />
            <span className="text-muted-foreground">
              Built for financial auditability.
            </span>
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Eliminate error-prone manual data entry with state-of-the-art vision
            models, visual coordinate provenance, and strict multi-currency
            verification.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid md:grid-cols-2 gap-6 lg:gap-8">
          {features.map((feature, idx) => (
            <div
              key={feature.number}
              className={`glass-surface rounded-2xl p-8 lg:p-10 flex flex-col justify-between hover-lift transition-all duration-500 group ${
                isVisible
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: `${idx * 100 + 100}ms` }}
            >
              <div>
                <div className="flex items-center justify-between mb-8">
                  <span className="font-mono text-xs text-muted-foreground tracking-widest">
                    FEATURE // {feature.number}
                  </span>
                  <span className="text-xs font-mono uppercase px-2.5 py-1 rounded-full bg-muted border border-border text-muted-foreground">
                    {feature.tagline}
                  </span>
                </div>

                {/* Visual Canvas/Diagram */}
                <div className="w-full h-44 mb-8 rounded-xl bg-field/80 border border-hairline/80 flex items-center justify-center p-4 overflow-hidden">
                  {feature.visual === "vlm" ? (
                    <VLMVisual />
                  ) : feature.visual === "grounding" ? (
                    <GroundingVisual />
                  ) : feature.visual === "pipeline" ? (
                    <PipelineVisual />
                  ) : (
                    <ReconcileVisual />
                  )}
                </div>

                <h3 className="text-2xl font-display font-semibold text-foreground mb-3">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
