"use client";
import { useRef, useState } from "react";
import { LiquidDocumentToolbar, type MaterialMode } from "@/components/liquid-glass/LiquidDocumentToolbar";
import "./prototype.css";


export function LiquidGlassLab() {
  const [zoom, setZoom] = useState(100);
  const [mode, setMode] = useState<MaterialMode>("auto");
  const [position, setPosition] = useState(0);
  const scroller = useRef<HTMLDivElement>(null);
  return <section className="lens-lab-lab" aria-labelledby="material-title">
    <a className="lens-lab-skip" href="#document-study">Skip to document</a>
    <header className="lens-lab-heading">
      <div><h1 id="material-title">A lens above the page.</h1><p>One floating toolbar. Live document refraction, a light that follows your hand.</p></div>
      <span className="lens-lab-badge">Isolated material study</span>
    </header>
    <div className="lens-lab-settings">
      <label>Material<select value={mode} onChange={e => setMode(e.target.value as MaterialMode)}>
        <option value="auto">Automatic refraction</option><option value="plain">Refraction off (compare)</option><option value="frost">Safari / Firefox fallback</option><option value="solid">Opaque fallback</option>
      </select></label>
      <label className="lens-lab-range">Move document under glass<input type="range" min="0" max="100" value={position} onChange={e => {
        const value = Number(e.target.value); setPosition(value);
        const node = scroller.current;
        if (node) node.scrollTop = value / 100 * (node.scrollHeight - node.clientHeight);
      }} /></label>
      <p>Hover the rim. Hold a button. Scroll the page.</p>
    </div>
    <div className="lens-lab-stage" id="document-study">
      <div className="lens-lab-document" ref={scroller} tabIndex={0} role="region" aria-label="Sample invoice document, scroll to inspect refraction" onScroll={e => {
        const node = e.currentTarget;
        setPosition(Math.round(node.scrollTop / Math.max(1, node.scrollHeight - node.clientHeight) * 100));
      }}>
        <div className="lens-lab-paper" style={{ width: `${zoom}%` }}>
          {/* Existing repository sample; preserve its original aspect ratio. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/material-lab/invoice-eur-english.png" width="1206" height="1706" alt="Repository sample invoice SRV-1895. Sample Company Ltd to Demo Services GmbH; original document image." />
        </div>
      </div>
      <div className="lens-lab-floating"><LiquidDocumentToolbar zoom={zoom} onZoom={setZoom} mode={mode} /></div>
    </div>
    <footer className="lens-lab-notes"><p>Source: checked-in invoice-eur-english.png. This study makes no extraction or financial changes.</p><p>Chromium enhances the curved edge with live displacement. Other browsers retain the rim, lighting and tactile controls with a deliberate frost fallback.</p></footer>
  </section>;
}
