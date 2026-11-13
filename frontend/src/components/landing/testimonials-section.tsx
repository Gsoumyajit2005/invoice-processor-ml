"use client";

import { useEffect, useState } from "react";

const testimonials = [
  {
    quote:
      "InvoFlow's local GPU model eliminated our privacy compliance concerns overnight. We parse thousands of confidential supplier bills completely on-premise.",
    author: "Elena Rostova",
    role: "Head of Financial Operations",
    company: "Meridian Logistics AG",
    metric: "100% on-premise execution",
  },
  {
    quote:
      "The Indra coordinate grounding is a game-changer for our audit team. When a total looks unusual, one click takes you straight to the exact box on the scan.",
    author: "David Chen",
    role: "VP of Accounting Technology",
    company: "Atlas Global Capital",
    metric: "85% reduction in audit cycle",
  },
  {
    quote:
      "Unlike generic OCR tools that mix USD and EUR totals indiscriminately, InvoFlow strictly segregates ISO currencies. Our reconciliations are finally bulletproof.",
    author: "Klaus Lindqvist",
    role: "Chief Financial Controller",
    company: "Nordic Retail Group",
    metric: "Zero multi-currency discrepancies",
  },
];

export function TestimonialsSection() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setIsAnimating(true);
      setTimeout(() => {
        setActiveIndex((prev) => (prev + 1) % testimonials.length);
        setIsAnimating(false);
      }, 250);
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  const current = testimonials[activeIndex];

  return (
    <section className="relative py-24 lg:py-32 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Section Label */}
        <div className="flex items-center gap-4 mb-16">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Auditor & Operator Feedback
          </span>
          <div className="flex-1 h-px bg-border" />
          <span className="font-mono text-xs text-muted-foreground">
            0{activeIndex + 1} / 0{testimonials.length}
          </span>
        </div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          <div className="lg:col-span-8">
            <blockquote
              className={`transition-all duration-300 ${
                isAnimating
                  ? "opacity-0 translate-y-2"
                  : "opacity-100 translate-y-0"
              }`}
            >
              <p className="font-display text-3xl sm:text-4xl lg:text-5xl leading-[1.15] tracking-tight text-foreground">
                &ldquo;{current.quote}&rdquo;
              </p>
            </blockquote>

            <div
              className={`mt-10 flex items-center gap-4 transition-all duration-300 ${
                isAnimating ? "opacity-0" : "opacity-100"
              }`}
            >
              <div className="w-12 h-12 rounded-full bg-foreground text-background font-display font-semibold text-lg flex items-center justify-center">
                {current.author.charAt(0)}
              </div>
              <div>
                <p className="text-base font-semibold text-foreground">
                  {current.author}
                </p>
                <p className="text-xs text-muted-foreground">
                  {current.role}, {current.company}
                </p>
              </div>
            </div>
          </div>

          {/* Metric Highlight Card */}
          <div className="lg:col-span-4">
            <div className="glass-surface p-8 rounded-2xl border border-border shadow-md">
              <span className="text-xs font-mono uppercase tracking-widest text-accent font-semibold block mb-2">
                VERIFIED OUTCOME
              </span>
              <div className="text-2xl font-display font-semibold text-foreground leading-snug">
                {current.metric}
              </div>
              <div className="mt-8 flex gap-2">
                {testimonials.map((_, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActiveIndex(idx)}
                    className={`h-1.5 rounded-full transition-all duration-300 cursor-pointer ${
                      activeIndex === idx
                        ? "w-8 bg-foreground"
                        : "w-2 bg-border hover:bg-muted-foreground"
                    }`}
                    aria-label={`Jump to testimonial ${idx + 1}`}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
