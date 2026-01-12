import pytest
from unittest.mock import patch
from pathlib import Path
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import process_invoice

# --- MOCK DATA ---
# This is what we pretend the ML model returned
MOCK_ML_RESPONSE = {
    "vendor": "MOCKED VENDOR INC",
    "date": "2023-01-01",
    "total_amount": "100.00",
    "receipt_number": "MOCK-123",
    "address": "123 Mock Street",
    "bill_to": "Mock Customer",
    "items": [],
    "raw_text": "Mocked raw text content"
}

@patch('pipeline.extract_rule_based')
def test_pipeline_rule_based(mock_extract):
    mock_extract.return_value = MOCK_ML_RESPONSE

    with patch('pathlib.Path.exists', return_value=True):
        result = process_invoice("fake_invoice.jpg", method="rules")

    assert result['vendor'] == "MOCKED VENDOR INC"
    assert result['validation_status'] == "passed"
    mock_extract.assert_called_once()

@patch('pipeline.extract_ml_based')
def test_pipeline_ml_mocked(mock_extract):
    """
    Tests the ML pipeline WITHOUT loading the heavy model.
    """
    mock_extract.return_value = MOCK_ML_RESPONSE

    with patch('pathlib.Path.exists', return_value=True):
        result = process_invoice("fake_invoice.jpg", method="ml")

    assert result['vendor'] == "MOCKED VENDOR INC"
    assert result['receipt_number'] == "MOCK-123"
    assert result['validation_status'] == "passed"

    mock_extract.assert_called_once()
    
