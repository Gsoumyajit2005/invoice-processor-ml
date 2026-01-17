# src/extraction.py

import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from difflib import SequenceMatcher

def extract_dates(text: str) -> List[str]:
    """
    Robust date extraction that handles:
    - Numeric formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    - Text month formats: 22 Mar 18, March 22, 2018, 22-Mar-2018
    - OCR noise like pipes (|) instead of slashes
    Validates using datetime to ensure semantic correctness.
    """
    if not text: return []
    
    # Month name mappings
    MONTH_MAP = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    valid_dates = []
    
    # Pattern 1: Numeric dates - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD MM YYYY
    # Also handles OCR noise like pipes (|) instead of slashes
    numeric_pattern = r'\b(\d{1,2})[\s/|.-](\d{1,2})[\s/|.-](\d{2,4})\b'
    for d, m, y in re.findall(numeric_pattern, text):
        try:
            year = int(y)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            dt = datetime(year, int(m), int(d))
            valid_dates.append(dt.strftime("%d/%m/%Y"))
        except ValueError:
            continue
    
    # Pattern 2: DD Mon YY/YYYY (e.g., "22 Mar 18", "22-Mar-2018", "22 March 2018")
    text_month_pattern1 = r'\b(\d{1,2})[\s/.-]?([A-Za-z]{3,9})[\s/.-]?(\d{2,4})\b'
    for d, m, y in re.findall(text_month_pattern1, text, re.IGNORECASE):
        month_num = MONTH_MAP.get(m.lower())
        if month_num:
            try:
                year = int(y)
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                dt = datetime(year, month_num, int(d))
                valid_dates.append(dt.strftime("%d/%m/%Y"))
            except ValueError:
                continue
    
    # Pattern 3: Mon DD, YYYY (e.g., "March 22, 2018", "Mar 22 2018")
    text_month_pattern2 = r'\b([A-Za-z]{3,9})[\s.-]?(\d{1,2})[,\s.-]+(\d{2,4})\b'
    for m, d, y in re.findall(text_month_pattern2, text, re.IGNORECASE):
        month_num = MONTH_MAP.get(m.lower())
        if month_num:
            try:
                year = int(y)
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                dt = datetime(year, month_num, int(d))
                valid_dates.append(dt.strftime("%d/%m/%Y"))
            except ValueError:
                continue
    
    # Pattern 4: YYYY-MM-DD (ISO format)
    iso_pattern = r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'
    for y, m, d in re.findall(iso_pattern, text):
        try:
            dt = datetime(int(y), int(m), int(d))
            valid_dates.append(dt.strftime("%d/%m/%Y"))
        except ValueError:
            continue
            
    return list(dict.fromkeys(valid_dates))  # Deduplicate while preserving order

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
    if not text: return None

    # 1. BLOCK LIST: Words that might be captured as the ID itself by mistake
    FORBIDDEN_WORDS = {
        'INVOICE', 'TAX', 'RECEIPT', 'BILL', 'NUMBER', 'NO', 'DATE', 
        'ORIGINAL', 'COPY', 'GST', 'REG', 'MEMBER', 'SLIP', 'TEL', 'FAX'
    }

    # 2. TOXIC CONTEXTS: If a line contains these, it's likely a Tax ID or Phone #, not an Invoice #
    # We skip the line entirely if these are found (unless "INVOICE" is also strictly present)
    TOXIC_LINE_INDICATORS = ['GST', 'REG', 'SSM', 'TIN', 'PHONE', 'TEL', 'FAX', 'UBL', 'UEN']

    # Strategy 1: Explicit Label Search (High Confidence)
    # matches "Invoice No:", "Slip No:", "Bill #:", etc.
    # ADDED: 'SLIP' to the valid prefixes
    keyword_pattern = r'(?i)(?:TAX\s*)?(?:INVOICE|INV|BILL|RECEIPT|SLIP)\s*(?:NO|NUMBER|#|NUM)\s*[:\.]?\s*([A-Z0-9\-/]+)'
    matches = re.findall(keyword_pattern, text)
    
    for match in matches:
        clean_match = match.strip()
        # Verify length and ensure the match itself isn't a forbidden word
        if len(clean_match) >= 3 and clean_match.upper() not in FORBIDDEN_WORDS:
            return clean_match

    # Strategy 2: Contextual Line Search (Medium Confidence)
    # We scan line-by-line for loose patterns like "No: 12345" or "Slip: 555"
    lines = text.split('\n')
    for line in lines[:25]: # Scan top 25 lines
        line_upper = line.upper()

        # CRITICAL FIX: Skip lines that look like Tax IDs (GST/REG)
        # But allow if the line explicitly says "INVOICE" (e.g. "Tax Invoice / GST Reg No")
        if any(bad in line_upper for bad in TOXIC_LINE_INDICATORS) and "INVOICE" not in line_upper:
            continue

        # Look for Invoice-like keywords (Added SLIP)
        # matches " NO", " #", "SLIP"
        if any(k in line_upper for k in ['INVOICE', ' NO', ' #', 'INV', 'SLIP', 'BILL']):
            
            # Find candidate tokens: 3+ alphanumeric chars
            tokens = re.findall(r'\b[A-Z0-9\-/]{3,}\b', line_upper)
            
            for token in tokens:
                if token in FORBIDDEN_WORDS:
                    continue
                
                # Heuristic: Invoice numbers almost always have digits.
                # This filters out purely alpha strings like "CREDIT" or "CASH"
                if any(c.isdigit() for c in token):
                    return token

    return None

