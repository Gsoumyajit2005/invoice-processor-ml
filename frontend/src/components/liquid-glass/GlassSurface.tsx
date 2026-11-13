"use client";

import { createContext, useContext, useId, useRef, type CSSProperties, type HTMLAttributes } from "react";
import { useGlassCapabilities } from "./capabilities";
import { useGlassLighting } from "./use-glass-lighting";
import { useGlassTactile } from "./use-glass-tactile";
import { useDisplacementMap } from "./use-displacement-map";
import "./liquid-glass.css";

export type MaterialMode = "auto" | "frost" | "solid" | "plain";
const InGlass = createContext(false);
export function useInsideGlass() { return useContext(InGlass); }

export interface GlassSurfaceProps extends HTMLAttributes<HTMLDivElement> {
  material?: "lens" | "chrome" | "panel";
  radius?: number;
  /** Lab comparisons only. Production surfaces use automatic browser/accessibility policy. */
  mode?: MaterialMode;
  showEngine?: boolean;
}
export function GlassSurface({ children, className = "", material = "lens", radius = 24, mode = "auto", showEngine = false, style, ...props }: GlassSurfaceProps) {
  const id = `invoice-lens-${useId().replace(/:/g, "")}`;
  const host = useRef<HTMLDivElement>(null), pane = useRef<HTMLDivElement>(null), map = useRef<SVGFEImageElement>(null);
  const nested = useContext(InGlass);
  const capability = useGlassCapabilities();
  const requested = capability.engine === "solid" || nested ? "solid" : mode === "auto" ? capability.engine : mode;
  const engine = material === "panel" && requested === "refraction" ? "frost" : requested;
  const strength = material === "chrome" ? .55 : 1;
  const refract = engine === "refraction" && material !== "panel";
  useDisplacementMap(host, pane, map, id, refract, radius, strength);
  const lighting = useGlassLighting<HTMLDivElement>();
  const tactile = useGlassTactile<HTMLDivElement>();
  const label = refract ? "Chromium · edge refraction" : engine === "solid" ? "Opaque material" : engine === "plain" ? "Refraction off · comparison" : "Frost fallback · no refraction";
  return <div {...props}
    onPointerMove={event => { props.onPointerMove?.(event); if (!event.defaultPrevented) lighting.onPointerMove(event); }}
    onPointerDown={event => { props.onPointerDown?.(event); if (!event.defaultPrevented) tactile.onPointerDown(event); }}
    onKeyDown={event => { props.onKeyDown?.(event); if (!event.defaultPrevented) tactile.onKeyDown(event); }}
    onKeyUp={event => { props.onKeyUp?.(event); tactile.onKeyUp(event); }}
    onBlur={event => { props.onBlur?.(event); tactile.onBlur(event); }} ref={host} className={`lg-surface ${className}`} data-engine={engine} data-material={material} style={{ "--lg-radius": `${radius}px`, ...style } as CSSProperties}>
    {refract ? <svg width="0" height="0" className="optical-defs" aria-hidden="true"><defs>
      <filter id={id} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feImage ref={map} width="100%" height="100%" preserveAspectRatio="none" result="packed" />
        <feColorMatrix in="packed" type="matrix" values="1 0 0 0 0  0 0 0 2 -1  0 0 0 0 0  0 0 0 0 1" result="vectors" />
        <feDisplacementMap in="SourceGraphic" in2="vectors" scale={96 * strength} xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs></svg> : null}
    <div className="optical-pane" ref={pane} aria-hidden="true" />
    <div className="optical-rim" aria-hidden="true" />
    <div className="optical-sheen" aria-hidden="true" />
    <InGlass value={true}><div className="lg-body">{children}</div></InGlass>
    {showEngine ? <output className="optical-engine" aria-live="polite">{label}</output> : null}
  </div>;
}
