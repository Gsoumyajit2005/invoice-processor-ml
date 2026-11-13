"use client";

import { useEffect, useState, useRef } from "react";
import { TrendingUp, Cpu, CheckCircle2, BarChart3, ArrowUpRight } from "lucide-react";

interface BenchmarkMetric {
  name: string;
  category: string;
  baseScore: number;
  loraScore: number;
  unit: string;
  higherIsBetter: boolean;
  highlight?: string;
}

interface BenchmarkDataset {
  id: string;
  label: string;
  badge: string;
  docCount: string;
  description: string;
  metrics: BenchmarkMetric[];
}

const datasets: BenchmarkDataset[] = [
  {
    id: "cord",
    label: "CORD-v2 Receipts",
    badge: "Indonesian Retail",
    docCount: "N = 30",
    description:
      "Challenging menu-item receipts with inclusive/exclusive tax lines, itemized dining bills, and complex currency formats.",
    metrics: [
      {
        name: "Tax Amount Accuracy",
        category: "Financial Calculation",
        baseScore: 40.0,
        loraScore: 100.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "+60.0% jump via tax-inclusive teacher audit",
      },
      {
        name: "Total Amount Accuracy",
        category: "Core Total",
        baseScore: 79.3,
        loraScore: 100.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "Zero confusion with cash-tendered/change",
      },
      {
        name: "Line-Item F1 Score",
        category: "Table Grounding",
        baseScore: 84.9,
        loraScore: 96.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "Extracted descriptions and prices aligned",
      },
      {
        name: "Math Reconciliation Rate",
        category: "Arithmetic Audit",
        baseScore: 66.7,
        loraScore: 83.3,
        unit: "%",
        higherIsBetter: true,
        highlight: "Subtotal + Tax matches Grand Total",
      },
    ],
  },
  {
    id: "sroie",
    label: "SROIE Scans",
    badge: "Thermal Paper",
    docCount: "N = 30",
    description:
      "Faded 2-digit thermal receipt dates (DD.MM.YY), corrupted tax columns, and seller vs buyer identification.",
    metrics: [
      {
        name: "Total Amount Match",
        category: "Grand Total",
        baseScore: 70.0,
        loraScore: 86.7,
        unit: "%",
        higherIsBetter: true,
        highlight: "+16.7% improvement on noisy prints",
      },
      {
        name: "Vendor Name (Fuzzy)",
        category: "Entity Extraction",
        baseScore: 83.3,
        loraScore: 100.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "100% vendor recognition achieved",
      },
      {
        name: "Date Parsing (Exact)",
        category: "Temporal Parsing",
        baseScore: 83.3,
        loraScore: 96.7,
        unit: "%",
        higherIsBetter: true,
        highlight: "Accurate ISO-8601 date normalization",
      },
      {
        name: "Vendor Name (Exact)",
        category: "String Match",
        baseScore: 70.0,
        loraScore: 83.3,
        unit: "%",
        higherIsBetter: true,
        highlight: "Scrubbed registration/tax numbers",
      },
    ],
  },
  {
    id: "temp_docs",
    label: "Multi-Format Temp Docs",
    badge: "EU & B2B Invoices",
    docCount: "N = 12",
    description:
      "Real-world multi-page tabular invoices, German B2B layouts, and European cross-border tax statements.",
    metrics: [
      {
        name: "Math Reconciliation",
        category: "Arithmetic Audit",
        baseScore: 100.0,
        loraScore: 100.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "100% perfect arithmetic verification",
      },
      {
        name: "Line-Item F1 Score",
        category: "Table Extraction",
        baseScore: 91.7,
        loraScore: 91.7,
        unit: "%",
        higherIsBetter: true,
        highlight: "High precision across multi-column tables",
      },
      {
        name: "JSON Schema Validity",
        category: "Structural Output",
        baseScore: 100.0,
        loraScore: 100.0,
        unit: "%",
        higherIsBetter: true,
        highlight: "0 malformed outputs with 1536 max tokens",
      },
      {
        name: "Total Amount Close",
        category: "Amount Precision",
        baseScore: 90.9,
        loraScore: 90.9,
        unit: "%",
        higherIsBetter: true,
        highlight: "Preserved precision on complex bills",
      },
    ],
  },
];

