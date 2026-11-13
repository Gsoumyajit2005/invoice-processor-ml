"use client";

import Link from "next/link";
import { ArrowRight, Check, Terminal, Cloud, ShieldCheck, Server } from "lucide-react";

const topologies = [
  {
    name: "Local Workstation",
    tagline: "Docker Compose · Zero Egress",
    badge: "100% Private",
    icon: Terminal,
    description:
      "Run the entire multimodal extraction pipeline locally on your workstation or internal network with Docker Compose.",
    features: [
      "Indra OCR 1.1 ONNX engine on CPU (300ms)",
      "Qwen3.5-0.8B LoRA on local NVIDIA GPU",
      "PostgreSQL relational ledger with audit trails",
      "Interactive SVG [0..1000] review studio",
      "Export to CSV, raw JSON, and printable HTML",
      "Zero telemetry & zero external network egress",
    ],
    command: "docker compose up -d",
    cta: "Launch Workspace",
    href: "/extract",
    popular: false,
  },
  {
    name: "Hybrid Serverless",
    tagline: "Modal Serverless · Supabase DB",
    badge: "Scale-to-Zero",
    icon: Cloud,
    description:
      "Production-ready distributed deployment pairing Modal serverless workers with Supabase managed PostgreSQL.",
    features: [
      "Modal CPU autoscaling FastAPI backend",
      "Modal GPU / Hugging Face ZeroGPU workers",
      "Supabase managed PostgreSQL (asyncpg)",
      "LiteLLM BYO-key cloud escalation router",
      "Cloudflare R2 / AWS S3 document vault",
      "Automatic session cookies and passcode auth",
    ],
    command: "modal deploy backend/modal_app.py",
    cta: "Explore Ledger",
    href: "/invoices",
    popular: true,
  },
  {
    name: "Sovereign Enterprise",
    tagline: "Private GPU Cluster · Tailored LoRA",
    badge: "Air-Gapped",
    icon: Server,
    description:
      "Dedicated air-gapped infrastructure for regulated financial institutions requiring isolated execution and custom adapters.",
    features: [
      "Direct PyTorch 2.6 / vLLM execution on private GPUs",
      "Custom LoRA fine-tuning on proprietary formats",
      "HMAC SHA-256 signed session token vault",
      "Printable HTML reconciliation audit reports",
      "Strict data sovereignty with no model retention",
      "Automated currency validation (ISO 4217)",
    ],
    command: "python -m ml.train.finetune_lora",
    cta: "Review Architecture",
    href: "#architecture",
    popular: false,
  },
];

export function DeploymentSection() {
  return (
    <section id="deployment" className="relative py-24 lg:py-32 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Section Header */}
        <div className="max-w-3xl mb-16 lg:mb-20">
          <span className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-accent font-semibold mb-3 bg-accent/10 px-3 py-1 rounded-full w-fit">
            <ShieldCheck className="w-3.5 h-3.5" />
            Deployment Topologies
          </span>
          <h2 className="font-display text-4xl lg:text-6xl tracking-tight text-foreground mb-4">
            Deploy anywhere.
            <br />
            <span className="text-muted-foreground">Run completely air-gapped.</span>
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground">
            InvoFlow AI is built to fit your security model — from a single laptop using Docker to autoscaling serverless cloud workers and air-gapped enterprise GPU clusters.
          </p>
        </div>

        {/* 3 Topologies Grid */}
        <div className="grid lg:grid-cols-3 gap-8">
          {topologies.map((plan) => {
            const Icon = plan.icon;
            return (
              <div
                key={plan.name}
                className={`relative rounded-3xl p-8 transition-all duration-300 flex flex-col justify-between ${
                  plan.popular
                    ? "glass-surface border-2 border-accent/40 shadow-xl"
                    : "glass-surface border border-border hover:border-foreground/20"
                }`}
              >
                {/* Popular Pill */}
                {plan.popular ? (
                  <div className="absolute -top-3.5 left-8 bg-accent text-accent-foreground text-xs font-mono font-semibold px-3 py-1 rounded-full uppercase tracking-wider shadow-sm">
                    Recommended Architecture
                  </div>
                ) : null}

                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-accent">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-muted text-muted-foreground border border-border">
                      {plan.badge}
                    </span>
                  </div>

                  <h3 className="text-2xl font-display font-semibold text-foreground mb-1">
                    {plan.name}
                  </h3>
                  <div className="text-xs font-mono text-accent mb-4">
                    {plan.tagline}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                    {plan.description}
                  </p>

                  {/* Terminal Command Box */}
                  <div className="mb-6 p-3 rounded-xl bg-muted/60 border border-border/80 font-mono text-xs text-foreground/90 flex items-center gap-2 overflow-x-auto">
                    <span className="text-accent select-none">$</span>
                    <span className="select-all">{plan.command}</span>
                  </div>

                  {/* Feature Checklist */}
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2.5 text-xs text-foreground/80">
                        <Check className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CTA Button */}
                <Link
                  href={plan.href}
                  className={`w-full inline-flex items-center justify-center gap-2 h-12 rounded-full font-semibold text-sm transition-all ${
                    plan.popular
                      ? "bg-foreground hover:bg-foreground/90 text-background shadow-md group"
                      : "border border-border bg-card/60 hover:bg-card text-foreground group"
                  }`}
                >
                  {plan.cta}
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
