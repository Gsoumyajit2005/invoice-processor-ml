import re
from typing import List, Dict, Optional, Any


def extract_dates(text: str) -> List[str]:
    if not text:
        return []
    
    dates = []

    pattern1 = r'\d{2}[/-]\d{2}[/-]\d{4}'
    pattern2 = r'\d{2}[/-]\d{2}[/-]\d{2}(?!\d)'
    pattern3 = r'\d{4}[/-]\d{2}[/-]\d{2}'

    dates.extend(re.findall(pattern1, text))
    dates.extend(re.findall(pattern2, text))
    dates.extend(re.findall(pattern3, text))

    dates = list(dict.fromkeys(dates))
    return dates


def extract_amounts(text:  str) -> List[float]:
    if not text:
        return []
    # Matches: 123.45, 1,234.56, $123.45, 123.45 RM
    pattern = r'(?:RM|Rs\.?|\$|€)?\s*\d{1,3}(?:,\d{3})*[.,]\d{2}'
    amounts_strings = (re.findall(pattern, text))
    
    amounts = []
    for amt_str in amounts_strings:
        amt_cleaned = re.sub(r'[^\d.,]', '', amt_str)
        amt_cleaned = amt_cleaned.replace(',', '.')
        try:
            amounts.append(float(amt_cleaned))
        except ValueError:
            continue
    return amounts


def extract_total(text: str) -> Optional[float]:
    if not text:
        return None

    pattern = r'(?:TOTAL|GRAND\s*TOTAL|AMOUNT\s*DUE|BALANCE)\s*:?\s*(\d+[.,]\d{2})'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
            amount_str = match.group(1).replace(',', '.')
            return float(amount_str)

    return None


def extract_vendor(text: str) -> Optional[str]:
    if not text:
        return None
    
    lines = text.strip().split('\n')

    company_suffixes = ['SDN BHD', 'INC', 'LTD', 'LLC', 'PLC', 'CORP', 'PTY', 'PVT']

    for line in lines:
        line = line.strip()

        # Skip empty or very short line
        if len(line) < 3:
            continue
            
        # Skip lines with only symbols
        if all(c in '*-=_#' for c in line.replace(' ', '')):
            continue

        for suffix in company_suffixes:
            if suffix in line.upper():
                return line
            
    # If we've gone through 10 lines and found nothing, 
    # return the first substantial line
    # (Vendor is usually in first few lines)
    
    # Fallback: return first non-trivial line
    for line in lines[:10]:
        line = line.strip()
        if len(line) >= 3 and not all(c in '*-=_#' for c in line.replace(' ', '')):
            return line
    return None


def extract_invoice_number(text: str) -> Optional[str]:
    if not text:
        return None
    
    # Look for invoice number patterns (alphanumeric with hyphens, 5+ chars)
    # Typically near invoice-related text
    lines = text.split('\n')
    
    for line in lines[:15]:  # Check first 15 lines (invoice # is usually at top)
        # If line mentions anything invoice-related
        if any(keyword in line.lower() for keyword in ['nvoice', 'receipt', 'bill', 'no']):
            # Find alphanumeric patterns
            patterns = re.findall(r'[A-Z]{2,}[A-Z0-9\-]{3,}', line, re.IGNORECASE)
            for pattern in patterns:
                # Must be 5+ chars and contain both letters and numbers
                if (len(pattern) >= 5 and 
                    any(c.isdigit() for c in pattern) and 
                    any(c.isalpha() for c in pattern)):
                    return pattern.upper()
    
    return None


