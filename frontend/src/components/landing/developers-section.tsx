"use client";

import { useState, useEffect, useRef } from "react";
import { Copy, Check, Terminal } from "lucide-react";

const codeExamples = [
  {
    label: "Python (FastAPI)",
    code: `import requests

url = "http://localhost:8000/api/v1/extract"
files = {"file": open("invoice-scan.pdf", "rb")}
data = {"mode": "auto"}  # "local" GPU first, cloud escalation fallback

response = requests.post(url, files=files, data=data)
extraction = response.json()

print(f"Vendor: {extraction['vendor_name']}")
print(f"Total: {extraction['total_amount']} {extraction['currency']}")
for item in extraction['line_items']:
    print(f" - {item['description']}: {item['total_price']}")`,
  },
  {
    label: "cURL",
    code: `# Process invoice with local Qwen3.5-0.8B LoRA + Indra OCR
curl -X POST "http://localhost:8000/api/v1/extract" \\
  -H "Accept: application/json" \\
  -F "file=@invoice-eur-english.png" \\
  -F "mode=local"`,
  },
  {
    label: "TypeScript / Node",
    code: `import { extractSingle } from "@/lib/api-client";

const formData = new FormData();
formData.append("file", fileBlob, "receipt.jpg");
formData.append("mode", "auto");

const invoice = await extractSingle(formData);
console.log("Extracted ID:", invoice.id);
console.log("Tax Grounding:", invoice.tax_amount_bbox);`,
  },
];

const developerHighlights = [
  {
    title: "FastAPI REST Contract",
    description: "Predictable JSON schemas and OpenAPI 3.1 documentation.",
  },
  {
    title: "Normalized Coordinates",
    description: "Boxes standardized to [0..1000] for responsive overlays.",
  },
  {
    title: "Multi-Currency Safety",
    description: "ISO 4217 validation prevents mixing incompatible currencies.",
  },
  {
    title: "PostgreSQL & Supabase",
    description: "Production SQL schema with soft deletes and audit columns.",
  },
];

export function DevelopersSection() {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeExamples[activeTab].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
      id="developers"
      ref={sectionRef}
      className="relative py-24 lg:py-32 border-b border-border overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div
          className={`max-w-3xl mb-16 lg:mb-20 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
            <span className="w-8 h-px bg-foreground/30" />
            Developer Integration
          </span>
          <h2 className="text-4xl lg:text-6xl font-display tracking-tight text-foreground mb-4">
            Built for automated
            <br />
            financial pipelines.
          </h2>
          <p className="text-base lg:text-lg text-muted-foreground">
            Integrate InvoFlow into accounting bots, ERP ingestion workers, and
            AP queues with a clean REST API.
          </p>
        </div>

        {/* Code Tabs & Highlights */}
        <div className="grid lg:grid-cols-12 gap-10 lg:gap-14 items-start">
          {/* Code Viewer */}
          <div className="lg:col-span-8 rounded-2xl border border-border glass-surface overflow-hidden shadow-lg">
            {/* Header / Tabs */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-accent" />
                <div className="flex gap-1.5 ml-2">
                  {codeExamples.map((item, idx) => (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => setActiveTab(idx)}
                      className={`px-3 py-1.5 text-xs font-mono rounded-lg transition-colors cursor-pointer ${
                        activeTab === idx
                          ? "bg-foreground text-background font-semibold"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground px-2.5 py-1 rounded-md border border-border hover:bg-card transition-colors cursor-pointer"
                aria-label="Copy code snippet"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>

            {/* Code Body */}
            <div className="p-6 bg-card/60 overflow-x-auto">
              <pre className="font-mono text-xs lg:text-sm text-foreground leading-relaxed whitespace-pre">
                <code>{codeExamples[activeTab].code}</code>
              </pre>
            </div>
          </div>

          {/* Highlights */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            {developerHighlights.map((hl) => (
              <div
                key={hl.title}
                className="p-5 rounded-2xl border border-border/80 glass-subtle"
              >
                <h3 className="text-sm font-semibold text-foreground mb-1">
                  {hl.title}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {hl.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
