export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "invproc_theme_v1";
const THEME_EVENT = "invproc:theme-change";

export const THEME_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem("${THEME_STORAGE_KEY}");var d=s==="dark"||(s!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);document.documentElement.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

function applyThemeClass(isDark: boolean): void {
  document.documentElement.classList.toggle("dark", isDark);
  document.documentElement.style.colorScheme = isDark ? "dark" : "light";
}

export function subscribeTheme(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onMediaChange = () => {
    try {
      const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (saved !== "light" && saved !== "dark") {
        applyThemeClass(media.matches);
        callback();
      }
    } catch {
      // Ignore storage errors
    }
  };
  const onStorage = (event: StorageEvent) => {
    if (event.key === THEME_STORAGE_KEY) {
      applyThemeClass(event.newValue === "dark");
      callback();
    }
  };

  window.addEventListener(THEME_EVENT, callback);
  window.addEventListener("storage", onStorage);
  media.addEventListener("change", onMediaChange);
  return () => {
    window.removeEventListener(THEME_EVENT, callback);
    window.removeEventListener("storage", onStorage);
    media.removeEventListener("change", onMediaChange);
  };
}

export function getThemeSnapshot(): ThemeMode {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark")
    ? "dark"
    : "light";
}

export function getThemeServerSnapshot(): ThemeMode {
  return "light";
}

export function setThemeMode(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  applyThemeClass(mode === "dark");
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}

export function toggleThemeMode(): ThemeMode {
  const next: ThemeMode = getThemeSnapshot() === "dark" ? "light" : "dark";
  setThemeMode(next);
  return next;
}
