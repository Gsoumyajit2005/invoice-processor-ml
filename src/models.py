# src/models.py

from typing import List, Optional
from datetime import date as DateType
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship

# --- INSTRUCTIONS ---
# SQLModel classes should mirror the Pydantic models in src/schema.py
# but with database-specific configurations (primary keys, foreign keys).

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    # TODO: Define Primary Key 'id' (int, optional, default=None)
    
    # TODO: Add Data Fields
    # - receipt_number (str, indexed)
    # - date (DateType)
    # - total_amount (Decimal, max_digits=10, decimal_places=2)
    # - vendor (str)
    # - address (str)
    # - semantic_hash (str, unique, indexed) -> Critical for deduplication
    
    # TODO: Add Metadata Fields
    # - validation_status (str)
    # - validation_errors (str) -> Store as JSON string since we don't need to query inside it yet
    # - created_at (DateType) -> Default to today
    
    # TODO: Define relationship to LineItem (One-to-Many)
    # items: List["LineItem"] = Relationship(...)
    pass


class LineItem(SQLModel, table=True):
    __tablename__ = "line_items"

    # TODO: Define Primary Key
    
    # TODO: Define Foreign Key 'invoice_id' linking to 'invoices.id'
    
    # TODO: Add Data Fields
    # - description (str)
    # - quantity (int)
    # - unit_price (Decimal)
    # - total (Decimal)

    # TODO: Define relationship back to Invoice
    # invoice: Optional[Invoice] = Relationship(...)
    pass
