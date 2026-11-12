import type {
  BatchExtractionResponse,
  CloudProvider,
  ExtractMode,
} from "@/lib/types";

const CLOUD_STORAGE_KEY = "invproc_cloud_vlm_session_v1";
const LATEST_BATCH_KEY = "invproc_latest_batch_session_v1";
const SESSION_STORE_EVENT = "invproc:session-store";

export interface CloudKeyConfig {
  provider: CloudProvider;
  model: string;
  apiKey: string;
}

export interface StoredBatchRun {
  savedAt: string;
  batch: BatchExtractionResponse;
}

export const CLOUD_PROVIDER_DEFAULTS: Record<
  CloudProvider,
  { label: string; defaultModel: string; placeholder: string }
> = {
  gemini: {
    label: "Google Gemini (via LiteLLM)",
    defaultModel: "gemini/gemini-2.5-flash",
    placeholder: "AIza...",
  },
  openai: {
    label: "OpenAI Vision",
    defaultModel: "openai/gpt-4o-mini",
    placeholder: "sk-...",
  },
  openrouter: {
    label: "OpenRouter",
    defaultModel: "openrouter/google/gemini-2.5-flash",
    placeholder: "sk-or-...",
  },
};

export function defaultCloudConfig(): CloudKeyConfig {
  return {
    provider: "gemini",
    model: CLOUD_PROVIDER_DEFAULTS.gemini.defaultModel,
    apiKey: "",
  };
}

function emitSessionStoreChange(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_STORE_EVENT));
  }
}

export function subscribeSessionStore(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  window.addEventListener(SESSION_STORE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(SESSION_STORE_EVENT, callback);
  };
}

export function getCloudConfigRaw(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(CLOUD_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function parseCloudConfigRaw(raw: string): CloudKeyConfig {
  if (!raw) return defaultCloudConfig();
  try {
    const parsed = JSON.parse(raw) as Partial<CloudKeyConfig>;
    const provider: CloudProvider =
      parsed.provider === "openai" || parsed.provider === "openrouter"
        ? parsed.provider
        : "gemini";
    return {
      provider,
      model:
        typeof parsed.model === "string" && parsed.model.trim()
          ? parsed.model.trim()
          : CLOUD_PROVIDER_DEFAULTS[provider].defaultModel,
      apiKey: typeof parsed.apiKey === "string" ? parsed.apiKey : "",
    };
  } catch {
    return defaultCloudConfig();
  }
}

export function loadCloudConfig(): CloudKeyConfig {
  return parseCloudConfigRaw(getCloudConfigRaw());
}

export function saveCloudConfig(config: CloudKeyConfig): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(CLOUD_STORAGE_KEY, JSON.stringify(config));
    emitSessionStoreChange();
  } catch {
    // Ignore storage quota / privacy mode failures
  }
}

export function clearCloudConfig(): CloudKeyConfig {
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.removeItem(CLOUD_STORAGE_KEY);
      emitSessionStoreChange();
    } catch {
      // Ignore
    }
  }
  return defaultCloudConfig();
}

export function buildCloudHeaders(
  mode: ExtractMode,
  override?: CloudKeyConfig,
): Record<string, string> {
  if (mode === "local") return {};
  const cfg = override ?? loadCloudConfig();
  const key = cfg.apiKey.trim();
  if (!key) return {};
  const headers: Record<string, string> = {
    "X-LLM-Provider": cfg.provider,
    "X-LLM-Api-Key": key,
  };
  const model = cfg.model.trim();
  if (model) {
    headers["X-LLM-Model"] = model;
  }
  return headers;
}

export function getLatestBatchRaw(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(LATEST_BATCH_KEY) ?? "";
  } catch {
    return "";
  }
}

export function parseLatestBatchRaw(raw: string): StoredBatchRun | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as {
      savedAt?: unknown;
      batch?: BatchExtractionResponse;
    };
    if (typeof parsed.savedAt === "string" && parsed.batch) {
      return { savedAt: parsed.savedAt, batch: parsed.batch };
    }
    return null;
  } catch {
    return null;
  }
}

export function saveLatestBatch(batch: BatchExtractionResponse): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      LATEST_BATCH_KEY,
      JSON.stringify({ savedAt: new Date().toISOString(), batch }),
    );
    emitSessionStoreChange();
  } catch {
    // Ignore
  }
}

export function clearLatestBatch(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(LATEST_BATCH_KEY);
    emitSessionStoreChange();
  } catch {
    // Ignore
  }
}
