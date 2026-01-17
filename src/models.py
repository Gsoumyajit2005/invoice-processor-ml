# src/models.py

from typing import List, Optional
from datetime import date as DateType
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship

SQLModel.metadata.clear()

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Data Fields
    receipt_number: Optional[str] = Field(default=None, index=True)
    date: Optional[DateType] = Field(default=None)
    total_amount: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    vendor: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    
    # Critical for Deduplication
    semantic_hash: str = Field(unique=True, index=True)
    
    # Metadata Fields
    validation_status: str = Field(default="unknown")
    # Store validation_errors as a JSON string because SQLModel/SQLite doesn't always support arrays out of the box
    validation_errors: Optional[str] = Field(default="[]") 
    created_at: DateType = Field(default_factory=datetime.now)
    
    # Relationship to LineItem (One-to-Many)
    items: List["LineItem"] = Relationship(back_populates="invoice")


class LineItem(SQLModel, table=True):
    __tablename__ = "line_items"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id")
    
    # Data Fields
    description: str
    quantity: int = Field(default=1)
    unit_price: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    total: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)

    # Relationship back to Invoice
    invoice: Optional[Invoice] = Relationship(back_populates="items")