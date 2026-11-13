"use client";

import { useEffect, useState, useRef } from "react";
import { Shield, Lock, FileCheck, KeyRound } from "lucide-react";

const securityFeatures = [
  {
    icon: Lock,
    title: "Zero Cloud Retention",
    description:
      "When running in Local GPU mode, document images and parsed financial figures never touch external servers or public clouds.",
  },
  {
    icon: KeyRound,
    title: "Non-Custodial API Keys",
    description:
      "Cloud provider API keys (Gemini, OpenAI, OpenRouter) are saved strictly in browser session storage and transmitted directly via secure proxy.",
  },
  {
    icon: Shield,
    title: "Cryptographic Sessions",
    description:
      "Demonstration access and workspace endpoints are protected by HMAC SHA-256 authenticated session cookies with strict TTL enforcement.",
  },
  {
    icon: FileCheck,
    title: "Complete Audit Provenance",
    description:
      "Every persisted row preserves original bounding box coordinates, extraction latency, model identity, and human edit history.",
  },
];

const certifications = [
  "Air-Gapped Compatible",
  "Zero Vendor Training",
  "HMAC SHA-256 Signed",
  "PostgreSQL Row Isolation",
  "GDPR / CCPA Ready",
];

export function SecuritySection() {
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
      id="security"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-muted/30 border-b border-border overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Content */}
          <div
            className={`transition-all duration-700 ${
              isVisible
                ? "opacity-100 translate-y-0"
                : "opacity-0 translate-y-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
              <span className="w-8 h-px bg-foreground/30" />
              Financial Data Governance
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-6">
              Data sovereignty is
              <br />
              <span className="text-accent">non-negotiable.</span>
            </h2>
            <p className="text-lg text-muted-foreground leading-relaxed mb-10">
              Corporate balance sheets and supplier invoices contain sensitive
              pricing, margin, and identity data. InvoFlow AI is built from the
              ground up with privacy-preserving architectural guarantees.
            </p>

            {/* Certifications Pills */}
            <div className="flex flex-wrap gap-2.5">
              {certifications.map((cert) => (
                <span
                  key={cert}
                  className="px-3.5 py-1.5 rounded-full border border-border bg-card text-xs font-mono text-foreground"
                >
                  {cert}
                </span>
              ))}
            </div>
          </div>

          {/* Right: Security Cards Grid */}
          <div className="grid sm:grid-cols-2 gap-5">
            {securityFeatures.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="glass-surface p-6 rounded-2xl border border-border flex flex-col justify-between"
                >
                  <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-5">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-foreground mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
