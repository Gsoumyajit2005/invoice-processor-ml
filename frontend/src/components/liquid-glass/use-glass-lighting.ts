"use client";

import { useEffect, useRef, type PointerEvent } from "react";

export function useGlassLighting<T extends HTMLElement>() {
  const frame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);
  return {
    onPointerMove(event: PointerEvent<T>) {
      if (event.pointerType === "touch" || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const node = event.currentTarget;
      const { clientX, clientY } = event;
      const control = (event.target as Element).closest<HTMLElement>("button, a, summary");
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        const box = node.getBoundingClientRect();
        const controlBox = control?.getBoundingClientRect();
        // Batch reads before writes; no React state or map regeneration per move.
        if (control && controlBox) {
          control.style.setProperty("--control-x", `${clientX - controlBox.left}px`);
          control.style.setProperty("--control-y", `${clientY - controlBox.top}px`);
        }
        node.style.setProperty("--light-x", `${clientX - box.left}px`);
        node.style.setProperty("--light-y", `${clientY - box.top}px`);
        node.style.setProperty("--light-angle", `${Math.atan2(clientY - box.top - box.height / 2, clientX - box.left - box.width / 2) * 180 / Math.PI + 90}deg`);
      });
    },
  };
}
