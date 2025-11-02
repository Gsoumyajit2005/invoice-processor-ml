import sys
sys.path.append('src')

from extraction import extract_dates, extract_amounts, extract_total, extract_vendor, extract_invoice_number

receipt_text = """
tan chay yee

*** COPY ***

OJC MARKETING SDN BHD.

ROC NO: 538358-H

TAX INVOICE

Invoice No: PEGIV-1030765
Date: 15/01/2019 11:05:16 AM

TOTAL: 193.00
"""

print("🧪 Testing Extraction Functions")
print("=" * 60)

dates = extract_dates(receipt_text)
print(f"\n📅 Date: {dates}")

amounts = extract_amounts(receipt_text)
print(f"\n💰 Amounts: {amounts}")

total = extract_total(receipt_text)
print(f"\n💵 Total: {total}")

vendor = extract_vendor(receipt_text)
print(f"\n🏢 Vendor: {vendor}")

invoice_num = extract_invoice_number(receipt_text)
print(f"\n📄 Invoice Number: {invoice_num}")

print("\n✅ All extraction tests complete!")