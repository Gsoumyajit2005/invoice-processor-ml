# src/extraction.py

import re
from typing import List, Dict, Optional, Any
from datetime import datetime

def extract_dates(text: str) -> List[str]:
    """
    Robust date extraction that handles noisy OCR separators (spaces, pipes, dots)
    and validates using datetime to ensure semantic correctness.
    """
    if not text: return []
    
    # Matches DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD MM YYYY
    # Also handles OCR noise like pipes (|) instead of slashes
    pattern = r'\b(\d{1,2})[\s/|.-](\d{1,2})[\s/|.-](\d{2,4})\b'
    matches = re.findall(pattern, text)
    
    valid_dates = []
    for d, m, y in matches:
        try:
            # Try to parse it to check if it's a real date
            # This filters out "99/99/2000" or random phone numbers like 12 34 5678
            # Assuming Day-Month-Year format which is common in SROIE/International
            # For US format, you might swap d and m
            dt = datetime(int(y), int(m), int(d))
            valid_dates.append(dt.strftime("%d/%m/%Y"))
        except ValueError:
            continue # Invalid date logic (e.g. Month 13 or Day 32)
            
    return list(dict.fromkeys(valid_dates)) # Deduplicate

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
    Robust total extraction using keyword confidence + Footer Search.
    """
    if not text: return None
    
    # 1. Try specific "Total" keywords first (Highest Confidence)
    # Looks for "Total: 123.45" or "Total Amount $123.45"
    pattern = r'(?:TOTAL|AMOUNT DUE|GRAND TOTAL|BALANCE|PAYABLE)[\w\s]*[:$]?\s*([\d,]+\.\d{2})'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    if matches:
        # Return the last match (often the grand total at bottom)
        try:
            return float(matches[-1].replace(',', ''))
        except ValueError:
            pass
            
    # 2. Fallback: Context-Aware Footer Search (Medium Confidence)
    # Instead of taking max() of the whole doc (risky), we only look at the bottom 30%
    lines = text.split('\n')
    if not lines: return None

    # Focus on the footer where totals usually live
    footer_lines = lines[-int(len(lines)*0.3):] 
    
    candidates = []
    for line in footer_lines:
        line_amounts = extract_amounts(line)
        for amt in line_amounts:
            # Simple heuristic: Totals are rarely 'years' like 2024 or 2025
            if 2000 <= amt <= 2030 and float(amt).is_integer():
                continue
            candidates.append(amt)
            
    if candidates:
        return max(candidates)

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
    Improved regex that handles alphanumeric AND numeric IDs, plus variations like "Tax Inv".
    """
    if not text: return None
    
    # Strategy 1: Look for "Invoice No: XXXXX" pattern
    # UPDATED: Handles "Tax Invoice", "Inv No", and standard variations
    keyword_pattern = r'(?:TAX\s*)?(?:INVOICE|INV|BILL|RECEIPT)\s*(?:NO|NUMBER|#|NUM)?[\s\.:-]*([A-Z0-9\-/]{3,})'
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