def extract_bill_to(text: str) -> Optional[Dict[str, str]]:
    if not text: return None
    
    # Look for "Bill To" block
    match = re.search(r'(?:BILL|BILLED)\s*TO[:\s]+([^\n]+)', text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        return {"name": name, "email": None}
    return None

def extract_address(text: str, vendor_name: Optional[str] = None) -> Optional[str]:
    """
    Generalized Address Extraction using Spatial Heuristics.
    Strategy:
    1. If Vendor is known, look at the lines immediately FOLLOWING it (Spatial).
    2. If Vendor is unknown, look for lines in the top header with 'Address-like' traits
       (mix of text + numbers, 3+ words, contains Zip-code-like patterns).
    """
    if not text: return None
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # --- FILTERS (Generalized) ---
    # Skip lines that are clearly NOT addresses
    def is_invalid_line(line):
        line_upper = line.upper()
        # 1. It's a Phone/Fax/Email/URL
        if any(x in line_upper for x in ['TEL', 'FAX', 'PHONE', 'EMAIL', '@', 'WWW.', '.COM', 'HTTP']):
            return True
        # 2. It's a Date
        if len(line) < 15 and any(c.isdigit() for c in line) and ('/' in line or '-' in line):
            return True
        # 3. It's the Vendor name itself (if provided)
        if vendor_name and vendor_name.lower() in line.lower():
            return True
        return False

    # --- STRATEGY 1: Contextual Search (Below Vendor) ---
    # This is the most accurate method for receipts worldwide.
    candidate_lines = []
    
    if vendor_name:
        vendor_found = False
        # Find where the vendor appears
        for i, line in enumerate(lines[:15]): # Check top 15 lines only
            if vendor_name.lower() in line.lower() or (len(vendor_name) > 5 and SequenceMatcher(None, vendor_name, line).ratio() > 0.8):
                vendor_found = True
                # Grab the next 1-3 lines as the potential address block
                # We stop if we hit a phone number or blank line
                for j in range(1, 4): 
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        if not is_invalid_line(next_line):
                            candidate_lines.append(next_line)
                        else:
                            # If we hit a phone number, the address block usually ended
                            break 
                break
    
    # If Strategy 1 found something, join it and return
    if candidate_lines:
        return ", ".join(candidate_lines)

    # --- STRATEGY 2: Header Scan (Density Heuristic) ---
    # If we couldn't anchor to the vendor, we scan the top 10 lines for "Address-looking" text.
    # An address usually has:
    # - At least one digit (Building number, Zip code)
    # - At least 3 words
    # - Is NOT a phone number
    # 
    # CONTIGUITY RULE: Once we start collecting candidates, we STOP at the first
    # invalid line (phone/fax/etc). This prevents capturing non-adjacent lines
    # like GST numbers that appear after phone numbers.
    
    fallback_candidates = []
    started_collecting = False
    
    for line in lines[:10]:
        if is_invalid_line(line):
            # If we've already started collecting, an invalid line means 
            # the address block has ended - don't continue past it
            if started_collecting:
                break
            continue
            
        # Check for Address Density:
        # 1. Has digits (e.g. "123 Main St" or "Singapore 55123")
        has_digits = any(c.isdigit() for c in line)
        # 2. Length is substantial (avoid short noise)
        is_long_enough = len(line) > 10
        # 3. Has spaces (at least 2 spaces => 3 words)
        is_multi_word = line.count(' ') >= 2
        
        # FIRST line must have digits (to anchor on building/street number)
        # CONTINUATION lines only need length + multi-word (city/state names often lack digits)
        is_valid_first_line = has_digits and is_long_enough and is_multi_word
        is_valid_continuation = started_collecting and is_long_enough and is_multi_word
        
        if is_valid_first_line or is_valid_continuation:
            # We found a strong candidate line
            fallback_candidates.append(line)
            started_collecting = True
            # If we have 3 candidates, that's probably the full address block
            if len(fallback_candidates) >= 3:
                break
                
    if fallback_candidates:
        return ", ".join(fallback_candidates)

    return None

def extract_line_items(text: str) -> List[Dict[str, Any]]:
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