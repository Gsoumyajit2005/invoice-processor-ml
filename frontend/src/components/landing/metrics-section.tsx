"use client";

import { useEffect, useState, useRef } from "react";

function AnimatedCounter({
  end,
  suffix = "",
  prefix = "",
}: {
  end: number;
  suffix?: string;
  prefix?: string;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          const duration = 1800;
          const startTime = performance.now();

          const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * end));

            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };

          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.3 }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, hasAnimated]);

  return (
    <div
      ref={ref}
      className="text-5xl lg:text-7xl font-display font-semibold tracking-tight text-foreground"
    >
      {prefix}
      {count.toLocaleString()}
      {suffix}
    </div>
  );
}

const metrics = [
  {
    value: 100,
    suffix: "%",
    prefix: "",
    label: "CORD Total & Tax Accuracy",
    meta: "79.3% → 100% with LoRA Adapter",
  },
  {
    value: 75,
    suffix: "%",
    prefix: "-",
    label: "Extraction failure reduction",
    meta: "16 failures down to 4 across 72 docs",
  },
  {
    value: 240,
    suffix: "ms",
    prefix: "",
    label: "Indra OCR coordinate latency",
    meta: "Normalized [0..1000] CPU Engine",
  },
  {
    value: 52,
    suffix: " steps",
    prefix: "",
    label: "LoRA training convergence",
    meta: "Loss: 0.168 → 0.0249 (RTX 3050 6GB)",
  },
];

export function MetricsSection() {
  const [time, setTime] = useState<string>("");
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const updateTime = () => {
      setTime(new Date().toUTCString().slice(17, 25) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative py-24 lg:py-32 border-y border-border bg-muted/20"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-16 lg:mb-20">
          <div>
            <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-3">
              <span className="w-8 h-px bg-foreground/30" />
              Operational Benchmarks
            </span>
            <h2 className="text-3xl lg:text-5xl font-display tracking-tight text-foreground">
              Production performance at scale.
            </h2>
          </div>
          <div className="font-mono text-xs text-muted-foreground flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Telemetry clock:</span>
            <span className="text-foreground font-semibold">
              {time || "SYNCHRONIZING..."}
            </span>
          </div>
        </div>

        {/* Counter Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-10">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="glass-surface p-6 lg:p-8 rounded-2xl border border-border flex flex-col justify-between"
            >
              <AnimatedCounter
                end={metric.value}
                prefix={metric.prefix}
                suffix={metric.suffix}
              />
              <div className="mt-4 pt-4 border-t border-border/80">
                <div className="text-sm font-semibold text-foreground">
                  {metric.label}
                </div>
                <div className="text-xs font-mono text-muted-foreground mt-1">
                  {metric.meta}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
