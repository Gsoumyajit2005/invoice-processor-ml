"use client";

import { Minus, Plus, Scan } from "lucide-react";
import { GlassSurface, type MaterialMode } from "./GlassSurface";
export type { MaterialMode } from "./GlassSurface";
import "./liquid-glass.css";


export function LiquidDocumentToolbar({ zoom, onZoom, mode }: {
  zoom: number; onZoom: (zoom: number) => void; mode: MaterialMode;
}) {
  return <GlassSurface className="optical-toolbar" radius={34} mode={mode} showEngine>
    <div className="optical-controls" role="group" aria-label="Document zoom">
      <span className="optical-page">Page 1 / 1</span>
      <span className="optical-divider" />
      <button type="button" aria-label="Zoom out" disabled={zoom <= 75} onClick={() => onZoom(zoom - 25)}><Minus aria-hidden="true" size={18} /></button>
      <span className="optical-zoom" aria-live="polite">{zoom}%</span>
      <button type="button" aria-label="Zoom in" disabled={zoom >= 200} onClick={() => onZoom(zoom + 25)}><Plus aria-hidden="true" size={18} /></button>
      <span className="optical-divider" />
      <button type="button" aria-label="Fit document" onClick={() => onZoom(100)}><Scan aria-hidden="true" size={18} /><span className="optical-fit">Fit</span></button>
    </div>
  </GlassSurface>;
}
