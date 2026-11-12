"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Cpu,
  FileSpreadsheet,
  FileText,
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
        <div className="glass-surface flex items-center gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300">
          <Activity className="h-4 w-4 animate-pulse text-indigo-600 dark:text-indigo-400" />
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
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 text-indigo-600 ring-1 ring-indigo-500/20 dark:from-indigo-500/25 dark:to-violet-500/25 dark:text-indigo-300 dark:ring-indigo-400/25">
            <Lock className="h-5 w-5" />
          </div>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Invoice Studio Demo Access
          </h1>
          <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400">
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
                className="block text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400"
              >
                Demo Passcode
              </label>
              <div className="relative mt-1.5">
                <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                <input
                  id="demo-passcode"
                  type="password"
                  required
                  autoFocus
                  value={passcodeInput}
                  onChange={(e) => setPasscodeInput(e.target.value)}
                  placeholder="Enter passcode..."
                  className="w-full rounded-xl border border-slate-200/80 bg-white/75 py-2.5 pl-9 pr-3 text-sm text-slate-900 backdrop-blur-md placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-white/15 dark:bg-slate-950/60 dark:text-slate-100 dark:placeholder:text-slate-500"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={unlocking || !passcodeInput}
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/25 transition hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50"
            >
              {unlocking ? "Verifying..." : "Unlock Workspace"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-transparent text-slate-900 dark:text-slate-100">
      <header className="sticky top-0 z-30 border-b border-white/60 bg-white/65 backdrop-blur-xl shadow-[0_4px_24px_-6px_rgba(15,23,42,0.06)] dark:border-white/10 dark:bg-slate-950/60 dark:shadow-[0_4px_24px_-6px_rgba(0,0,0,0.45)]">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/25 ring-1 ring-white/25">
                <FileText className="h-4 w-4" />
              </div>
              <div className="leading-tight">
                <span className="block text-sm font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                  Invoice Studio
                </span>
                <span className="hidden text-[11px] text-slate-500 dark:text-slate-400 sm:block">
                  Qwen3.5-0.8B VLM + Indra OCR
                </span>
              </div>
            </Link>

            <nav
              className="flex items-center gap-1"
              aria-label="Main navigation"
            >
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition",
                      isActive
                        ? "bg-indigo-500/12 text-indigo-700 ring-1 ring-inset ring-indigo-500/20 backdrop-blur-sm dark:bg-indigo-400/15 dark:text-indigo-200 dark:ring-indigo-400/25"
                        : "text-slate-600 hover:bg-white/60 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/8 dark:hover:text-white",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2.5">
            {health ? (
              <div
                className="hidden items-center gap-2 rounded-full border border-slate-200/80 bg-white/60 px-3 py-1 text-xs text-slate-700 backdrop-blur-md shadow-xs dark:border-white/12 dark:bg-white/6 dark:text-slate-200 md:inline-flex"
                title={`DB: ${health.database.connected ? "Connected" : "Offline"} | Local VLM: ${health.local_vlm.weights_present ? (health.local_vlm.loaded ? "Loaded on GPU" : "Ready (lazy)") : "Weights missing"} | Cloud default: ${health.cloud_default_configured ? "Configured" : "BYO Key"}`}
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    health.status === "ok" ? "bg-emerald-500" : "bg-amber-500",
                  )}
                />
                <Cpu className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400" />
                <span className="font-medium">
                  {health.local_vlm.loaded
                    ? "Local VLM Loaded"
                    : health.local_vlm.weights_present
                      ? "Local VLM Ready"
                      : "Cloud / OCR"}
                </span>
                <span className="text-slate-400 dark:text-slate-500">·</span>
                <span className="text-slate-500 dark:text-slate-400">
                  {health.database.connected ? "DB OK" : "DB Issue"}
                </span>
              </div>
            ) : healthOffline ? (
              <button
                type="button"
                onClick={() => void loadHealth()}
                className="hidden items-center gap-1.5 rounded-full border border-rose-200/80 bg-rose-50/75 px-3 py-1 text-xs font-medium text-rose-700 backdrop-blur-md dark:border-rose-500/30 dark:bg-rose-950/50 dark:text-rose-300 md:inline-flex"
                title="Click to retry backend health check"
              >
                <span className="h-2 w-2 rounded-full bg-rose-500" />
                Backend Offline
              </button>
            ) : null}

            <ThemeToggle />

            {auth.required && auth.authenticated ? (
              <button
                type="button"
                onClick={() => void handleLogout()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/70 px-2.5 py-1.5 text-xs font-medium text-slate-700 backdrop-blur-md hover:bg-white/90 dark:border-white/12 dark:bg-white/6 dark:text-slate-200 dark:hover:bg-white/12"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Lock</span>
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        {children}
      </main>
    </div>
  );
}
