export type DocumentType = "invoice" | "receipt" | "credit_note" | "unknown";

export type InvoiceStatus = "extracted" | "needs_review" | "verified" | "failed";

export type ExtractMode = "auto" | "local" | "cloud";

export type CloudProvider = "gemini" | "openai" | "openrouter";

export interface BoundingBox {
  page: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number | null;
}

export interface FieldProvenance {
  value: unknown;
  bbox: BoundingBox | null;
  source: "ocr_matched" | "vlm_inferred" | "user_edited";
}

export interface LineItem {
  id?: string;
  position?: number;
  description: string;
  quantity: number | null;
  unit_price: number | null;
  total_price: number | null;
  bbox: BoundingBox | null;
}

export interface InvoiceExtractionData {
  document_type: DocumentType;
  vendor: string | null;
  vendor_address: string | null;
  receipt_number: string | null;
  date: string | null;
  due_date: string | null;
  currency: string | null;
  subtotal: number | null;
  tax_amount: number | null;
  discount_amount: number | null;
  total_amount: number | null;
  bill_to: string | null;
  line_items: LineItem[];
  provenance: Record<string, FieldProvenance>;
  validation_warnings: string[];
}

export interface ExtractionResponse {
  invoice_id: string;
  filename: string;
  file_hash: string;
  semantic_hash: string | null;
  duplicate_of_id: string | null;
  status: InvoiceStatus;
  extractor_used: string;
  latency_ms: number;
  page_count: number;
  items_match_subtotal: boolean | null;
  totals_reconcile: boolean | null;
  needs_escalation: boolean;
  extraction: InvoiceExtractionData;
  page_image_urls: string[];
  created_at: string;
}

export interface BatchExtractionItem {
  filename: string;
  ok: boolean;
  result: ExtractionResponse | null;
  error: string | null;
}

export interface BatchExtractionResponse {
  total: number;
  succeeded: number;
  failed: number;
  items: BatchExtractionItem[];
}

export interface InvoiceSummary {
  id: string;
  filename: string;
  document_type: DocumentType;
  vendor: string | null;
  receipt_number: string | null;
  date: string | null;
  currency: string | null;
  total_amount: number | null;
  status: InvoiceStatus;
  extractor_used: string | null;
  items_match_subtotal: boolean | null;
  totals_reconcile: boolean | null;
  duplicate_of_id: string | null;
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface InvoiceListResponse {
  items: InvoiceSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface InvoiceDetail {
  id: string;
  filename: string;
  file_hash: string;
  semantic_hash: string | null;
  duplicate_of_id: string | null;
  status: InvoiceStatus;
  document_type: DocumentType;
  vendor: string | null;
  vendor_address: string | null;
  receipt_number: string | null;
  date: string | null;
  due_date: string | null;
  currency: string | null;
  subtotal: number | null;
  tax_amount: number | null;
  discount_amount: number | null;
  total_amount: number | null;
  bill_to: string | null;
  extractor_used: string | null;
  extraction_latency_ms: number | null;
  items_match_subtotal: boolean | null;
  totals_reconcile: boolean | null;
  page_count: number;
  raw_ocr_markdown: string | null;
  provenance: Record<string, FieldProvenance>;
  validation_warnings: string[];
  line_items: LineItem[];
  page_image_urls: string[];
  created_at: string;
  updated_at: string;
}

export interface InvoicePatchPayload {
  document_type?: DocumentType | null;
  vendor?: string | null;
  vendor_address?: string | null;
  receipt_number?: string | null;
  date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  subtotal?: number | null;
  tax_amount?: number | null;
  discount_amount?: number | null;
  total_amount?: number | null;
  bill_to?: string | null;
  line_items?: Array<{
    description: string;
    quantity: number | null;
    unit_price: number | null;
    total_price: number | null;
    bbox: BoundingBox | null;
  }> | null;
  status?: InvoiceStatus | null;
  mark_verified?: boolean;
}

export interface BulkReportRequest {
  invoice_ids?: string[] | null;
  status?: InvoiceStatus | null;
  format: "json" | "csv" | "html";
}

export interface HealthResponse {
  status: "ok" | "degraded";
  database: {
    connected: boolean;
    error: string | null;
  };
  storage_backend: string;
  local_vlm: {
    enabled: boolean;
    weights_present: boolean;
    loaded: boolean;
    adapter_configured: boolean;
    model_dir: string;
    started_at: number;
  };
  cloud_default_configured: boolean;
  limits: {
    max_upload_mb: number;
    max_pdf_pages: number;
    rate_limit_extract: string;
  };
}

export interface AuthStatusResponse {
  required: boolean;
  authenticated: boolean;
}