const highlights = [
  {
    label: "Failure Reduction",
    value: "-75%",
    meta: "16 failures down to 4 across all 72 benchmark docs",
    color: "from-rose-500/20 to-orange-500/20 border-orange-500/30 text-orange-600 dark:text-orange-400",
  },
  {
    label: "CORD Total & Tax Accuracy",
    value: "100%",
    meta: "Perfect extraction score on CORD-v2 test set",
    color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
  },
  {
    label: "Peak Training VRAM",
    value: "3.26 GB",
    meta: "Trained on consumer NVIDIA RTX 3050 6GB Laptop GPU",
    color: "from-blue-500/20 to-indigo-500/20 border-blue-500/30 text-blue-600 dark:text-blue-400",
  },
  {
    label: "Adapter Runtime Overhead",
    value: "0 ms",
    meta: "Merged at load time via .merge_and_unload()",
    color: "from-amber-500/20 to-yellow-500/20 border-amber-500/30 text-amber-600 dark:text-amber-400",
  },
];

export function BenchmarksSection() {
  const [activeTab, setActiveTab] = useState("cord");
  const [isVisible, setIsVisible] = useState(false);
  const [animateBars, setAnimateBars] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          setTimeout(() => setAnimateBars(true), 200);
        }
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const currentDataset = datasets.find((d) => d.id === activeTab) || datasets[0];

  return (
    <section
      id="benchmarks"
      ref={sectionRef}
      className="relative py-24 lg:py-32 border-b border-border overflow-hidden"
    >
      {/* Background radial glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] lg:w-[900px] h-[500px] bg-accent/5 rounded-full blur-3xl pointer-events-none"
        aria-hidden="true"
      />

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Section Header */}
        <div
          className={`max-w-3xl mb-16 lg:mb-20 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="inline-flex items-center gap-2.5 text-xs font-mono uppercase tracking-widest text-accent font-semibold mb-4 bg-accent/10 px-3 py-1 rounded-full w-fit">
            <BarChart3 className="w-3.5 h-3.5" />
            Verified Empirical Ablation
          </span>
          <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-4">
            Quantitative benchmarks.
            <br />
            <span className="text-muted-foreground">Rigorous LoRA evaluation.</span>
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground leading-relaxed">
            We fine-tuned a parameter-efficient BF16 LoRA adapter on top of Qwen3.5-0.8B inside a 6GB VRAM budget. Tested on 72 unseen documents across CORD-v2, SROIE, and multi-format German B2B invoices.
          </p>
        </div>

        {/* 4 KPI Banner Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-14">
          {highlights.map((h, i) => (
            <div
              key={i}
              className={`p-6 rounded-2xl border bg-gradient-to-br backdrop-blur-md glass-surface transition-all duration-500 hover:-translate-y-0.5 ${h.color}`}
            >
              <div className="text-xs font-mono uppercase tracking-wider opacity-80 mb-2 font-medium">
                {h.label}
              </div>
              <div className="text-3xl lg:text-4xl font-display font-bold tracking-tight mb-2">
                {h.value}
              </div>
              <div className="text-xs text-foreground/75 leading-relaxed font-sans">
                {h.meta}
              </div>
            </div>
          ))}
        </div>

        {/* Interactive Benchmark Graph Card */}
        <div className="glass-surface rounded-3xl border border-border p-6 lg:p-10 shadow-xl backdrop-blur-xl">
          {/* Header & Tabs */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-8 border-b border-border/80">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-2xl font-display font-semibold text-foreground">
                  {currentDataset.label}
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20">
                  {currentDataset.docCount}
                </span>
                <span className="hidden sm:inline px-2.5 py-0.5 rounded-full text-xs font-mono bg-muted text-muted-foreground">
                  {currentDataset.badge}
                </span>
              </div>
              <p className="text-xs lg:text-sm text-muted-foreground max-w-xl">
                {currentDataset.description}
              </p>
            </div>

            {/* Dataset Switcher Tabs */}
            <div className="flex flex-wrap gap-2 p-1.5 rounded-2xl bg-muted/50 border border-border/70 self-start lg:self-auto">
              {datasets.map((dataset) => {
                const isActive = activeTab === dataset.id;
                return (
                  <button
                    key={dataset.id}
                    type="button"
                    onClick={() => {
                      setActiveTab(dataset.id);
                      setAnimateBars(false);
                      setTimeout(() => setAnimateBars(true), 50);
                    }}
                    className={`px-4 py-2 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                      isActive
                        ? "bg-foreground text-background shadow-md font-semibold"
                        : "text-muted-foreground hover:text-foreground hover:bg-card/60"
                    }`}
                  >
                    {dataset.label.split(" ")[0]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center justify-between gap-4 py-6">
            <div className="flex items-center gap-6 text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded bg-muted-foreground/35 border border-muted-foreground/50" />
                <span className="text-muted-foreground">Base Model (Qwen3.5-0.8B)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded bg-gradient-to-r from-orange-500 via-amber-500 to-emerald-500 border border-orange-400" />
                <span className="font-semibold text-foreground">InvoFlow LoRA Adapter</span>
              </div>
            </div>
            <div className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              <span>Evaluated at 1536 max tokens</span>
            </div>
          </div>

          {/* Grouped Comparison Bars */}
          <div className="space-y-6 lg:space-y-8 pt-2">
            {currentDataset.metrics.map((metric) => {
              const delta = metric.loraScore - metric.baseScore;
              const hasImprovement = delta > 0;

              return (
                <div
                  key={metric.name}
                  className="p-4 lg:p-5 rounded-2xl bg-card/40 border border-border/60 hover:border-accent/30 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <div>
                      <span className="text-sm lg:text-base font-semibold text-foreground block">
                        {metric.name}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">
                        {metric.category} {metric.highlight ? `· ${metric.highlight}` : ""}
                      </span>
                    </div>

                    {hasImprovement ? (
                      <span className="self-start sm:self-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25">
                        <TrendingUp className="w-3 h-3" />
                        +{delta.toFixed(1)}% Gain
                      </span>
                    ) : (
                      <span className="self-start sm:self-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-mono text-muted-foreground bg-muted/60 border border-border">
                        Saturated (100%)
                      </span>
                    )}
                  </div>

                  {/* Dual Bar Display */}
                  <div className="space-y-2.5 pt-1">
                    {/* Base Bar */}
                    <div className="flex items-center gap-3">
                      <span className="w-14 sm:w-16 text-[11px] font-mono text-muted-foreground shrink-0">
                        Base
                      </span>
                      <div className="flex-1 h-6 bg-muted/60 rounded-lg overflow-hidden p-0.5 border border-border/40 relative">
                        <div
                          className="h-full bg-muted-foreground/35 rounded-md transition-all duration-1000 ease-out flex items-center justify-end pr-2"
                          style={{
                            width: animateBars ? `${metric.baseScore}%` : "0%",
                          }}
                        >
                          <span className="text-[10px] font-mono font-medium text-foreground">
                            {metric.baseScore.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* LoRA Bar (Colorful Gradient) */}
                    <div className="flex items-center gap-3">
                      <span className="w-14 sm:w-16 text-[11px] font-mono font-bold text-foreground shrink-0">
                        LoRA
                      </span>
                      <div className="flex-1 h-7.5 bg-muted/60 rounded-lg overflow-hidden p-0.5 border border-border/40 relative shadow-inner">
                        <div
                          className="h-full bg-gradient-to-r from-orange-500 via-amber-500 to-emerald-500 rounded-md transition-all duration-1000 ease-out flex items-center justify-end pr-2.5 shadow-sm"
                          style={{
                            width: animateBars ? `${metric.loraScore}%` : "0%",
                          }}
                        >
                          <span className="text-xs font-mono font-bold text-black drop-shadow-xs">
                            {metric.loraScore.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Technical Specs & Hardware Footnote */}
          <div className="mt-8 pt-6 border-t border-border flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs font-mono text-muted-foreground">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-accent shrink-0" />
              <span>
                NVIDIA RTX 3050 6GB Laptop GPU · PyTorch 2.15 + CUDA 13.2 · 52 Steps (17m 56s)
              </span>
            </div>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-foreground transition-colors group"
            >
              <span>Inspect Raw JSON Eval Metrics</span>
              <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
