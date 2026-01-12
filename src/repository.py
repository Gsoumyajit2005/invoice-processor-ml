# src/repository.py

from sqlmodel import Session, select
from typing import Dict, Any, Optional
import json

from src.models import Invoice, LineItem
from src.database import get_session, engine

class InvoiceRepository:
    def __init__(self, session: Session = None):
        """
        Initialize with an optional session. 
        Allows dependency injection for testing or API usage.
        """
        self.session = session

    def save_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """
        Saves an invoice and its line items to the database.
        
        Steps to implement:
        1. Manage Session: If self.session is None, create a new one using 'engine'.
        2. Clean Data: Separate 'items' list from the main invoice properties.
        3. Create Invoice: Instantiate the Invoice SQLModel.
        4. Deserialize Complex Types: e.g. 'validation_errors' list -> JSON string.
        5. Process Items: Iterate 'items', create LineItem models, check keys match, and append to invoice.items.
        6. Commit: Add to session, commit, and refresh.
        7. Error Handling: Wrap in try/except to rollback on failure.
        """
        # TODO: Implementation
        raise NotImplementedError("Implement the save logic.")

    def get_by_hash(self, semantic_hash: str) -> Optional[Invoice]:
        """
        Check if invoice already exists using the semantic hash.
        """
        # TODO: Create session if needed
        # TODO: Execute SELECT statement filtering by hash
        # TODO: Return first result or None
        raise NotImplementedError("Implement the query logic.")
