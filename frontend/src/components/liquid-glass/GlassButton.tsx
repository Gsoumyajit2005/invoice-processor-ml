"use client";

import type { ButtonHTMLAttributes, Ref } from "react";
import { useGlassLighting } from "./use-glass-lighting";
import { useGlassTactile } from "./use-glass-tactile";
import { useInsideGlass } from "./GlassSurface";
import "./liquid-glass.css";

export function GlassButton({ className = "", tone = "neutral", ref, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "neutral" | "primary" | "danger"; ref?: Ref<HTMLButtonElement> }) {
  const inside = useInsideGlass();
  const lighting = useGlassLighting<HTMLButtonElement>();
  const tactile = useGlassTactile<HTMLButtonElement>();
  return <button ref={ref} type="button" {...(!inside ? { ...lighting, ...tactile } : {})} {...props} className={`lg-control lg-button ${className}`} data-tone={tone} />;
}
