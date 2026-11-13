"use client";

import { useEffect, type RefObject } from "react";
import { bakeLensMap } from "./lens-map";

const cache = new Map<string, ReturnType<typeof bakeLensMap>>();
export function useDisplacementMap(host: RefObject<HTMLDivElement | null>, pane: RefObject<HTMLDivElement | null>, image: RefObject<SVGFEImageElement | null>, id: string, enabled: boolean, radius: number, strength: number) {
  useEffect(() => {
    const node = host.current;
    const surface = pane.current;
    if (!node || !surface || !enabled) return;
    let active = true, revision = 0, timer: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width), height = Math.round(entry.contentRect.height);
      const current = ++revision;
      clearTimeout(timer);
      // Debounce resize bursts. The last correctly shaped map remains visible meanwhile.
      timer = setTimeout(() => {
        if (width <= 0 || height <= 0) return;
        const key = `${width}:${height}:${radius}`;
        let map = cache.get(key);
        if (!map) {
          map = bakeLensMap(width, height, radius);
          if (cache.size >= 32) cache.delete(cache.keys().next().value!);
          cache.set(key, map);
        }
        if (!map) return;
        const decoded = new Image();
        decoded.onload = () => {
          if (!active || current !== revision) return;
          image.current?.setAttribute("href", map.url);
          surface.style.backdropFilter = `url("#${id}") blur(0.45px) saturate(1.12)`;
          node.dataset.ready = "true";
        };
        decoded.onerror = () => { if (active && current === revision) { surface.style.backdropFilter = ""; node.dataset.ready = "false"; } };
        decoded.src = map.url;
      }, 80);
    });
    observer.observe(node);
    return () => { active = false; clearTimeout(timer); observer.disconnect(); surface.style.backdropFilter = ""; node.dataset.ready = "false"; };
  }, [host, pane, image, id, enabled, radius, strength]);
}
