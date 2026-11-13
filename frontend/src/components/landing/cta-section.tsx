"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { AnimatedTetrahedron } from "./animated-tetrahedron";

export function CtaSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 50, y: 50 });

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.15 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <section
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div
          className={`relative rounded-3xl border border-border glass-surface overflow-hidden shadow-2xl transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          onMouseMove={handleMouseMove}
        >
          {/* Mouse Spotlight effect */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none transition-opacity duration-300"
            style={{
              background: `radial-gradient(600px circle at ${mousePosition.x}% ${mousePosition.y}%, rgba(189, 84, 53, 0.25), transparent 45%)`,
            }}
          />

          <div className="relative z-10 px-8 lg:px-16 py-16 lg:py-24">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-12">
              {/* Left content */}
              <div className="flex-1 max-w-2xl">
                <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-accent bg-accent/10 px-3 py-1 rounded-full mb-6">
                  <Sparkles className="w-3.5 h-3.5" />
                  Instant Workspace Access
                </div>

                <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-6 leading-[0.98] text-foreground">
                  Ready to transform your
                  <br />
                  invoice review workflow?
                </h2>

                <p className="text-base lg:text-lg text-muted-foreground mb-10 leading-relaxed">
                  Extract headers, items, and tax reconciliation data with
                  verifiable coordinate bounding boxes in seconds.
                </p>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                  <Link
                    href="/extract"
                    className="inline-flex items-center justify-center gap-2 bg-foreground hover:bg-foreground/90 text-background px-8 h-13 text-sm font-semibold rounded-full shadow-md group transition-all"
                  >
                    Launch Workstation
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                  <Link
                    href="/invoices"
                    className="inline-flex items-center justify-center gap-2 h-13 px-7 text-sm font-medium rounded-full border border-border bg-card/60 hover:bg-card text-foreground transition-all"
                  >
                    View Invoice Ledger
                  </Link>
                </div>

                <p className="text-xs text-muted-foreground mt-6 font-mono">
                  Private on-device local execution available · No cloud lock-in
                </p>
              </div>

              {/* Right animation */}
              <div className="hidden lg:flex items-center justify-center w-[460px] h-[460px] -mr-8">
                <AnimatedTetrahedron />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
