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
import { GlassButton } from "@/components/liquid-glass/GlassButton";
import { GlassSurface } from "@/components/liquid-glass/GlassSurface";
import "@/components/liquid-glass/workspace.css";
import { AlertBanner, ThemeToggle } from "@/components/ui";

const NAV_ITEMS = [
  { href: "/", label: "Extract", icon: UploadCloud },
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
      <div className="flex min-h-screen items-center justify-center bg-transparent px-4">
        <div className="glass-surface-elevated relative w-full max-w-md rounded-2xl p-8">
          <div className="absolute right-4 top-4">
            <ThemeToggle />
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br/20/20 text-stone-600 ring-1 ring-stone-500/20 dark:from-stone-500/25 dark:to-stone-500/25 dark:text-stone-300 dark:ring-stone-400/25">
            <Lock className="h-5 w-5" />
          </div>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-stone-900 dark:text-stone-100">
            Invoice Studio Demo Access
          </h1>
          <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400">
            Enter the deployment passcode to unlock extraction, review tools,
            and the invoice ledger.
          </p>

          <form onSubmit={handleUnlock} className="mt-6 space-y-4">
            {authError ? (
              <AlertBanner variant="error">{authError}</AlertBanner>
            ) : null}
            <div>
              <label
                htmlFor="demo-passcode"
                className="block text-xs font-medium uppercase tracking-wider text-stone-600 dark:text-stone-400"
              >
                Demo Passcode
              </label>
              <div className="relative mt-1.5">
                <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400 dark:text-stone-500" />
                <input
                  id="demo-passcode"
                  type="password"
                  required
                  autoFocus
                  value={passcodeInput}
                  onChange={(e) => setPasscodeInput(e.target.value)}
                  placeholder="Enter passcode..."
                  className="w-full rounded-xl border border-stone-200/80 bg-white/75 py-2.5 pl-9 pr-3 text-sm text-stone-900 backdrop-blur-md placeholder:text-stone-400 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-500/20 dark:border-white/15 dark:bg-stone-950/60 dark:text-stone-100 dark:placeholder:text-stone-500"
                />
              </div>
            </div>
            <GlassButton
              type="submit"
              disabled={unlocking || !passcodeInput}
              className="w-full rounded-xl action-primary px-4 py-2.5 text-sm font-semibold text-white shadow-md transition disabled:opacity-50"
            >
              {unlocking ? "Verifying..." : "Unlock Workspace"}
            </GlassButton>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-transparent text-stone-900 dark:text-stone-100">
      <header className="workspace-header">
        <div className="workspace-header-inner">
          <Link href="/" className="workspace-brand">
            <div className="workspace-mark" aria-hidden="true">i.</div>
            <div className="min-w-0 leading-tight">
              <span className="block text-sm font-semibold tracking-tight">invoflow</span>
              <span className="workspace-subtitle">Document intelligence</span>
            </div>
          </Link>
          <GlassSurface material="chrome" radius={999} className="workspace-navigation">
            <nav aria-label="Main navigation">
              {NAV_ITEMS.map((item) => {
                const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return <Link key={item.href} href={item.href} aria-current={isActive ? "page" : undefined} className="lg-control workspace-nav-link">
                  <Icon aria-hidden="true" className="h-4 w-4" /><span>{item.label}</span>
                </Link>;
              })}
            </nav>
          </GlassSurface>
          <div className="workspace-account">
            {health ? (
              <div
                className="workspace-health"
                title={`DB: ${health.database.connected ? "Connected" : "Offline"} | Local VLM: ${health.local_vlm.weights_present ? (health.local_vlm.loaded ? "Loaded on GPU" : "Ready (lazy)") : "Weights missing"} | Cloud default: ${health.cloud_default_configured ? "Configured" : "BYO Key"}`}
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    health.status === "ok" ? "bg-emerald-500" : "bg-amber-500",
                  )}
                />
                <Cpu className="h-3.5 w-3.5 text-stone-500 dark:text-stone-400" />
                <span className="font-medium">
                  {health.local_vlm.loaded
                    ? "Local VLM Loaded"
                    : health.local_vlm.weights_present
                      ? "Local VLM Ready"
                      : "Cloud / OCR"}
                </span>
                <span className="text-stone-400 dark:text-stone-500">·</span>
                <span className="text-stone-500 dark:text-stone-400">
                  {health.database.connected ? "DB OK" : "DB Issue"}
                </span>
              </div>
            ) : healthOffline ? (
              <GlassButton
                type="button"
                onClick={() => void loadHealth()}
                className="workspace-health lg-control"
                title="Click to retry backend health check"
              >
                <span className="h-2 w-2 rounded-full bg-rose-500" />
                Backend Offline
              </GlassButton>
            ) : null}

            <ThemeToggle />
            {auth.required && auth.authenticated ? (
              <GlassButton type="button" onClick={() => void handleLogout()} className="lg-control" aria-label="Lock workspace">
                <LogOut aria-hidden="true" className="h-3.5 w-3.5" /><span className="hidden sm:inline">Lock</span>
              </GlassButton>
            ) : null}
          </div>
        </div>
      </header>

      <main className="workspace-main">
        {children}
      </main>
    </div>
  );
}
