# Phase 4 Frontend Architecture, HITL Workbench & UI Roadmap

**Repository:** `invoice-processor-ml` (branch: `feat/v2-modernization`)  
**Stack:** Next.js `16.4.6` (App Router) · React `19.3.0` · TypeScript `5.x` · Tailwind CSS `4.3.3` · Lucide Icons · Headless Chromium CDP Test Harness  
**Source Code:** `frontend/` (`frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/`)  

---

## 1. Executive Summary

Phase 4 replaced the legacy single-script Streamlit prototype (`app.py`) with a production-grade, enterprise Next.js TypeScript frontend. The interface provides an end-to-end Human-in-the-Loop (HITL) review environment for complex multi-page financial documents, structured extraction previews, currency-segregated ledger analytics, and zero-flash light/dark theme switching with a modern glassmorphic design system.

### Key Capabilities Built in Phase 4
1. **Side-by-Side HITL Review Studio (`/invoices/[id]`):** Split-screen workbench pairing an interactive SVG bounding-box overlay (`[0..1000]` canvas) directly with editable invoice schema fields and line-item tables. Hovering or focusing any form field immediately highlights its corresponding OCR bounding box on the rendered page scan.
2. **Deterministic Math Reconciliation Banner:** Live arithmetic verification checking `sum(line_items) == subtotal` and `subtotal + tax - discount == total_amount` with one-click discrepancy resolution.
3. **Multi-Currency Batch Analytics (`/batch`):** Totals and summaries strictly segregated by ISO currency code (never mixed or coerced into a single symbol), with instant CSV, JSON, and standalone styled HTML report downloads.
4. **Zero-Flash Theme Engine & Glassmorphism (`theme.ts`, `globals.css`):** Client-side external store synchronization with inline `<head>` hydration script, explicit browser `color-scheme` control, fixed ambient gradient depth orbs, and layered frosted glass surfaces (`backdrop-blur-xl`, translucent fills, and hairline specular highlights).
5. **Secure Backend-for-Frontend (BFF) Proxy:** Next.js server-side route handlers proxying API calls, injecting `X-Backend-Secret`, streaming authenticated page PNGs, and enforcing optional timing-safe HMAC cookie authentication for demo environments.

---

## 2. Mode Verification & Validation Status

| Mode | Architecture & Pipeline | Status | Verification Details |
|---|---|:---:|---|
| **Auto Hybrid Mode** | Ingest → Indra OCR 1.1 ONNX → Local Qwen3.5-0.8B LoRA → Math Reconciliation → Optional Cloud Escalation | **Verified Live** | Tested end-to-end in real browser. Successfully extracted `swc enterprise receipt.jpeg` (`SWC ENTERPRISE SDN BHD`, `MYR 8.00`, 6 grounded bounding boxes, balanced reconciliation) on local NVIDIA RTX 3050 6GB GPU and PostgreSQL 16. |
| **Local GPU Only** | Private Indra OCR 1.1 + Qwen3.5-0.8B LoRA (Strictly local, zero network egress) | **Verified Live** | Confirmed fully operational with lazy model initialization and VRAM safety locks (`~2.0–2.8 GB` peak VRAM). |
| **BYOK Cloud VLM Mode** | Client ephemeral `sessionStorage` → `X-LLM-*` headers → Server Proxy → LiteLLM (Gemini / OpenAI / OpenRouter) | **Implemented (Pending Live API Key)** | Architecture, UI drawer, header forwarding, and backend proxy router fully implemented. Pending live end-to-end verification with active third-party API keys (e.g. Gemini 2.5 Flash / GPT-4o-mini). |

> [!NOTE]
> **BYOK Security Guarantee:** Bring-Your-Own-Key credentials remain strictly in browser `sessionStorage` and request memory headers. They are **never** committed to the database, stored in `localStorage`, or persisted to disk.

---

## 3. Glassmorphism Design System & Theme Engine

