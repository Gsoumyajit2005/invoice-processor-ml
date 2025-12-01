# src/extraction.py

import re
from typing import List, Dict, Optional, Any

def extract_dates(text: str) -> List[str]:
    if not text: return []
    dates = []
    # DD/MM/YYYY or DD-MM-YYYY
    pattern1 = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    # YYYY-MM-DD
    pattern2 = r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
    
    dates.extend(re.findall(pattern1, text))
    dates.extend(re.findall(pattern2, text))
    return list(dict.fromkeys(dates))

def extract_amounts(text:  str) -> List[float]:
    if not text: return []
    # Matches: 1,234.56 or 1234.56
    pattern = r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b'
    amounts_strings = re.findall(pattern, text)
    
    amounts = []
    for amt_str in amounts_strings:
        amt_cleaned = amt_str.replace(',', '')
        try:
            amounts.append(float(amt_cleaned))
        except ValueError:
            continue
    return amounts

def extract_total(text: str) -> Optional[float]:
    """
    Robust total extraction looking for keywords + largest number context.
    """
    if not text: return None
    
    # 1. Try specific "Total" keywords first
    # Looks for "Total: 123.45" or "Total Amount $123.45"
    pattern = r'(?:TOTAL|AMOUNT DUE|GRAND TOTAL|BALANCE|PAYABLE)[\w\s]*[:$]?\s*([\d,]+\.\d{2})'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    if matches:
        # Return the last match (often the grand total at bottom)
        try:
            return float(matches[-1].replace(',', ''))
        except ValueError:
            pass
            
    # 2. Fallback: Find the largest monetary value in the bottom half of text
    # (Risky, but better than None)
    amounts = extract_amounts(text)
    if amounts:
        return max(amounts)

    return None

def extract_vendor(text: str) -> Optional[str]:
    if not text: return None
    lines = text.strip().split('\n')
    company_suffixes = ['SDN BHD', 'INC', 'LTD', 'LLC', 'PLC', 'CORP', 'PTY', 'PVT', 'LIMITED']

    for line in lines[:10]: # Check top 10 lines
        line_upper = line.upper()
        if any(suffix in line_upper for suffix in company_suffixes):
            return line.strip()
    
    # Fallback: Return first non-empty line that isn't a date
    for line in lines[:5]:
        if len(line.strip()) > 3 and not re.search(r'\d{2}/\d{2}', line):
             return line.strip()
    return None

def extract_invoice_number(text: str) -> Optional[str]:
    """
    Improved regex that handles alphanumeric AND numeric IDs.
    """
    if not text: return None
    
    # Strategy 1: Look for "Invoice No: XXXXX" pattern
    # Matches: "Invoice No: 12345", "Inv #: AB-123", "Bill No. 999"
    keyword_pattern = r'(?:INVOICE|BILL|RECEIPT)\s*(?:NO|NUMBER|#|NUM)?[\s\.:-]*([A-Z0-9\-/]{3,})'
    match = re.search(keyword_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Strategy 2: Look for standalone labeled patterns (Existing Logic)
    # Only if Strategy 1 fails
    lines = text.split('\n')
    for line in lines[:20]:
        if any(k in line.lower() for k in ['invoice', 'no', '#']):
            # Allow pure digits now if they are long enough (e.g. 40378170)
            # Match 4+ digits OR alphanumeric
            token_match = re.search(r'\b([A-Z0-9-]{4,})\b', line)
            if token_match:
                return token_match.group(1)
                
    return None

def extract_bill_to(text: str) -> Optional[Dict[str, str]]:
    if not text: return None
    
    # Look for "Bill To" block
    match = re.search(r'(?:BILL|BILLED)\s*TO[:\s]+([^\n]+)', text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        return {"name": name, "email": None}
    return None

def extract_line_items(text: str) -> List[Dict[str, Any]]:
    # (Keeping your existing logic simple for now)
    return []

def structure_output(text: str) -> Dict[str, Any]:
    """Legacy wrapper for rule-based-only pipeline"""
    return {
        "receipt_number": extract_invoice_number(text),
        "date": extract_dates(text)[0] if extract_dates(text) else None,
        "total_amount": extract_total(text),
        "vendor": extract_vendor(text),
        "raw_text": text
    }