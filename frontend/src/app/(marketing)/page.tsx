import { Navigation } from "@/components/landing/navigation";
import { HeroSection } from "@/components/landing/hero-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { InfrastructureSection } from "@/components/landing/infrastructure-section";
import { MetricsSection } from "@/components/landing/metrics-section";
import { IntegrationsSection } from "@/components/landing/integrations-section";
import { SecuritySection } from "@/components/landing/security-section";
import { DevelopersSection } from "@/components/landing/developers-section";
import { BenchmarksSection } from "@/components/landing/benchmarks-section";
import { DeploymentSection } from "@/components/landing/deployment-section";
import { CtaSection } from "@/components/landing/cta-section";
import { FooterSection } from "@/components/landing/footer-section";

export const metadata = {
  title: "InvoFlow AI — Multimodal Financial Document Intelligence",
  description:
    "Structured invoice & receipt extraction powered by fine-tuned Qwen3.5-0.8B VLM, Indra OCR 1.1 coordinate grounding, and PostgreSQL human-in-the-loop review.",
};

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-x-hidden noise-overlay">
      <Navigation />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <InfrastructureSection />
      <MetricsSection />
      <IntegrationsSection />
      <SecuritySection />
      <DevelopersSection />
      <BenchmarksSection />
      <DeploymentSection />
      <CtaSection />
      <FooterSection />
    </main>
  );
}
