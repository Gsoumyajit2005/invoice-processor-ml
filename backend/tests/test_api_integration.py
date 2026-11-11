"""Integration tests for FastAPI v1 routes, auto escalation, HITL edits, and reports."""

from __future__ import annotations

from pathlib import Path

import httpx
from app.core.config import Settings
from app.core.schemas import InvoiceExtraction, LineItemSchema
from app.extractors.router import ExtractionRouter
from app.main import create_app

from tests.conftest import (
    FakeOcrService,
    StubExtractor,
    make_multipage_pdf_bytes,
    make_png_bytes,
)


async def test_health_endpoint(test_client: httpx.AsyncClient) -> None:
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    assert body["storage_backend"] == "local"


async def test_extract_multipage_pdf_pages_duplicate_and_delete(
    test_client: httpx.AsyncClient,
) -> None:
    pdf_bytes = make_multipage_pdf_bytes(num_pages=2)
    r1 = await test_client.post(
        "/api/v1/extract",
        files={"file": ("multi.pdf", pdf_bytes, "application/pdf")},
    )
    assert r1.status_code == 200
    body1 = r1.json()
    inv_id = body1["invoice_id"]
    assert body1["page_count"] == 2
    assert len(body1["page_image_urls"]) == 2
    assert body1["duplicate_of_id"] is None
    assert body1["totals_reconcile"] is True
    assert body1["status"] == "extracted"
    assert body1["extraction"]["provenance"]["vendor"]["source"] == "ocr_matched"

    # Rendered pages stream cleanly; page 3 returns 404
    p1 = await test_client.get(f"/api/v1/invoices/{inv_id}/pages/1")
    p2 = await test_client.get(f"/api/v1/invoices/{inv_id}/pages/2")
    p3 = await test_client.get(f"/api/v1/invoices/{inv_id}/pages/3")
    assert p1.status_code == 200 and p1.headers["content-type"] == "image/png"
    assert p2.status_code == 200 and p2.headers["content-type"] == "image/png"
    assert p3.status_code == 404

    # Re-uploading flags duplicate_of_id pointing to original invoice
    r2 = await test_client.post(
        "/api/v1/extract",
        files={"file": ("multi_copy.pdf", pdf_bytes, "application/pdf")},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["duplicate_of_id"] == inv_id
    dup_id = body2["invoice_id"]

    # Deleting original succeeds without FK errors and nullifies duplicate_of_id on copy
    d_res = await test_client.delete(f"/api/v1/invoices/{inv_id}")
    assert d_res.status_code == 204
    assert (await test_client.get(f"/api/v1/invoices/{inv_id}")).status_code == 404

    copy_detail = (await test_client.get(f"/api/v1/invoices/{dup_id}")).json()
    assert copy_detail["duplicate_of_id"] is None


async def test_hitl_patch_verify_search_and_bulk_xss_safe_reports(
    test_client: httpx.AsyncClient,
) -> None:
    png = make_png_bytes()
    ext = (
        await test_client.post(
            "/api/v1/extract",
            files={"file": ("receipt.png", png, "image/png")},
        )
    ).json()
    inv_id = ext["invoice_id"]

    # Inject XSS + CSV-formula vendor string via HITL PATCH and mark verified
    patch_payload = {
        "vendor": '=cmd|<script>alert("xss")</script>',
        "subtotal": 200.0,
        "tax_amount": 20.0,
        "total_amount": 220.0,
        "line_items": [
            {"description": "Updated <Item>", "quantity": 2, "unit_price": 100, "total_price": 200}
        ],
        "mark_verified": True,
    }
    patched = await test_client.patch(f"/api/v1/invoices/{inv_id}", json=patch_payload)
    assert patched.status_code == 200
    p_body = patched.json()
    assert p_body["status"] == "verified"
    assert p_body["total_amount"] == 220.0
    assert p_body["totals_reconcile"] is True
    assert p_body["provenance"]["vendor"]["source"] == "user_edited"
    assert len(p_body["line_items"]) == 1

    # Search and filter pagination
    listed = (await test_client.get("/api/v1/invoices", params={"status": "verified"})).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == inv_id

    # HTML export escapes <script> tags cleanly
    html_resp = await test_client.post(
        "/api/v1/reports/bulk",
        json={"invoice_ids": [inv_id], "format": "html"},
    )
    assert html_resp.status_code == 200
    assert "<script>" not in html_resp.text
    assert "&lt;script&gt;" in html_resp.text

    # CSV export neutralizes leading '=' formula injection
    csv_resp = await test_client.post(
        "/api/v1/reports/bulk",
        json={"format": "csv"},
    )
    assert csv_resp.status_code == 200
    assert "'=cmd" in csv_resp.text

    # JSON export includes full nested items
    json_resp = await test_client.post(
        "/api/v1/reports/bulk",
        json={"format": "json"},
    )
    assert json_resp.status_code == 200
    assert json_resp.json()["count"] == 1


async def test_batch_extract_and_validation_limits(test_client: httpx.AsyncClient) -> None:
    good_png = make_png_bytes()
    bad_bytes = b"not-an-image-or-pdf"

    batch_resp = await test_client.post(
        "/api/v1/extract/batch",
        files=[
            ("files", ("good.png", good_png, "image/png")),
            ("files", ("bad.exe", bad_bytes, "application/octet-stream")),
        ],
    )
    assert batch_resp.status_code == 200
    b_data = batch_resp.json()
    assert b_data["total"] == 2
    assert b_data["succeeded"] == 1
    assert b_data["failed"] == 1
    assert b_data["items"][0]["ok"] is True
    assert b_data["items"][1]["ok"] is False

    # Single extract rejects wrong magic bytes with 415
    unsupported = await test_client.post(
        "/api/v1/extract",
        files={"file": ("fake.png", bad_bytes, "image/png")},
    )
    assert unsupported.status_code == 415

    # Single extract rejects >1MB upload with 413
    oversized = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (1024 * 1024 + 50))
    too_big = await test_client.post(
        "/api/v1/extract",
        files={"file": ("huge.png", oversized, "image/png")},
    )
    assert too_big.status_code == 413


