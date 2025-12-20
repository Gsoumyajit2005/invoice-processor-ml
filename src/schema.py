# src/schema.py

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Union, Dict
from decimal import Decimal, InvalidOperation
from datetime import date as DateType, datetime

# --- 1. Line Item Schema ---
class LineItem(BaseModel):
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    total: Decimal = Field(default=0, ge=0)

    @field_validator('unit_price', 'total', mode='before')
    @classmethod
    def validate_precision(cls, v):
        """Ensure exactly 2 decimal places for currency."""
        if v is None:
            return None
        try:
            d = Decimal(str(v))
            return d.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')

# --- 2. Invoice Schema ---
class InvoiceData(BaseModel):
    """
    Strict Data Contract for Invoice Extraction.
    """
    # Core Fields
    receipt_number: Optional[str] = Field(default=None, description="Unique ID")
    
    date: Optional[DateType] = Field(default=None, description="Invoice Date")
    
    # Financials
    total_amount: Optional[Decimal] = Field(default=None, ge=0)
    
    # Entities
    vendor: Optional[str] = None
    address: Optional[str] = None
    bill_to: Optional[Union[str, Dict]] = None 
    
    # Nested Items
    items: List[LineItem] = Field(default_factory=list)

    # --- METADATA ---
    validation_status: str = Field(default="unknown", description="passed/failed")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation failure messages")
    semantic_hash: Optional[str] = Field(default=None, description="Unique fingerprint of the invoice content")

    # --- VALIDATORS ---

    @field_validator('date', mode='before')
    @classmethod
    def clean_date(cls, v):
        """Logic: Handle None, parse formats, then validate range."""
        if not v: 
            return None
        
        parsed_date = v
        
        if isinstance(v, str):
            try:
                # Try common formats
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
                    try:
                        parsed_date = datetime.strptime(v, fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                return None 

        if isinstance(parsed_date, DateType):
            today = datetime.now().date()
            if parsed_date > today:
                return None 
            
            # ⚠️ FIX: Use 'DateType' constructor
            min_date = DateType(today.year - 10, 1, 1)
            if parsed_date < min_date:
                return None
            
            return parsed_date
            
        return None

    @field_validator('total_amount', mode='before')
    @classmethod
    def validate_money(cls, v):
        if v is None: 
            return None
        try:
            d = Decimal(str(v))
            return d.quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            return None

    @model_validator(mode='after')
    def validate_math(self):
        if not self.items or self.total_amount is None:
            return self
        
        line_items_sum = sum(item.total for item in self.items)
        diff = abs(self.total_amount - line_items_sum)
        
        if diff > Decimal('0.05'):
            print(f"⚠️ Validation Warning: Total {self.total_amount} != Sum of items {line_items_sum}")
            
        return self