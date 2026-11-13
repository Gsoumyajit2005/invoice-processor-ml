"use client";

import { useEffect, useRef } from "react";

export function AnimatedWave() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);
  const isVisibleRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const chars = "·∘○◯◌●◉";
    let time = 0;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.resetTransform?.();
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener("resize", resize);

    const render = () => {
      if (!isVisibleRef.current && !prefersReducedMotion) {
        frameRef.current = requestAnimationFrame(render);
        return;
      }

      const rect = canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        frameRef.current = requestAnimationFrame(render);
        return;
      }

      ctx.clearRect(0, 0, rect.width, rect.height);

      const isDark = document.documentElement.classList.contains("dark");
      const rgb = isDark ? "245, 240, 232" : "41, 39, 35";

      ctx.font = "14px monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const cols = Math.max(1, Math.floor(rect.width / 20));
      const rows = Math.max(1, Math.floor(rect.height / 20));

      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const px = (x + 0.5) * (rect.width / cols);
          const py = (y + 0.5) * (rect.height / rows);

          const wave1 = Math.sin(x * 0.2 + time * 2) * Math.cos(y * 0.15 + time);
          const wave2 = Math.sin((x + y) * 0.1 + time * 1.5);
          const wave3 = Math.cos(x * 0.1 - y * 0.1 + time * 0.8);

          const combined = (wave1 + wave2 + wave3) / 3;
          const normalized = (combined + 1) / 2;

          const charIndex = Math.floor(normalized * (chars.length - 1));
          const alpha = 0.1 + normalized * 0.4;

          ctx.fillStyle = `rgba(${rgb}, ${alpha})`;
          ctx.fillText(chars[charIndex], px, py);
        }
      }

      if (!prefersReducedMotion) {
        time += 0.03;
        frameRef.current = requestAnimationFrame(render);
      }
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisibleRef.current = entry.isIntersecting;
      },
      { threshold: 0.05 }
    );
    observer.observe(canvas);

    render();

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: "block" }}
      aria-hidden="true"
    />
  );
}