def extract_bill_to(text: str) -> Optional[Dict[str, str]]:
    if not text:
        return None
    
    bill_to = None

    # Normalize lines and remove empty lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Possible headings
    headings = ['bill to', 'billed to', 'billing name', 'customer']

    bill_to_text = None
    for i, line in enumerate(lines):
        lower_line = line.lower()
        if any(h in lower_line for h in headings):
            # Capture text after colon or hyphen if present
            split_line = re.split(r'[:\-]', line, maxsplit=1)
            if len(split_line) > 1:
                bill_to_text = split_line[1].strip()
            else:
                # If name is on next line
                if i + 1 < len(lines):
                    bill_to_text = lines[i + 1].strip()
            break

    if not bill_to_text:
        return None

    # Extract email if present
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', bill_to_text)
    email = email_match.group(0) if email_match else None

    # Remove email from name
    if email:
        bill_to_text = bill_to_text.replace(email, '').strip()

    if len(bill_to_text) > 2:  # Basic validation
        bill_to = {"name": bill_to_text, "email": email}

    return bill_to


def extract_line_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from receipt text more robustly.
    Handles:
        - Multi-line descriptions
        - Prices with or without currency symbols
        - Quantities in different formats
        - Missing decimals
    
    Args:
        text: Raw OCR text
    
    Returns:
        List of dictionaries with description, quantity, unit_price, total
    """
    items = []
    lines = text.split('\n')

    # Keywords to detect start/end of item section
    start_keywords = ['description', 'item', 'qty', 'price', 'amount']
    end_keywords = ['total', 'subtotal', 'tax', 'gst']

    # Detect section
    start_index = -1
    end_index = len(lines)
    for i, line in enumerate(lines):
        lower = line.lower()
        if start_index == -1 and any(k in lower for k in start_keywords):
            start_index = i + 1
        if start_index != -1 and any(k in lower for k in end_keywords):
            end_index = i
            break

    if start_index == -1:
        return []

    item_lines = lines[start_index:end_index]

    current_description = ""
    for line in item_lines:
        # Remove currency symbols, commas, etc.
        clean_line = re.sub(r'[^\d\.\s]', '', line)
        
        # Find all numbers (floats or integers)
        amounts_on_line = re.findall(r'\d+(?:\.\d+)?', clean_line)

        # Attempt to detect quantity at the start: "2 ", "3 x", etc.
        qty_match = re.match(r'^\s*(\d+)\s*(?:x)?', line)
        quantity = int(qty_match.group(1)) if qty_match else 1

        # Extract description by removing numbers and common symbols
        desc_part = re.sub(r'[\d\.\s]+', '', line).strip()
        if len(desc_part) > 0:
            if current_description:
                current_description += " " + desc_part
            else:
                current_description = desc_part

        # If there are numbers and a description, create item
        if amounts_on_line and current_description:
            try:
                # Heuristic: last number is total, second last is unit price
                item_total = float(amounts_on_line[-1])
                unit_price = float(amounts_on_line[-2]) if len(amounts_on_line) > 1 else item_total

                items.append({
                    "description": current_description.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total": item_total
                })
                current_description = ""  # reset for next item
            except ValueError:
                current_description = ""
                continue

    return items


def structure_output(text: str) -> Dict[str, Any]:
    """
    Extract all information and return in the desired advanced format.
    """
    
    # Old fields
    date = extract_dates(text)[0] if extract_dates(text) else None
    total = extract_total(text)
    
    # New fields
    bill_to = extract_bill_to(text)
    items = extract_line_items(text)
    invoice_num = extract_invoice_number(text) # Renamed for clarity
    
    data = {
        "receipt_number": invoice_num,
        "date": date,
        "bill_to": bill_to,
        "items": items,
        "total_amount": total,
        "raw_text": text
    }
    
    # --- Confidence and Validation ---
    fields_to_check = ['receipt_number', 'date', 'bill_to', 'total_amount']
    extracted_fields = sum(1 for field in fields_to_check if data.get(field) is not None)
    if items: # Count items as an extracted field
        extracted_fields += 1
        
    data['extraction_confidence'] = int((extracted_fields / (len(fields_to_check) + 1)) * 100)
    
    # A more advanced validation
    items_total = sum(item.get('total', 0) for item in items)
    data['validation_passed'] = False
    if total is not None and abs(total - items_total) < 0.01: # Check if total matches sum of items
        data['validation_passed'] = True
        
    return data
    