"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

const plans = [
  {
    name: "Community",
    tagline: "Open-Source & Self-Hosted",
    price: { monthly: 0, annual: 0 },
    description: "For developers and internal deployments running on local hardware.",
    features: [
      "Local GPU Qwen3.5-0.8B VLM",
      "Indra OCR 1.1 coordinate grounding",
      "PostgreSQL relational ledger",
      "Interactive bounding box review",
      "CSV & JSON batch export",
      "Zero telemetry / air-gapped",
    ],
    cta: "Launch Workspace",
    href: "/extract",
    popular: false,
  },
  {
    name: "Team Workstation",
    tagline: "Collaborative Finance Desk",
    price: { monthly: 49, annual: 39 },
    description: "For finance departments managing high-volume invoice reconciliation.",
    features: [
      "Everything in Community",
      "Hybrid LiteLLM cloud escalation",
      "Multi-user demo sessions & passcodes",
      "Automated currency validation",
      "Priority batch queue processing",
      "Cloud key vault integration",
      "Audit logging & soft deletes",
    ],
    cta: "Start Free Trial",
    href: "/extract",
    popular: true,
  },
  {
    name: "Enterprise",
    tagline: "Custom Weights & Air-Gapped",
    price: { monthly: null, annual: null },
    description: "For large enterprises requiring tailored VLM fine-tuning and compliance.",
    features: [
      "Custom LoRA fine-tuning on your invoices",
      "SAP, NetSuite & QuickBooks connectors",
      "Strict zero-egress hardware deployment",
      "Dedicated model inference nodes",
      "Custom DTO schema definitions",
      "24/7 SLA and engineering support",
    ],
    cta: "Talk to Engineering",
    href: "mailto:sales@invoflow.ai",
    popular: false,
  },
];

export function PricingSection() {
  const [isAnnual, setIsAnnual] = useState(true);

  return (
    <section id="pricing" className="relative py-24 lg:py-32 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="max-w-3xl mb-16 lg:mb-20">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground block mb-3">
            Predictable Pricing
          </span>
          <h2 className="font-display text-4xl lg:text-6xl tracking-tight text-foreground mb-4">
            Transparent plans for
            <br />
            teams of every size.
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground">
            Start with our open-source local workstation, or scale up with hybrid
            cloud escalation and enterprise fine-tuning.
          </p>

          {/* Billing Switch */}
          <div className="flex items-center gap-3.5 mt-8">
            <span
              className={`text-xs font-mono font-medium ${
                !isAnnual ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              Monthly
            </span>
            <button
              type="button"
              onClick={() => setIsAnnual(!isAnnual)}
              className="relative w-12 h-6.5 bg-muted rounded-full p-1 border border-border cursor-pointer transition-colors"
              aria-label="Toggle annual billing discount"
            >
              <div
                className={`w-4.5 h-4.5 bg-foreground rounded-full transition-transform duration-300 ${
                  isAnnual ? "translate-x-5.5" : "translate-x-0"
                }`}
              />
            </button>
            <span
              className={`text-xs font-mono font-medium flex items-center gap-1.5 ${
                isAnnual ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              Annual
              <span className="text-[10px] uppercase font-bold text-accent bg-accent/15 px-2 py-0.5 rounded-full">
                Save 20%
              </span>
            </span>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid md:grid-cols-3 gap-6 lg:gap-8 items-stretch">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl p-8 flex flex-col justify-between transition-all duration-300 ${
                plan.popular
                  ? "glass-surface border-2 border-foreground shadow-xl relative"
                  : "glass-subtle border border-border"
              }`}
            >
              <div>
                {plan.popular ? (
                  <span className="absolute -top-3 left-8 text-[10px] font-mono uppercase tracking-widest bg-foreground text-background font-bold px-3 py-1 rounded-full shadow-sm">
                    Most Popular
                  </span>
                ) : null}

                <div className="mb-4">
                  <h3 className="text-xl font-display font-semibold text-foreground">
                    {plan.name}
                  </h3>
                  <p className="text-xs font-mono text-muted-foreground mt-0.5">
                    {plan.tagline}
                  </p>
                </div>

                <div className="mb-6 pb-6 border-b border-border">
                  {plan.price.monthly !== null ? (
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl lg:text-5xl font-display font-semibold text-foreground">
                        ${isAnnual ? plan.price.annual : plan.price.monthly}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">
                        / month
                      </span>
                    </div>
                  ) : (
                    <div className="text-3xl font-display font-semibold text-foreground">
                      Custom
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                    {plan.description}
                  </p>
                </div>

                {/* Feature List */}
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-center gap-2.5 text-xs text-foreground/90"
                    >
                      <Check className="w-4 h-4 text-emerald-500 shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <Link
                href={plan.href}
                className={`w-full py-3 rounded-full text-center text-xs lg:text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-1.5 ${
                  plan.popular
                    ? "bg-foreground hover:bg-foreground/90 text-background shadow-md"
                    : "border border-border bg-card hover:bg-card/80 text-foreground"
                }`}
              >
                <span>{plan.cta}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
