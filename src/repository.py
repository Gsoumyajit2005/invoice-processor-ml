# src/repository.py

from sqlmodel import Session, select
from typing import Dict, Any, Optional
import json
from datetime import date

from src.models import Invoice, LineItem
from src.database import get_session, engine, DB_CONNECTED

class InvoiceRepository:
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize with an optional session. 
        If no session is provided, try to get a new one from the engine.
        Only creates session if database is actually connected.
        """
        if session:
            self.session = session
        elif engine and DB_CONNECTED:
            self.session = Session(engine)
        else:
            self.session = None

    def save_invoice(self, invoice_data: Dict[str, Any]) -> Optional[Invoice]:
        """
        Saves an invoice and its line items to the database.
        Returns the saved Invoice object or None if DB is disabled/failed.
        """
        if not self.session:
            print("⚠️ DB Session missing. Skipping save.")
            return None

        try:
            # 1. Prepare Data
            data = invoice_data.copy()
            
            # Serialize complex types (validation_errors)
            if 'validation_errors' in data and isinstance(data['validation_errors'], list):
                data['validation_errors'] = json.dumps(data['validation_errors'])
            
            # Extract items to process separately
            items_data = data.pop('items', [])
            
            # 2. Create Invoice Record
            invoice = Invoice(**data)
            
            # 3. Process Items
            for item in items_data:
                # Ensure item is a dict (if it's a Pydantic model, convert it)
                if hasattr(item, 'model_dump'):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    continue
                    
                line_item = LineItem(**item_dict)
                invoice.items.append(line_item)
            
            # 4. Commit
            self.session.add(invoice)
            self.session.commit()
            self.session.refresh(invoice)
            
            print(f"✅ Invoice {invoice.id} saved to DB.")
            return invoice

        except Exception as e:
            print(f"❌ Error saving invoice to DB: {e}")
            self.session.rollback()
            return None

    def get_by_hash(self, semantic_hash: str) -> Optional[Invoice]:
        """
        Check if invoice already exists using the semantic hash.
        """
        if not self.session:
            return None

        try:
            statement = select(Invoice).where(Invoice.semantic_hash == semantic_hash)
            results = self.session.exec(statement)
            return results.first()
        except Exception as e:
            print(f"❌ Error checking hash: {e}")
            return None