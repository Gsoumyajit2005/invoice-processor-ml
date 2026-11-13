import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";
import "./design-tokens.css";
import "./workstation.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "InvoFlow — Document workstation",
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
      <body className="app-canvas">
        <div className="relative z-10 min-h-full">
          <AppShell>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
