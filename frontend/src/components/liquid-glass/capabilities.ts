"use client";

import { useSyncExternalStore } from "react";

const queries = ["(prefers-reduced-motion: reduce)", "(prefers-reduced-transparency: reduce)", "(prefers-contrast: more)", "(forced-colors: active)"];
const listeners = new Set<() => void>();
let media: MediaQueryList[] = [];
function changed() { listeners.forEach(listener => listener()); }
function subscribe(listener: () => void) {
  if (!listeners.size) {
    media = queries.map(query => matchMedia(query));
    media.forEach(query => query.addEventListener("change", changed));
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (!listeners.size) { media.forEach(query => query.removeEventListener("change", changed)); media = []; }
  };
}
function snapshot() {
  const prefs = media.length ? media : queries.map(query => matchMedia(query));
  const opaque = prefs.slice(1).some(query => query.matches);
  // CSS.supports(url()) alone is insufficient: Safari/Firefox accept syntax
  // without rendering SVG backdrop displacement. Never gate ordinary blur on it.
  const chromium = "userAgentData" in navigator || /Chrome|Chromium|Edg\//.test(navigator.userAgent);
  const blur = CSS.supports("backdrop-filter", "blur(1px)") || CSS.supports("-webkit-backdrop-filter", "blur(1px)");
  return `${opaque || !blur ? "solid" : chromium ? "refraction" : "frost"}:${prefs[0].matches ? "still" : "motion"}`;
}
export function useGlassCapabilities() {
  const value = useSyncExternalStore(subscribe, snapshot, () => "frost:still");
  return { engine: value.split(":")[0] as "solid" | "refraction" | "frost", reducedMotion: value.endsWith(":still") };
}