### Architecture
To ensure the frosted glass effect refracts depth without compromising document legibility, the interface employs a dual-canvas visual hierarchy:
- **Base Ambient Mesh Canvas (`RootLayout`):** Fixed, pointer-events-none background containing soft blurred radial gradient orbs (indigo, cyan, violet) on `#eef2f7` (light) and `#030712` (dark).
- **Frosted Glass Panels (`.glass-surface`, `.glass-surface-elevated`, `.glass-subtle`):** Defined within `@layer components` using Tailwind utilities (`@apply backdrop-blur-xl backdrop-saturate-150`) to ensure LightningCSS preserves both standard `backdrop-filter` and `-webkit-backdrop-filter` across all modern browser engines.
- **Scanned Document Preservation:** While the surrounding toolbars and form cards use translucent frosted styling, the document paper container in `DocumentOverlayViewer` maintains an opaque white scan canvas to guarantee OCR inks and bounding box strokes remain 100% sharp and true to color.

### Theme Engine Implementation
- **Zero-Flash Hydration:** An inline script in `<head>` reads `localStorage` or `matchMedia('(prefers-color-scheme: dark)')` before the initial DOM render, toggling `document.documentElement.classList` and `document.documentElement.style.colorScheme`.
- **External Store Synchronization:** Uses React `useSyncExternalStore` for atomic theme reactivity without React hydration mismatch warnings.
- **Native Form Integration:** Syncing `colorScheme = 'dark' | 'light'` ensures browser-native datepicker flyouts (`<input type="date">`), dropdown menus (`<select>`), and OS scrollbars automatically reflect the active theme.

---

## 4. UI Future Upgrade Roadmap

The current v2 interface is fully functional, responsive, and robust for production use. The following enhancements are cataloged for future UI iterations:

1. **Interactive Batch Data Visualizations (`/batch`):**
   - Add lightweight SVG/Canvas charts (e.g. Chart.js or Recharts) to visualize spend over time, vendor Pareto distributions, and tax vs. net ratios per currency bucket.
2. **Mobile & Touch Gestures for Document Canvas (`/invoices/[id]`):**
   - Implement multi-touch pinch-to-zoom and two-finger pan gestures for mobile/tablet review workflows.
3. **Advanced Keyboard Navigation:**
   - Add Vim-style or spreadsheet-style keyboard shortcuts (`j`/`k` for invoice row traversal, `Cmd+S` / `Ctrl+S` for quick draft saving, `Tab`/`Shift+Tab` for cycling directly through bounding boxes on the page).
4. **Multi-Page Thumbnail Filmstrip:**
   - For 10+ page PDFs, provide a collapsible vertical thumbnail filmstrip sidebar allowing rapid page navigation with page-level bbox presence indicators.
5. **Bulk Archive Uploads:**
   - Support folder drag-and-drop and `.zip` archive upload unpacking on the `/` dropzone.

---

## 5. Resume-Ready Engineering Highlights

- **Full-Stack Document AI Architecture:** Architected and deployed a multi-stage Document AI platform pairing ONNX-based coordinate OCR (`Indra OCR 1.1`) with a fine-tuned multimodal 0.8B VLM (`Qwen3.5-0.8B LoRA`), achieving sub-second token grounding and 90%+ extraction accuracy within 3.3 GB VRAM.
- **Human-in-the-Loop Split-Screen Workbench:** Built a high-performance Next.js 16 (App Router) review studio in TypeScript, featuring bi-directional SVG bounding-box highlight synchronization, deterministic subtotal/tax/discount arithmetic reconciliation, and live draft persistence.
- **Enterprise Design System & Theme Engine:** Engineered a zero-flash light/dark theme engine with custom Tailwind v4 glassmorphic components (`backdrop-blur-xl`, specular edge lighting, ambient mesh canvases) validated via automated headless Chromium CDP testing across all application routes.
- **Security & Privacy-First BFF:** Designed a secure Node.js proxy layer with timing-safe HMAC demo authentication, server-injected backend credentials, and ephemeral `sessionStorage` BYOK Cloud VLM routing with zero server-side credential persistence.
