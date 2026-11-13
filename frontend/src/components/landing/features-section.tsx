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
    title: "HITL Review Studio",
    tagline: "Side-by-Side Audit Studio",
    description:
      "Interactive split-pane workspace visually links every extracted field to the scan. Inspect coordinate polygons, zoom and pan, edit values inline, and confirm verified records with full provenance.",
    visual: "studio",
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

function StudioVisual() {
  return (
    <svg viewBox="0 0 200 160" className="w-full h-full text-foreground/80">
      {/* Left Pane: Document Scan with Bounding Boxes */}
      <rect
        x="16"
        y="18"
        width="76"
        height="124"
        rx="5"
        fill="currentColor"
        fillOpacity="0.04"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      {/* Mini header lines on scan */}
      <rect x="24" y="28" width="30" height="5" rx="1.5" fill="currentColor" opacity="0.35" />
      <rect x="24" y="38" width="46" height="3" rx="1" fill="currentColor" opacity="0.2" />
      <rect x="24" y="46" width="38" height="3" rx="1" fill="currentColor" opacity="0.15" />
      <line x1="24" y1="56" x2="84" y2="56" stroke="currentColor" strokeWidth="0.8" opacity="0.2" />
      <rect x="24" y="62" width="58" height="3" rx="1" fill="currentColor" opacity="0.15" />
      <rect x="24" y="70" width="54" height="3" rx="1" fill="currentColor" opacity="0.15" />

      {/* Target grounded bounding box on scan */}
      <rect
        x="22"
        y="82"
        width="64"
        height="18"
        rx="3"
        fill="var(--accent)"
        fillOpacity="0.12"
        stroke="var(--accent)"
        strokeWidth="1.4"
      >
        <animate
          attributeName="stroke-opacity"
          values="0.5;1;0.5"
          dur="2s"
          repeatCount="indefinite"
        />
      </rect>
      <text
        x="26"
        y="94"
        fontSize="7"
        fontFamily="monospace"
        fontWeight="bold"
        fill="var(--accent)"
      >
        $1,420.50
      </text>

      {/* Floating Zoom / Page Navigation Pill on Document Viewer */}
      <rect
        x="28"
        y="114"
        width="52"
        height="14"
        rx="7"
        fill="currentColor"
        fillOpacity="0.1"
        stroke="currentColor"
        strokeWidth="0.8"
      />
      <circle cx="37" cy="121" r="2" fill="currentColor" opacity="0.4" />
      <rect x="43" y="119.5" width="22" height="3" rx="1" fill="currentColor" opacity="0.5" />
      <circle cx="71" cy="121" r="2" fill="currentColor" opacity="0.4" />

      {/* Connecting Interactive Ray / Grounding Link */}
      <path
        d="M 86 91 C 98 91, 100 80, 108 80"
        stroke="var(--accent)"
        strokeWidth="1.2"
        strokeDasharray="2.5 2"
        fill="none"
      />
      <circle cx="108" cy="80" r="2" fill="var(--accent)" />

      {/* Right Pane: Form & Verified Field Card */}
      <rect
        x="108"
        y="18"
        width="76"
        height="124"
        rx="5"
        fill="currentColor"
        fillOpacity="0.04"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      {/* Field 1: Vendor */}
      <rect
        x="114"
        y="26"
        width="64"
        height="24"
        rx="3.5"
        fill="currentColor"
        fillOpacity="0.06"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeOpacity="0.2"
      />
      <text x="119" y="34" fontSize="6" fontFamily="monospace" fill="currentColor" opacity="0.5">
        VENDOR
      </text>
      <text x="119" y="44" fontSize="7.5" fontWeight="bold" fill="currentColor">
        Acme Supplies
      </text>

      {/* Field 2: Total Amount (Active Focused & Verified) */}
      <rect
        x="114"
        y="58"
        width="64"
        height="36"
        rx="3.5"
        fill="var(--accent)"
        fillOpacity="0.1"
        stroke="var(--accent)"
        strokeWidth="1.2"
      />
      <text x="119" y="68" fontSize="6" fontFamily="monospace" fill="var(--accent)" fontWeight="bold">
        TOTAL AMOUNT
      </text>
      <circle cx="170" cy="66" r="3" fill="#10b981" />
      <path
        d="M 168.5 66 L 169.5 67.5 L 171.5 64.5"
        stroke="#ffffff"
        strokeWidth="0.8"
        fill="none"
        strokeLinecap="round"
      />
      <text x="119" y="82" fontSize="9" fontWeight="bold" fill="currentColor">
        $1,420.50
      </text>
      <text x="119" y="90" fontSize="5.5" fontFamily="monospace" fill="currentColor" opacity="0.6">
        [0..1000] Grounded
      </text>

      {/* Field 3: Status Action */}
      <rect
        x="114"
        y="102"
        width="64"
        height="18"
        rx="3.5"
        fill="currentColor"
        fillOpacity="0.08"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeOpacity="0.2"
      />
      <text x="124" y="114" fontSize="6.5" fontFamily="monospace" fontWeight="bold" fill="currentColor">
        ✓ VERIFIED LEDGER
      </text>
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
                  ) : feature.visual === "studio" ? (
                    <StudioVisual />
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
