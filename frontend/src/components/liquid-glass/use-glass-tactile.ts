"use client";

import { useEffect, useRef, type PointerEvent, type KeyboardEvent, type FocusEvent } from "react";

/** Delegated native-button/link feedback. Never prevents a click or captures a pointer. */
export function useGlassTactile<T extends HTMLElement>() {
  const motion = useRef({ frame: 0, value: 1, velocity: 0, target: 1, control: null as HTMLElement | null });
  const releaseListener = useRef<(() => void) | null>(null);
  useEffect(() => () => { cancelAnimationFrame(motion.current.frame); releaseListener.current?.(); }, []);

  function spring(control: HTMLElement, pressed: boolean) {
    const state = motion.current;
    if (state.control !== control) {
      state.control?.style.removeProperty("scale");
      if (state.control) state.control.dataset.pressed = "false";
      state.value = 1; state.velocity = 0;
    }
    state.control = control;
    state.target = pressed ? .985 : 1;
    control.dataset.pressed = String(pressed);
    cancelAnimationFrame(state.frame);
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { control.style.removeProperty("scale"); return; }
    let last = performance.now();
    function step(now: number) {
      const dt = Math.min((now - last) / 1000, .025);
      last = now;
      state.velocity += ((state.target - state.value) * 460 - state.velocity * 29) * dt;
      state.value += state.velocity * dt;
      control.style.scale = String(state.value);
      if (Math.abs(state.target - state.value) + Math.abs(state.velocity) > .001) state.frame = requestAnimationFrame(step);
      else { if (pressed) control.style.scale = ".985"; else control.style.removeProperty("scale"); state.frame = 0; }
    }
    state.frame = requestAnimationFrame(step);
  }
  function target(element: EventTarget | null) {
    const node = element instanceof Element ? element.closest<HTMLElement>("button, a, summary") : null;
    return node && !node.matches(":disabled, [aria-disabled='true']") ? node : null;
  }
  function release() {
    releaseListener.current?.();
    releaseListener.current = null;
    if (motion.current.control) spring(motion.current.control, false);
  }
  function key(event: KeyboardEvent<T>, pressed: boolean) {
    if ((event.key === " " || event.key === "Enter") && !event.repeat) {
      const node = target(event.target);
      if (node) spring(node, pressed);
    }
  }
  return {
    onPointerDown(event: PointerEvent<T>) {
      if (event.button !== 0) return;
      const node = target(event.target);
      if (!node) return;
      release();
      spring(node, true);
      window.addEventListener("pointerup", release, { once: true });
      window.addEventListener("pointercancel", release, { once: true });
      window.addEventListener("blur", release, { once: true });
      releaseListener.current = () => {
        window.removeEventListener("pointerup", release);
        window.removeEventListener("pointercancel", release);
        window.removeEventListener("blur", release);
      };
    },
    onKeyDown: (event: KeyboardEvent<T>) => key(event, true),
    onKeyUp: (event: KeyboardEvent<T>) => key(event, false),
    onBlur: (event: FocusEvent<T>) => { if (event.target === motion.current.control) release(); },
  };
}