async def test_auto_escalation_and_shared_secret_auth(tmp_path: Path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        storage_backend="local",
        local_upload_dir=str(tmp_path / "uploads"),
        backend_shared_secret="super-secret-token",
        local_vlm_enabled=True,
        rate_limit_extract="100/minute",
    )
    bad_local = InvoiceExtraction(
        vendor="Local Partial",
        subtotal=100.0,
        tax_amount=19.0,
        total_amount=999.0,  # Forces reconciliation mismatch -> needs_escalation=True
        line_items=[LineItemSchema(description="Service", total_price=100.0)],
    )
    good_cloud = InvoiceExtraction(
        vendor="Local Partial",
        receipt_number="INV-99",
        date="2025-05-28",
        subtotal=100.0,
        tax_amount=19.0,
        total_amount=119.0,
        line_items=[LineItemSchema(description="Service", total_price=100.0)],
    )
    local_stub = StubExtractor("local:Qwen3.5-0.8B", bad_local)
    cloud_stub = StubExtractor("cloud:gemini-2.5-flash", good_cloud)
    router = ExtractionRouter(
        settings,
        ocr_service=FakeOcrService(),  # type: ignore[arg-type]
        local_extractor=local_stub,
        cloud_extractor=cloud_stub,
    )
    app = create_app(settings_override=settings, router_override=router)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Missing or wrong secret is rejected cleanly on protected routes
            unauth = await client.get("/api/v1/invoices")
            assert unauth.status_code == 401
            wrong = await client.get(
                "/api/v1/invoices",
                headers={"X-Backend-Secret": "wrong"},
            )
            assert wrong.status_code == 401

            # Health remains open
            assert (await client.get("/api/v1/health")).status_code == 200

            # Auto mode escalates when local reconciliation fails and BYO key is supplied
            secret_key_val = "sk-ephemeral-test-only"
            ok = await client.post(
                "/api/v1/extract",
                headers={
                    "X-Backend-Secret": "super-secret-token",
                    "X-LLM-Provider": "gemini",
                    "X-LLM-Api-Key": secret_key_val,
                },
                files={"file": ("inv.png", make_png_bytes(), "image/png")},
            )
            assert ok.status_code == 200
            body = ok.json()
            assert "cloud:" in body["extractor_used"]
            assert body["extraction"]["total_amount"] == 119.0
            assert body["totals_reconcile"] is True
            assert len(local_stub.calls) == 1
            assert len(cloud_stub.calls) == 1
            assert secret_key_val not in ok.text
