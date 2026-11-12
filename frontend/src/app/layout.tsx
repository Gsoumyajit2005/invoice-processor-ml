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
      <body className="min-h-full bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
