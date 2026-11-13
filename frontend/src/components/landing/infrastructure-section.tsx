"use client";

import { useEffect, useState, useRef } from "react";
import { Cpu } from "lucide-react";

const nodes = [
  { name: "Local GPU Worker", role: "Qwen3.5-0.8B LoRA", status: "Operational", latency: "820ms" },
  { name: "Indra OCR Engine", role: "Coordinate Grounding", status: "Operational", latency: "240ms" },
  { name: "PostgreSQL Ledger", role: "ACID Persistence", status: "Connected", latency: "12ms" },
  { name: "Cloud Fallback Gateway", role: "LiteLLM Router", status: "Ready (BYO Key)", latency: "1.2s" },
  { name: "Session Auth Vault", role: "HMAC Signed Tokens", status: "Secure", latency: "<1ms" },
];

export function InfrastructureSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeNode, setActiveNode] = useState(0);
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

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveNode((prev) => (prev + 1) % nodes.length);
    }, 2400);
    return () => clearInterval(interval);
  }, []);

  return (
    <section
      id="architecture"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden border-t border-border"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Content */}
          <div
            className={`transition-all duration-700 ${
              isVisible
                ? "opacity-100 translate-x-0"
                : "opacity-0 -translate-x-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
              <span className="w-8 h-px bg-foreground/30" />
              Architecture & Privacy
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-6">
              Air-gapped privacy.
              <br />
              <span className="text-muted-foreground">Hybrid scalability.</span>
            </h2>
            <p className="text-lg text-muted-foreground leading-relaxed mb-10">
              Run multimodal extraction completely on-premise without a single
              byte leaving your private network. When cloud escalation is
              enabled, your own API keys are used with zero model training
              retention.
            </p>

            {/* Architecture Metrics */}
            <div className="grid grid-cols-3 gap-6 pt-4 border-t border-border">
              <div>
                <div className="text-3xl lg:text-4xl font-display font-semibold text-foreground mb-1">
                  &lt;1s
                </div>
                <div className="text-xs text-muted-foreground">
                  Local VLM Latency
                </div>
              </div>
              <div>
                <div className="text-3xl lg:text-4xl font-display font-semibold text-foreground mb-1">
                  100%
                </div>
                <div className="text-xs text-muted-foreground">
                  Data Sovereignty
                </div>
              </div>
              <div>
                <div className="text-3xl lg:text-4xl font-display font-semibold text-foreground mb-1">
                  0 KB
                </div>
                <div className="text-xs text-muted-foreground">
                  External Data Egress
                </div>
              </div>
            </div>
          </div>

          {/* Right: Operational Cluster Status */}
          <div
            className={`transition-all duration-700 delay-200 ${
              isVisible
                ? "opacity-100 translate-x-0"
                : "opacity-0 translate-x-8"
            }`}
          >
            <div className="glass-surface rounded-2xl overflow-hidden border border-border shadow-lg">
              {/* Header */}
              <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/40">
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-accent" />
                  Cluster Node Topology
                </span>
                <span className="flex items-center gap-2 text-xs font-mono text-emerald-600 dark:text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  System Healthy
                </span>
              </div>

              {/* Node List */}
              <div className="divide-y divide-border/60">
                {nodes.map((node, index) => (
                  <div
                    key={node.name}
                    className={`px-6 py-4.5 flex items-center justify-between transition-colors duration-200 ${
                      activeNode === index
                        ? "bg-muted/60"
                        : "hover:bg-muted/30"
                    }`}
                  >
                    <div>
                      <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                        {node.name}
                        {index === 0 ? (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/15 text-accent font-medium">
                            Primary
                          </span>
                        ) : null}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {node.role}
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                        {node.status}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        {node.latency}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
