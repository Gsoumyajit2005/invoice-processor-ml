import { buildCloudHeaders, type CloudKeyConfig } from "@/lib/cloud-settings";
import type {
  AuthStatusResponse,
  BatchExtractionResponse,
  BulkReportRequest,
  ExtractMode,
  ExtractionResponse,
  HealthResponse,
  InvoiceDetail,
  InvoiceListResponse,
  InvoicePatchPayload,
  InvoiceStatus,
} from "@/lib/types";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  const fallback = `Request failed (${response.status})`;
  try {
    const text = await response.text();
    if (!text) return fallback;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; error?: unknown };
      if (typeof parsed.detail === "string" && parsed.detail.trim()) {
        return parsed.detail;
      }
      if (Array.isArray(parsed.detail)) {
        return parsed.detail
          .map((item) => {
            if (item && typeof item === "object" && "msg" in item) {
              return String((item as { msg: unknown }).msg);
            }
            return JSON.stringify(item);
          })
          .join("; ");
      }
      if (typeof parsed.error === "string" && parsed.error.trim()) {
        return parsed.error;
      }
    } catch {
      return text.slice(0, 300);
    }
  } catch {
    return fallback;
  }
  return fallback;
}

async function requestJson<T>(
  input: string,
  init: RequestInit = {},
  options: { dispatchUnauthorized?: boolean } = {},
): Promise<T> {
  const response = await fetch(input, {
    credentials: "same-origin",
    ...init,
  });

  if (
    response.status === 401 &&
    options.dispatchUnauthorized !== false &&
    typeof window !== "undefined"
  ) {
    window.dispatchEvent(new CustomEvent("invproc:unauthorized"));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getAuthStatus(): Promise<AuthStatusResponse> {
  return requestJson<AuthStatusResponse>(
    "/api/auth",
    { cache: "no-store" },
    { dispatchUnauthorized: false },
  );
}

export async function submitPasscode(
  passcode: string,
): Promise<{ ok: boolean; required: boolean; authenticated: boolean }> {
  return requestJson(
    "/api/auth",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode }),
    },
    { dispatchUnauthorized: false },
  );
}

export async function logoutPasscode(): Promise<void> {
  await requestJson("/api/auth", { method: "DELETE" }, { dispatchUnauthorized: false });
}

export async function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health", { cache: "no-store" });
}

export async function extractSingle(
  file: File,
  mode: ExtractMode,
  cloudOverride?: CloudKeyConfig,
): Promise<ExtractionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<ExtractionResponse>(
    `/api/v1/extract?mode=${encodeURIComponent(mode)}`,
    {
      method: "POST",
      headers: buildCloudHeaders(mode, cloudOverride),
      body: formData,
    },
  );
}

export async function extractBatch(
  files: File[],
  mode: ExtractMode,
  cloudOverride?: CloudKeyConfig,
): Promise<BatchExtractionResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  return requestJson<BatchExtractionResponse>(
    `/api/v1/extract/batch?mode=${encodeURIComponent(mode)}`,
    {
      method: "POST",
      headers: buildCloudHeaders(mode, cloudOverride),
      body: formData,
    },
  );
}

export interface ListInvoicesParams {
  search?: string;
  status?: InvoiceStatus | "";
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export async function listInvoices(
  params: ListInvoicesParams = {},
): Promise<InvoiceListResponse> {
  const qs = new URLSearchParams();
  if (params.search?.trim()) qs.set("search", params.search.trim());
  if (params.status) qs.set("status", params.status);
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  if (typeof params.limit === "number") qs.set("limit", String(params.limit));
  if (typeof params.offset === "number") qs.set("offset", String(params.offset));
  const query = qs.toString();
  return requestJson<InvoiceListResponse>(
    `/api/v1/invoices${query ? `?${query}` : ""}`,
    { cache: "no-store" },
  );
}

export async function getInvoice(id: string): Promise<InvoiceDetail> {
  return requestJson<InvoiceDetail>(
    `/api/v1/invoices/${encodeURIComponent(id)}`,
    { cache: "no-store" },
  );
}

export async function patchInvoice(
  id: string,
  payload: InvoicePatchPayload,
): Promise<InvoiceDetail> {
  return requestJson<InvoiceDetail>(
    `/api/v1/invoices/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteInvoice(id: string): Promise<void> {
  await requestJson<void>(`/api/v1/invoices/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

function extractFilenameFromHeader(
  header: string | null,
  fallback: string,
): string {
  if (!header) return fallback;
  const match = header.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
  if (match?.[1]) {
    return decodeURIComponent(match[1].trim());
  }
  return fallback;
}

export async function downloadBulkReport(
  payload: BulkReportRequest,
): Promise<string> {
  const response = await fetch("/api/v1/reports/bulk", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (response.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("invproc:unauthorized"));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  const blob = await response.blob();
  const fallbackName = `invoices-report.${payload.format}`;
  const filename = extractFilenameFromHeader(
    response.headers.get("content-disposition"),
    fallbackName,
  );

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  return filename;
}
