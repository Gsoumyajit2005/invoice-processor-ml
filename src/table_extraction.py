# src/table_extraction.py

from typing import List, Dict, Any
import re

# Common phrases that indicate NON-item text (should be filtered out)
EXCLUDE_PHRASES = [
    "thank you", "thank", "goods sold", "not returnable", "returnable",
    "shopping at", "visit again", "customer copy", "merchant copy",
    "powered by", "terms and conditions", "t&c apply", "cashier",
    "counter", "sdn bhd", "bhd", "pte ltd", "pvt ltd", "llc", "inc",
    "gst summary", "tax summary", "payment", "change", "cash",
    "credit card", "debit card", "subtotal", "sub total", "grand total",
    "total includes", "includes gst", "tax invoice", "invoice"
]

def extract_table_items(words: List[str], boxes: List[List[int]]) -> List[Dict[str, Any]]:
    """
    Geometric Heuristic to extract table rows.
    Logic:
    1. Find 'Header' Y-position (words like 'Description', 'Item', 'Qty').
    2. Find 'Footer' Y-position (where 'Total' usually sits).
    3. Filter all words strictly BETWEEN Header and Footer.
    4. Group remaining words into 'Rows' based on similar Y-coordinates.
    """
    
    if not words or not boxes:
        return []
    
    # 1. Identify Anchor Points
    header_y = 0
    footer_y = float('inf')
    
    header_keywords = ["description", "item", "particulars", "qty", "quantity", "price", "amount", "rate", "uom", "unit"]
    footer_keywords = ["total", "subtotal", "tax", "grand total", "payment", "cash", "change", "gst summary", "tax summary"]
    
    # Scan for Header (Top boundary)
    for i, word in enumerate(words):
        if word.lower() in header_keywords:
            y_bottom = boxes[i][1] + boxes[i][3]
            if y_bottom > header_y:
                header_y = y_bottom

    # Scan for Footer (Bottom boundary)
    for i, word in enumerate(words):
        if word.lower() in footer_keywords:
            y_top = boxes[i][1]
            if y_top < footer_y and y_top > header_y: 
                footer_y = y_top

    # If no header found, assume top 25% is header
    if header_y == 0 and boxes:
        max_y = max(b[1] for b in boxes)
        header_y = max_y * 0.25
    
    # If no footer found, assume bottom 25% is footer
    if footer_y == float('inf') and boxes:
        max_y = max(b[1] for b in boxes)
        footer_y = max_y * 0.75

    # 2. Filter Content (The "Sandwich" Meat)
    table_words = []
    for i, word in enumerate(words):
        bx, by, bw, bh = boxes[i]
        if by > header_y and (by + bh) < footer_y:
            table_words.append({"text": word, "box": boxes[i]})

    # 3. Group by Rows (Y-clustering)
    rows = []
    if not table_words:
        return []

    table_words.sort(key=lambda x: x["box"][1])
    
    current_row = [table_words[0]]
    current_y = table_words[0]["box"][1]
    
    for item in table_words[1:]:
        y = item["box"][1]
        if abs(y - current_y) < 15:
            current_row.append(item)
        else:
            current_row.sort(key=lambda x: x["box"][0])
            rows.append(current_row)
            current_row = [item]
            current_y = y
            
    if current_row:
        current_row.sort(key=lambda x: x["box"][0])
        rows.append(current_row)

    # 4. Convert Rows to Structured Dicts with FILTERING
    structured_items = []
    
    for row in rows:
        full_text = " ".join([w["text"] for w in row])
        full_text_lower = full_text.lower()
        
        # Skip rows that match exclude phrases
        if any(phrase in full_text_lower for phrase in EXCLUDE_PHRASES):
            continue
        
        # Skip very short rows (likely noise)
        if len(full_text.strip()) < 3:
            continue
        
        # Find all numbers (potential prices)
        # Match patterns like: 0.90, 12.50, 1,234.56
        numbers = re.findall(r'\d{1,3}(?:,\d{3})*\.?\d*', full_text)
        
        item_obj = {
            "description": full_text, 
            "quantity": 1, 
            "unit_price": 0.0, 
            "total": 0.0
        }
        
        if numbers:
            try:
                # Clean and convert last number as price
                val = float(numbers[-1].replace(',', ''))
                
                # Skip if price is 0 or unreasonably small for a line item
                if val <= 0:
                    continue
                    
                item_obj["total"] = val
                item_obj["unit_price"] = val
                # Remove the price from description
                item_obj["description"] = full_text.replace(numbers[-1], "").strip()
                
                # Skip if description is now empty or too short
                if len(item_obj["description"].strip()) < 2:
                    continue
                    
            except:
                continue
        else:
            # No numbers found = not a valid line item
            continue
                
        structured_items.append(item_obj)

    return structured_items