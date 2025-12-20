import streamlit as st
import os
import json
from datetime import datetime
from PIL import Image
import numpy as np
import pandas as pd
from pathlib import Path

# Import our actual, working pipeline function
import sys
sys.path.append('src')
from pipeline import process_invoice

# --- Mock Functions (KEPT AS IS) ---
def detect_invoice_format(ocr_text: str):
    """
    A mock function to simulate format detection.
    In a real system, this would analyze the text layout.
    """
    if "SDN BHD" in ocr_text:
        return {
            'name': 'Template A (Retail)',
            'confidence': 95.0,
            'supported': True,
            'indicators': ["Found 'SDN BHD' suffix", "Date format DD/MM/YYYY detected"]
        }
    else:
        return {
            'name': 'Unknown Format',
            'confidence': 20.0,
            'supported': False,
            'indicators': ["No known company suffixes found"]
        }

def get_format_recommendations(format_info):
    """Mock recommendations based on the detected format."""
    if format_info['supported']:
        return ["• Extraction should be highly accurate."]
    else:
        return ["• Results may be incomplete.", "• Consider adding patterns for this format."]

# --- Streamlit App (KEPT AS IS) ---

st.set_page_config(
    page_title="Invoice Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (KEPT AS IS)
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title & Sidebar (KEPT AS IS)
st.markdown('<h1 class="main-header">📄 Smart Invoice Processor</h1>', unsafe_allow_html=True)
st.markdown("### Extract structured data from invoices using your custom-built OCR pipeline")

with st.sidebar:
    st.header("ℹ️ About")
    st.info("""
    This app uses the pipeline you built to automatically extract:
    - Receipt/Invoice number
    - Date
    - Customer information
    - Line items
    - Total amount
    
    **Technology Stack:**
    - Tesseract OCR
    - OpenCV
    - Python Regex
    - Streamlit
    """)
    
    st.header("📊 Stats")
    if 'processed_count' not in st.session_state:
        st.session_state.processed_count = 0
    st.metric("Invoices Processed Today", st.session_state.processed_count)

    st.header("⚙️ Configuration")
    extraction_method = st.selectbox(
        "Choose Extraction Method:",
        ('ML-Based (LayoutLMv3)', 'Rule-Based (Regex)'),
        help="ML-Based is more robust. Rule-Based is faster."
    )

# Main content
tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📚 Sample Invoices", "ℹ️ How It Works"])

with tab1:
    st.header("Upload an Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose an invoice image (JPG, PNG) or PDF", 
        type=['jpg', 'jpeg', 'png', 'pdf'], # Added PDF support
        help="Upload a clear image or PDF of an invoice"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📸 Original Document")
            # Preview Logic updated for PDF support
            if uploaded_file.type == "application/pdf":
                st.info("📄 PDF Uploaded (Preview not supported directly)")
            else:
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)
            st.caption(f"Filename: {uploaded_file.name}")
        
        with col2:
            st.subheader("🔄 Processing Status")
            
            if st.button("🚀 Extract Data", type="primary"):
                with st.spinner("Executing your custom pipeline..."):
                    try:
                        # Save temp file
                        temp_dir = "temp"
                        os.makedirs(temp_dir, exist_ok=True)
                        temp_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Call Pipeline
                        st.write("✅ Calling `process_invoice`...")
                        method = 'ml' if extraction_method == 'ML-Based (LayoutLMv3)' else 'rules'
                        st.write(f"⚙️ Using **{method.upper()}** extraction method...")

                        # ⚠️ UPDATE: Pass string path
                        extracted_data = process_invoice(str(temp_path), method=method)
                        
                        st.write("✅ Simulating format detection...")
                        format_info = detect_invoice_format(extracted_data.get("raw_text", ""))
                        
                        st.session_state.extracted_data = extracted_data
                        st.session_state.format_info = format_info
                        st.session_state.processed_count += 1
                        
                        st.success("✅ Pipeline executed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ An error occurred in the pipeline: {str(e)}")
        
        # Display results
        if 'extracted_data' in st.session_state:
            st.markdown("---")
            st.header("📊 Extraction Results")

            # --- Format Detection Section (KEPT AS IS) ---
            format_info = st.session_state.format_info
            st.subheader("📋 Detected Format (Simulated)")
            col1_fmt, col2_fmt = st.columns([2, 3])
            with col1_fmt:
                st.metric("Format Type", format_info['name'])
                st.metric("Detection Confidence", f"{format_info['confidence']:.0f}%")
                if format_info['supported']: st.success("✅ Fully Supported")
                else: st.warning("⚠️ Limited Support")
            with col2_fmt:
                st.write("**Detected Indicators:**")
                for indicator in format_info['indicators']: st.write(f"• {indicator}")
                st.write("**Recommendations:**")
                for rec in get_format_recommendations(format_info): st.write(rec)
            st.markdown("---")
            
            # --- Main Results Section (UPDATED) ---
            data = st.session_state.extracted_data
            
            # 1. New Validation Display (Replaces old Confidence box)
            status = data.get('validation_status', 'unknown')
            if status == 'passed':
                st.markdown(f'<div class="success-box">✅ <strong>Validation Passed</strong>: Data meets strict quality rules (Pydantic).</div>', unsafe_allow_html=True)
            elif status == 'failed':
                err_count = len(data.get('validation_errors', []))
                st.markdown(f'<div class="error-box">❌ <strong>Validation Failed</strong>: Found {err_count} issues. Check JSON for details.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="warning-box">⚠️ <strong>Status Unknown</strong>: Validation logic was skipped.</div>', unsafe_allow_html=True)

            # 2. Key Metrics (Mapped to NEW keys)
            st.metric("🏢 Vendor", data.get('vendor') or "N/A")

            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("📄 Receipt Number", data.get('receipt_number') or "N/A")
            res_col2.metric("📅 Date", data.get('date') or "N/A")
            # Handle total (it's now a string from the pipeline, but metric handles strings fine)
            total = data.get('total_amount')
            res_col3.metric("💵 Total Amount", f"${total}" if total else "N/A")

            # 3. Expanded Details
            with st.expander("Show More Details"):
                st.markdown(f"**🧾 Receipt Number:** {data.get('receipt_number') or 'N/A'}")
                
                # Handle bill_to
                bill_to = data.get('bill_to')
                if isinstance(bill_to, dict):
                    bill_to_display = bill_to.get('name') or 'N/A'
                elif isinstance(bill_to, str):
                    bill_to_display = bill_to
                else:
                    bill_to_display = 'N/A'
                st.markdown(f"**👤 Bill To:** {bill_to_display}")
                
                st.markdown(f"**📍 Vendor Address:** {data.get('address') or 'N/A'}")
                
                # New: Show Duplicate Hash
                st.markdown(f"**🔑 Semantic Hash (Duplicate ID):** `{data.get('semantic_hash') or 'N/A'}`")

            # 4. Line items table
            if data.get('items'):
                st.subheader("🛒 Line Items")
                items_df_data = [{
                    "Description": item.get("description", "N/A"),
                    "Qty": item.get("quantity", "N/A"),
                    "Unit Price": f"${item.get('unit_price', 0.0) if item.get('unit_price') is not None else 0}",
                    "Total": f"${item.get('total', 0.0) if item.get('total') is not None else 0}"
                } for item in data['items']]
                df = pd.DataFrame(items_df_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("ℹ️ No line items were extracted.")
            
            # JSON output and download
            with st.expander("📄 View Full JSON Output"):
                st.json(data)
            
            json_str = json.dumps(data, indent=2)
            st.download_button(
                label="💾 Download JSON",
                data=json_str,
                file_name=f"invoice_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            with st.expander("📝 View Raw OCR Text"):
                raw_text = data.get('raw_text', '')
                if raw_text:
                    st.text(raw_text)
                else:
                    st.info("No OCR text available.")

with tab2:
    st.header("📚 Sample Invoices")
    st.write("Try the sample invoice below to see how the system performs:")
    
    sample_dir = "data/samples"
    if os.path.exists(sample_dir):
        sample_files = [f for f in os.listdir(sample_dir) if f.endswith(('.jpg', '.png', '.jpeg', '.pdf'))]
        
        if sample_files:
            file_path = os.path.join(sample_dir, sample_files[0])
            st.write(f"**Sample File:** {sample_files[0]}")
            if file_path.endswith('.pdf'):
                 st.info("📄 PDF Sample available. Download and upload it to test.")
            else:
                st.image(Image.open(file_path), caption=sample_files[0], use_container_width=True)
        else:
            st.warning("No sample invoices found in `data/samples/`.")
    else:
        st.error("The `data/samples` directory was not found.")

with tab3:
    st.header("ℹ️ How It Works (Your Custom Pipeline)")
    st.markdown("""
    This app follows the exact pipeline you built:
    ```
    1. 📸 Input Handling
       Detects JPG vs PDF. Smart Loader extracts text from PDFs instantly.
       ↓
    2. 🧠 Hybrid Engine
       - Digital PDFs: Direct Text Extraction (Fast)
       - Images/Scans: LayoutLMv3 (ML) + Tesseract (OCR)
       ↓
    3. 🛡️ Validation Gate
       Pydantic Schema ensures data integrity (Decimal precision, Date formats).
       ↓
    4. 🔑 Duplicate Detection
       Generates a unique semantic hash based on content.
       ↓
    5. 📊 Output JSON
       Standardized, validated output ready for API response.
    ```
    """)