"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/ui";

const navLinks = [
  { name: "Features", href: "#features" },
  { name: "Workflow", href: "#how-it-works" },
  { name: "Architecture", href: "#architecture" },
  { name: "Benchmarks", href: "#benchmarks" },
  { name: "API", href: "#developers" },
];

export function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`fixed z-50 transition-all duration-500 ${
        isScrolled ? "top-4 left-4 right-4" : "top-0 left-0 right-0"
      }`}
    >
      <nav
        aria-label="Landing Navigation"
        className={`mx-auto transition-all duration-500 ${
          isScrolled || isMobileMenuOpen
            ? "glass-surface rounded-2xl shadow-lg max-w-[1200px]"
            : "bg-transparent max-w-[1400px]"
        }`}
      >
        <div
          className={`flex items-center justify-between transition-all duration-500 px-6 lg:px-8 ${
            isScrolled ? "h-14" : "h-20"
          }`}
        >
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div
              className="w-7 h-7 rounded-lg bg-foreground text-background flex items-center justify-center font-bold text-xs tracking-tighter"
              aria-hidden="true"
            >
              i.
            </div>
            <div className="leading-none">
              <span className="font-display font-semibold text-lg lg:text-xl tracking-tight text-foreground">
                InvoFlow
              </span>
              <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground ml-1.5">
                AI
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-8 lg:gap-10">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-200 relative group"
              >
                {link.name}
                <span className="absolute -bottom-1 left-0 w-0 h-px bg-foreground transition-all duration-200 group-hover:w-full" />
              </a>
            ))}
          </div>

          {/* Desktop Controls & CTA */}
          <div className="hidden lg:flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/invoices"
              className="text-sm font-medium text-muted-foreground hover:text-foreground px-3 py-1.5 transition-colors"
            >
              Ledger
            </Link>
            <Link
              href="/extract"
              className={`inline-flex items-center gap-1.5 bg-foreground hover:bg-foreground/90 text-background font-semibold rounded-full shadow-sm transition-all duration-300 ${
                isScrolled ? "h-8 px-4 text-xs" : "h-10 px-5 text-sm"
              }`}
            >
              Launch Workspace
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex lg:hidden items-center gap-2">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-foreground rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Drawer Overlay */}
      {isMobileMenuOpen ? (
        <div className="lg:hidden fixed inset-0 top-[72px] bg-background/95 backdrop-blur-xl z-40 p-6 flex flex-col justify-between border-t border-border animate-in fade-in duration-200">
          <div className="flex flex-col gap-5 pt-4">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-lg font-medium text-foreground hover:text-accent transition-colors"
              >
                {link.name}
              </a>
            ))}
          </div>
          <div className="flex flex-col gap-3 pb-8">
            <Link
              href="/invoices"
              onClick={() => setIsMobileMenuOpen(false)}
              className="w-full text-center py-3 rounded-xl border border-border text-foreground font-medium text-sm"
            >
              View Invoice Ledger
            </Link>
            <Link
              href="/extract"
              onClick={() => setIsMobileMenuOpen(false)}
              className="w-full text-center py-3.5 rounded-xl bg-foreground text-background font-semibold text-sm shadow-md"
            >
              Launch Workspace
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}
