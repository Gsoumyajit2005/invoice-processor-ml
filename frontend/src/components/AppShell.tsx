"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Cpu,
  FileSpreadsheet,
  KeyRound,
  Layers,
  Lock,
  LogOut,
  UploadCloud,
} from "lucide-react";
import {
  ApiError,
  getAuthStatus,
  getHealth,
  logoutPasscode,
  submitPasscode,
} from "@/lib/api-client";
import { cn } from "@/lib/format";
import type { AuthStatusResponse, HealthResponse } from "@/lib/types";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import "@/components/liquid-glass/workspace.css";
import { AlertBanner, ThemeToggle } from "@/components/ui";

const NAV_ITEMS = [
  { href: "/extract", label: "Extract", icon: UploadCloud },
  { href: "/invoices", label: "Invoices", icon: FileSpreadsheet },
  { href: "/batch", label: "Batch Summary", icon: Layers },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [auth, setAuth] = useState<AuthStatusResponse | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [passcodeInput, setPasscodeInput] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthOffline, setHealthOffline] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const y = window.scrollY;
      if (y > 45) {
        setIsScrolled(true);
      } else if (y <= 25) {
        setIsScrolled(false);
      }
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [pathname]);

  const loadHealth = useCallback(async () => {
    try {
      const data = await getHealth();
      setHealth(data);
      setHealthOffline(false);
    } catch {
      setHealth(null);
      setHealthOffline(true);
    }
  }, []);

  useEffect(() => {
    let active = true;
    getAuthStatus()
      .then((status) => {
        if (!active) return;
        setAuth(status);
        if (!status.required || status.authenticated) {
          void getHealth()
            .then((h) => {
              if (!active) return;
              setHealth(h);
              setHealthOffline(false);
            })
            .catch(() => {
              if (!active) return;
              setHealth(null);
              setHealthOffline(true);
            });
        }
      })
      .catch(() => {
        if (!active) return;
        setAuth({ required: false, authenticated: true });
        void getHealth()
          .then((h) => {
            if (!active) return;
            setHealth(h);
            setHealthOffline(false);
          })
          .catch(() => {
            if (!active) return;
            setHealth(null);
            setHealthOffline(true);
          });
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setAuth({ required: true, authenticated: false });
    };
    window.addEventListener("invproc:unauthorized", onUnauthorized);
    return () => {
      window.removeEventListener("invproc:unauthorized", onUnauthorized);
    };
  }, []);

  const handleUnlock = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthError(null);
    setUnlocking(true);
    try {
      const res = await submitPasscode(passcodeInput);
      setAuth({ required: res.required, authenticated: res.authenticated });
      setPasscodeInput("");
      await loadHealth();
    } catch (error) {
      if (error instanceof ApiError) {
        setAuthError(error.detail);
      } else {
        setAuthError("Failed to verify passcode.");
      }
    } finally {
      setUnlocking(false);
    }
  };

  const handleLogout = async () => {
    await logoutPasscode();
    setAuth({ required: true, authenticated: false });
    setHealth(null);
  };

  if (auth === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-transparent">
        <div className="glass-surface flex items-center gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-300">
          <Activity className="h-4 w-4 animate-pulse text-stone-600 dark:text-stone-400" />
          Initializing workspace...
        </div>
      </div>
    );
  }

  if (auth.required && !auth.authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-transparent px-4 noise-overlay">
        <div className="glass-surface-elevated relative w-full max-w-md rounded-2xl p-8 border border-border shadow-xl">
          <div className="absolute right-4 top-4">
            <ThemeToggle />
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent/10 text-accent ring-1 ring-accent/20">
            <Lock className="h-5 w-5" />
          </div>
          <div className="mt-4">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground block mb-1">
              AUTHENTICATION REQUIRED
            </span>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
              InvoFlow Studio Access
            </h1>
          </div>
          <p className="mt-1.5 text-xs lg:text-sm text-muted-foreground leading-relaxed">
            Enter the deployment passcode to unlock multimodal extraction, review tools,
            and the invoice ledger.
          </p>

          <form onSubmit={handleUnlock} className="mt-6 space-y-4">
            {authError ? (
              <AlertBanner variant="error">{authError}</AlertBanner>
            ) : null}
            <div>
              <label
                htmlFor="demo-passcode"
                className="block text-xs font-mono uppercase tracking-wider text-muted-foreground"
              >
                Demo Passcode
              </label>
              <div className="relative mt-1.5">
                <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="demo-passcode"
                  type="password"
                  required
                  autoFocus
                  value={passcodeInput}
                  onChange={(e) => setPasscodeInput(e.target.value)}
                  placeholder="Enter passcode..."
                  className="w-full rounded-xl border border-border bg-card/80 py-2.5 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={unlocking || !passcodeInput}
              className="w-full rounded-full bg-foreground hover:bg-foreground/90 px-4 py-2.5 text-sm font-semibold text-background shadow-md transition-all disabled:opacity-50 cursor-pointer"
            >
              {unlocking ? "Verifying..." : "Unlock Workspace"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-transparent text-foreground">
      <header className={cn("workspace-header", isScrolled && "is-scrolled")}>
        <div className="workspace-header-inner">
          <Link
            href="/"
            className="workspace-brand flex items-center gap-2.5 group shrink-0"
            title="Return to InvoFlow landing page"
          >
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

          <div className="workspace-navigation-cluster">
            {/* Mobile Side Button: InvoFlow AI */}
            <div
              className={cn(
                "mobile-nav-side-btn mobile-nav-side-brand",
                isScrolled && "is-active",
              )}
              aria-hidden={!isScrolled}
            >
              <Link
                href="/"
                tabIndex={isScrolled ? 0 : -1}
                className="mobile-side-icon-btn lg-control lg-button flex items-center justify-center rounded-full shrink-0 shadow-xs"
                title="Return to InvoFlow landing page"
                aria-label="InvoFlow AI Home"
              >
                <div
                  className="w-5 h-5 rounded-md bg-foreground text-background flex items-center justify-center font-bold text-[10px] tracking-tighter shrink-0"
                  aria-hidden="true"
                >
                  i.
                </div>
              </Link>
            </div>

            <GlassSurface material="chrome" radius={999} className="workspace-navigation">
              <nav aria-label="Main navigation">
                {NAV_ITEMS.map((item) => {
                  const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={isActive ? "page" : undefined}
                      className="lg-control workspace-nav-link"
                    >
                      <Icon aria-hidden="true" className="h-4 w-4" />
                      <span>
                        {item.label === "Batch Summary" ? (
                          <>
                            <span className="hidden sm:inline">Batch Summary</span>
                            <span className="sm:hidden">Batch</span>
                          </>
                        ) : (
                          item.label
                        )}
                      </span>
                    </Link>
                  );
                })}
              </nav>
            </GlassSurface>

            {/* Mobile Side Button: Dark Mode Toggle */}
            <div
              className={cn(
                "mobile-nav-side-btn mobile-nav-side-theme",
                isScrolled && "is-active",
              )}
              aria-hidden={!isScrolled}
            >
              <div tabIndex={isScrolled ? 0 : -1} className="flex items-center justify-center shrink-0">
                <ThemeToggle className="mobile-side-icon-btn flex items-center justify-center rounded-full shrink-0 shadow-xs" />
              </div>
            </div>
          </div>

          <div className="workspace-account">
            {health ? (
              <div
                className="workspace-health inline-flex items-center gap-2 text-xs font-mono text-muted-foreground bg-muted/60 px-3.5 py-1.5 rounded-full border border-border shadow-2xs"
                title={`DB: ${health.database.connected ? "Connected" : "Offline"} | Local VLM: ${health.local_vlm.weights_present ? (health.local_vlm.loaded ? "Loaded on GPU" : "Ready (lazy)") : "Weights missing"} | Cloud default: ${health.cloud_default_configured ? "Configured" : "BYO Key"}`}
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full shrink-0",
                    health.status === "ok" ? "bg-emerald-500" : "bg-amber-500",
                  )}
                />
                <Cpu className="h-3.5 w-3.5 text-accent shrink-0" />
                <span className="font-medium text-foreground">
                  {health.local_vlm.loaded
                    ? "Local VLM Loaded"
                    : health.local_vlm.weights_present
                      ? "Local VLM Ready"
                      : "Cloud / OCR"}
                </span>
                <span>·</span>
                <span>
                  {health.database.connected ? "DB OK" : "DB Issue"}
                </span>
              </div>
            ) : healthOffline ? (
              <button
                type="button"
                onClick={() => void loadHealth()}
                className="inline-flex items-center gap-2 text-xs font-mono text-rose-600 dark:text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-full border border-rose-500/20 cursor-pointer"
                title="Click to retry backend health check"
              >
                <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                Backend Offline
              </button>
            ) : null}

            <ThemeToggle />
            {auth.required && auth.authenticated ? (
              <button
                type="button"
                onClick={() => void handleLogout()}
                className="inline-flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-full border border-border bg-card/60 hover:bg-card transition-colors cursor-pointer"
                aria-label="Lock workspace"
              >
                <LogOut aria-hidden="true" className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Lock</span>
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="workspace-main noise-overlay">
        {children}
      </main>
    </div>
  );
}
