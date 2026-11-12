import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Invoice Studio — Hybrid Document AI & HITL Workbench",
  description:
    "Structured invoice & receipt extraction powered by fine-tuned Qwen3.5-0.8B VLM, Indra OCR 1.1 coordinate grounding, and PostgreSQL human-in-the-loop review.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="relative min-h-full bg-[#eef2f7] text-slate-900 transition-colors duration-200 dark:bg-[#030712] dark:text-slate-100">
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
        >
          <div className="absolute -left-32 -top-28 h-[34rem] w-[34rem] rounded-full bg-indigo-400/25 blur-[110px] dark:bg-indigo-600/25" />
          <div className="absolute -right-24 top-10 h-[30rem] w-[30rem] rounded-full bg-sky-300/35 blur-[110px] dark:bg-cyan-500/15" />
          <div className="absolute -bottom-36 left-1/3 h-[34rem] w-[34rem] rounded-full bg-violet-300/25 blur-[120px] dark:bg-fuchsia-600/15" />
        </div>
        <div className="relative z-10 min-h-full">
          <AppShell>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
