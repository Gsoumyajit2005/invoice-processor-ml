"""SQLModel / SQLAlchemy persistence models for invoices and line items."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

_JSON_VARIANT = JSON().with_variant(JSONB(), "postgresql")


class InvoiceRecord(SQLModel, table=True):
    """Persisted invoice extraction record, deduplication hashes, and provenance."""

    __tablename__ = "invoices"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid(as_uuid=True), primary_key=True),
    )
    file_hash: str = Field(
        sa_column=Column(String(64), nullable=False, index=True),
    )
    semantic_hash: str | None = Field(
        default=None,
        sa_column=Column(String(64), nullable=True, index=True),
    )
    duplicate_of_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid(as_uuid=True),
            ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    filename: str = Field(
        sa_column=Column(String(512), nullable=False),
    )
    mime_type: str = Field(
        sa_column=Column(String(100), nullable=False),
    )
    file_key: str = Field(
        sa_column=Column(String(512), nullable=False),
    )
    page_count: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, default=1),
    )
    status: str = Field(
        default="extracted",
        sa_column=Column(String(32), nullable=False, default="extracted", index=True),
    )
    document_type: str = Field(
        default="invoice",
        sa_column=Column(String(32), nullable=False, default="invoice"),
    )
    vendor: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
    vendor_address: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    receipt_number: str | None = Field(
        default=None,
        sa_column=Column(String(128), nullable=True, index=True),
    )
    invoice_date: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True, index=True),
    )
    due_date: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    currency: str | None = Field(
        default=None,
        sa_column=Column(String(8), nullable=True),
    )
    subtotal: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    tax_amount: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    discount_amount: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    total_amount: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    bill_to: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    extractor_used: str | None = Field(
        default=None,
        sa_column=Column(String(128), nullable=True),
    )
    extraction_latency_ms: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    items_match_subtotal: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    totals_reconcile: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    raw_ocr_markdown: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    provenance_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(_JSON_VARIANT, nullable=False, default=dict),
    )
    warnings_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(_JSON_VARIANT, nullable=False, default=list),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    line_items: list["LineItemRecord"] = Relationship(
        back_populates="invoice",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "LineItemRecord.position",
        },
    )


class LineItemRecord(SQLModel, table=True):
    """Persisted invoice line item with optional normalized bounding box."""

    __tablename__ = "line_items"  # type: ignore[assignment]

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(Uuid(as_uuid=True), primary_key=True),
    )
    invoice_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid(as_uuid=True),
            ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    position: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, default=0),
    )
    description: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    quantity: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(12, 4), nullable=True),
    )
    unit_price: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    total_price: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(14, 4), nullable=True),
    )
    bbox_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(_JSON_VARIANT, nullable=True),
    )

    invoice: Optional["InvoiceRecord"] = Relationship(back_populates="line_items")
