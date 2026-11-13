"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { AnimatedSphere } from "./animated-sphere";

const words = ["extract", "ground", "reconcile", "audit"];

const stats = [
  { value: "99.2%", label: "coordinate precision", badge: "INDRA OCR 1.1" },
  { value: "< 840ms", label: "local VLM inference", badge: "QWEN3.5-0.8B" },
  { value: "100%", label: "private on-device", badge: "AIR-GAPPED GPU" },
  { value: "ISO 4217", label: "strict currency isolation", badge: "NO MIXED TOTALS" },
  { value: "Zero", label: "cloud data retention", badge: "NON-CUSTODIAL" },
];

export function HeroSection() {
  const isVisible = true;
  const [wordIndex, setWordIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setWordIndex((prev) => (prev + 1) % words.length);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative min-h-[92vh] flex flex-col justify-center overflow-hidden pt-20">
      {/* Animated sphere background */}
      <div className="absolute right-[-10%] top-1/2 -translate-y-1/2 w-[520px] h-[520px] lg:w-[780px] lg:h-[780px] opacity-40 pointer-events-none">
        <AnimatedSphere />
      </div>

      {/* Subtle grid lines */}
      <div
        className="absolute inset-0 overflow-hidden pointer-events-none opacity-20"
        aria-hidden="true"
      >
        {[...Array(6)].map((_, i) => (
          <div
            key={`h-${i}`}
            className="absolute h-px bg-foreground/15"
            style={{
              top: `${16.6 * (i + 1)}%`,
              left: 0,
              right: 0,
            }}
          />
        ))}
        {[...Array(8)].map((_, i) => (
          <div
            key={`v-${i}`}
            className="absolute w-px bg-foreground/15"
            style={{
              left: `${12.5 * (i + 1)}%`,
              top: 0,
              bottom: 0,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12 py-24 lg:py-32">
        {/* Eyebrow */}
        <div
          className={`mb-6 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          <span className="inline-flex items-center gap-2.5 text-xs font-mono uppercase tracking-widest text-muted-foreground bg-muted/60 px-3.5 py-1.5 rounded-full border border-border">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            Multimodal Financial Document Intelligence
          </span>
        </div>

        {/* Main headline */}
        <div className="mb-10 max-w-4xl">
          <h1
            className={`text-[clamp(2.8rem,8.5vw,7.5rem)] font-display leading-[0.94] tracking-tight transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="block text-foreground">The platform to</span>
            <span className="block text-foreground">
              automatically{" "}
              <span className="relative inline-block text-accent">
                <span key={wordIndex} className="inline-flex">
                  {words[wordIndex].split("").map((char, i) => (
                    <span
                      key={`${wordIndex}-${i}`}
                      className="inline-block animate-char-in"
                      style={{
                        animationDelay: `${i * 45}ms`,
                      }}
                    >
                      {char}
                    </span>
                  ))}
                </span>
                <span
                  className="absolute -bottom-1 left-0 right-0 h-2 bg-accent/20 rounded-full"
                  aria-hidden="true"
                />
              </span>
            </span>
          </h1>
        </div>

        {/* Description & CTAs */}
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-20 items-end">
          <p
            className={`text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-xl transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            High-accuracy invoice and receipt processing powered by fine-tuned
            local Qwen3.5-0.8B VLM, Indra OCR coordinate grounding, and
            PostgreSQL human-in-the-loop review.
          </p>

          <div
            className={`flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 transition-all duration-700 delay-300 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            <Link
              href="/extract"
              className="inline-flex items-center justify-center gap-2 bg-foreground hover:bg-foreground/90 text-background px-8 h-13 text-sm lg:text-base font-semibold rounded-full shadow-md group transition-all"
            >
              Launch Workspace
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link
              href="/invoices"
              className="inline-flex items-center justify-center gap-2 h-13 px-7 text-sm lg:text-base font-medium rounded-full border border-border bg-card/60 hover:bg-card text-foreground transition-all"
            >
              View Invoices
            </Link>
            <Link
              href="/liquid-glass-lab"
              className="inline-flex items-center justify-center gap-1.5 h-13 px-5 text-xs font-mono text-muted-foreground hover:text-foreground transition-all"
            >
              Material Lab →
            </Link>
          </div>
        </div>
      </div>

      {/* Stats marquee */}
      <div
        className={`w-full border-t border-b border-border/70 py-4 bg-muted/25 transition-all duration-700 delay-500 overflow-hidden ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="flex gap-14 marquee whitespace-nowrap">
          {[...Array(2)].map((_, loopIdx) => (
            <div key={loopIdx} className="flex gap-14 shrink-0">
              {stats.map((stat) => (
                <div
                  key={`${stat.badge}-${loopIdx}`}
                  className="flex items-baseline gap-3 shrink-0"
                >
                  <span className="text-3xl lg:text-4xl font-display font-semibold text-foreground">
                    {stat.value}
                  </span>
                  <div className="flex flex-col text-left">
                    <span className="text-xs text-muted-foreground">
                      {stat.label}
                    </span>
                    <span className="font-mono text-[10px] tracking-wider uppercase text-accent font-semibold">
                      {stat.badge}
                    </span>
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
