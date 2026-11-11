"""Initial invoices and line_items schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-12 01:53:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("semantic_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "duplicate_of_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_key", sa.String(length=512), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="extracted"),
        sa.Column("document_type", sa.String(length=32), nullable=False, server_default="invoice"),
        sa.Column("vendor", sa.Text(), nullable=True),
        sa.Column("vendor_address", sa.Text(), nullable=True),
        sa.Column("receipt_number", sa.String(length=128), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("tax_amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("discount_amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("bill_to", sa.Text(), nullable=True),
        sa.Column("extractor_used", sa.String(length=128), nullable=True),
        sa.Column("extraction_latency_ms", sa.Integer(), nullable=True),
        sa.Column("items_match_subtotal", sa.Boolean(), nullable=True),
        sa.Column("totals_reconcile", sa.Boolean(), nullable=True),
        sa.Column("raw_ocr_markdown", sa.Text(), nullable=True),
        sa.Column("provenance_json", _JSON_VARIANT, nullable=False, server_default="{}"),
        sa.Column("warnings_json", _JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_invoices_file_hash", "invoices", ["file_hash"])
    op.create_index("ix_invoices_semantic_hash", "invoices", ["semantic_hash"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_vendor", "invoices", ["vendor"])
    op.create_index("ix_invoices_receipt_number", "invoices", ["receipt_number"])
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"])

    op.create_table(
        "line_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "invoice_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("total_price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("bbox_json", _JSON_VARIANT, nullable=True),
    )
    op.create_index("ix_line_items_invoice_id", "line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_line_items_invoice_id", table_name="line_items")
    op.drop_table("line_items")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
    op.drop_index("ix_invoices_receipt_number", table_name="invoices")
    op.drop_index("ix_invoices_vendor", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_semantic_hash", table_name="invoices")
    op.drop_index("ix_invoices_file_hash", table_name="invoices")
    op.drop_table("invoices")
