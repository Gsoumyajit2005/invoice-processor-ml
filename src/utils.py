# src/utils.py

import hashlib
from typing import Dict, Any
from decimal import Decimal
from datetime import date

def generate_semantic_hash(invoice_data: Dict[str, Any]) -> str:
    """
    Generates a unique fingerprint using a Composite Key strategy.
    
    Composite Key = Vendor + Date + Total + Receipt Number
    """
    # Define the specific fields that determine uniqueness
    keys_to_hash = ['vendor', 'date', 'total_amount', 'receipt_number']
    normalized_values = []

    for key in keys_to_hash:
        value = invoice_data[key]

        # Normalize without modifying the original object
        if value is None:
           norm_val = ""
        elif isinstance(value, (date, Decimal, int, float)):
            norm_val = str(value)
        else:
            # String normalization
            norm_val = str(value).lower().strip()

        normalized_values.append(norm_val)    
    
    # Create the fingerprint string
    composite_string = "|".join(normalized_values)
    
    # Return the SHA256 hash of the string
    return hashlib.sha256(composite_string.encode()).hexdigest()
    