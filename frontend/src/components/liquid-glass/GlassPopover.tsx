"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { GlassSurface } from "./GlassSurface";
import { GlassButton } from "./GlassButton";
import "./overlays.css";

const subscribe = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;

/** Native light-dismiss popover, with a positioned nonmodal fallback for older engines. */
export function GlassPopover({ label, trigger, children, onOpen }: { label: string; trigger: ReactNode; children: ReactNode; onOpen?: () => void }) {
  const id = `glass-popover-${useId().replace(/:/g, "")}`;
  const mounted = useSyncExternalStore(subscribe, clientSnapshot, serverSnapshot);
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  function close() {
    panel.current?.hidePopover?.();
    setOpen(false);
    button.current?.focus();
  }
  useLayoutEffect(() => {
    if (!open) return;
    function position() {
      const node = panel.current, anchor = button.current;
      if (!node || !anchor) return;
      const rect = anchor.getBoundingClientRect();
      const width = Math.min(320, innerWidth - 24), height = node.offsetHeight;
      const left = Math.max(12, Math.min(innerWidth - width - 12, rect.right - width));
      const top = rect.bottom + height + 8 > innerHeight - 12 ? Math.max(12, rect.top - height - 8) : rect.bottom + 8;
      node.style.left = `${left}px`; node.style.top = `${top}px`;
    }
    position();
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, { capture: true, passive: true });
    return () => { window.removeEventListener("resize", position); window.removeEventListener("scroll", position, true); };
  }, [open]);
  useEffect(() => {
    if (!open || "showPopover" in HTMLElement.prototype) return;
    const dismiss = (event: PointerEvent) => { if (!panel.current?.contains(event.target as Node) && !button.current?.contains(event.target as Node)) setOpen(false); };
    window.addEventListener("pointerdown", dismiss);
    return () => window.removeEventListener("pointerdown", dismiss);
  }, [open]);
  return <>
    <GlassButton ref={button} className="lg-inspect-trigger" aria-label={label} aria-haspopup="dialog" aria-expanded={open} aria-controls={id} popoverTarget={id} onClick={() => {
      onOpen?.();
      if (!("showPopover" in HTMLElement.prototype)) setOpen(value => !value);
    }}>{trigger}</GlassButton>
    {mounted ? createPortal(
      <div ref={panel} id={id} popover="auto" className="lg-popover" data-open={open} role="dialog" aria-label={label}
        onToggle={event => setOpen(event.newState === "open")}
        onKeyDown={event => { if (event.key === "Escape") { event.preventDefault(); close(); } }}>
        {open ? <GlassSurface material="panel" radius={20} className="lg-popover-surface">
          <div className="lg-popover-heading"><strong>{label}</strong><GlassButton aria-label="Close inspector" onClick={close}><X aria-hidden="true" size={16} /></GlassButton></div>
          {children}
        </GlassSurface> : null}
      </div>, document.body) : null}
  </>;
}
