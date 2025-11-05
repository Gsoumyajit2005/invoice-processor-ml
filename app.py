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

# --- Mock Functions to support the UI without errors ---
# These functions simulate the ones from your example README.
# They allow the UI to render without needing to build a complex format detector today.

def detect_invoice_format(ocr_text: str):
    """
    A mock function to simulate format detection.
    In a real system, this would analyze the text layout.
    """
    # Simple heuristic: if it contains "SDN BHD", it's our known format.
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

# --- Streamlit App ---

# Page configuration
st.set_page_config(
    page_title="Invoice Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
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

# Title
st.markdown('<h1 class="main-header">📄 Smart Invoice Processor</h1>', unsafe_allow_html=True)
st.markdown("### Extract structured data from invoices using your custom-built OCR pipeline")

# Sidebar
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
        help="ML-Based is more robust but may miss fields not in its training data. Rule-Based is faster but more fragile."
    )

# Main content
tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📚 Sample Invoices", "ℹ️ How It Works"])

with tab1:
    st.header("Upload an Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose an invoice image (JPG, PNG)", 
        type=['jpg', 'jpeg', 'png'],
        help="Upload a clear image of an invoice or receipt"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📸 Original Image")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            st.caption(f"Filename: {uploaded_file.name}")
        
        with col2:
            st.subheader("🔄 Processing Status")
            
            if st.button("🚀 Extract Data", type="primary"):
                with st.spinner("Executing your custom pipeline..."):
                    try:
                        # Save the uploaded file to a temporary path to be used by our pipeline
                        temp_dir = "temp"
                        os.makedirs(temp_dir, exist_ok=True)
                        temp_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Step 1: Call YOUR full pipeline function
                        st.write("✅ Calling `process_invoice`...")
                        # Map the user-friendly name from the dropdown to the actual method parameter
                        method = 'ml' if extraction_method == 'ML-Based (LayoutLMv3)' else 'rules'
                        st.write(f"⚙️ Using **{method.upper()}** extraction method...")

                        # Call the pipeline with the selected method
                        extracted_data = process_invoice(temp_path, method=method)
                        
                        # Step 2: Simulate format detection using the extracted data
                        st.write("✅ Simulating format detection...")
                        format_info = detect_invoice_format(extracted_data.get("raw_text", ""))
                        
                        # Store results in session state to display them
                        st.session_state.extracted_data = extracted_data
                        st.session_state.format_info = format_info
                        st.session_state.processed_count += 1
                        
                        st.success("✅ Pipeline executed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ An error occurred in the pipeline: {str(e)}")
        
        # Display results if they exist in the session state
        if 'extracted_data' in st.session_state:
            st.markdown("---")
            st.header("📊 Extraction Results")

            # --- Format Detection Section ---
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
            
            # --- Main Results Section ---
            data = st.session_state.extracted_data
            
            # Confidence display
            confidence = data.get('extraction_confidence', 0)
            if confidence >= 80:
                st.markdown(f'<div class="success-box">✅ <strong>High Confidence: {confidence}%</strong> - Most key fields were found.</div>', unsafe_allow_html=True)
            elif confidence >= 50:
                st.markdown(f'<div class="warning-box">⚠️ <strong>Medium Confidence: {confidence}%</strong> - Some fields may be missing.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="error-box">❌ <strong>Low Confidence: {confidence}%</strong> - Format likely unsupported.</div>', unsafe_allow_html=True)

            # Validation display
            if data.get('validation_passed', False):
                st.success("✔️ Validation Passed: Total amount appears consistent with other extracted amounts.")
            else:
                st.warning("⚠️ Validation Failed: Total amount could not be verified against other numbers.")

            # Key metrics display
            # Key metrics display
            st.metric("🏢 Vendor", data.get('vendor') or "N/A") # <-- ADD THIS

            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("📄 Receipt Number", data.get('receipt_number') or "N/A")
            res_col2.metric("📅 Date", data.get('date') or "N/A")
            res_col3.metric("💵 Total Amount", f"${data.get('total_amount'):.2f}" if data.get('total_amount') is not None else "N/A")

            # Use an expander for longer text fields like address
            with st.expander("Show More Details"):
                st.markdown(f"**👤 Bill To:** {data.get('bill_to', {}).get('name') if data.get('bill_to') else 'N/A'}")
                st.markdown(f"**📍 Vendor Address:** {data.get('address') or 'N/A'}")

            # Line items table
            if data.get('items'):
                st.subheader("🛒 Line Items")
                # Ensure data is in the right format for DataFrame
                items_df_data = [{
                    "Description": item.get("description", "N/A"),
                    "Qty": item.get("quantity", "N/A"),
                    "Unit Price": f"${item.get('unit_price', 0.0):.2f}",
                    "Total": f"${item.get('total', 0.0):.2f}"
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
    
    sample_dir = "data/samples" # ✅ Points to the correct folder
    if os.path.exists(sample_dir):
        sample_files = [f for f in os.listdir(sample_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        
        if sample_files:
            # Display the first sample found
            img_path = os.path.join(sample_dir, sample_files[0])
            st.image(Image.open(img_path), caption=sample_files[0], use_container_width=True)
            st.info("You can download this image and upload it in the 'Upload & Process' tab to test the pipeline.")
        else:
            st.warning("No sample invoices found in `data/samples/`.")
    else:
        st.error("The `data/samples` directory was not found.")

with tab3:
    st.header("ℹ️ How It Works (Your Custom Pipeline)")
    st.markdown("""
    This app follows the exact pipeline you built:
    ```
    1. 📸 Image Upload
       ↓
    2. 🔄 Preprocessing (OpenCV)
       Grayscale conversion and noise removal.
       ↓
    3. 🔍 OCR (Tesseract)
       Optimized with PSM 6 for receipt layouts.
       ↓
    4. 🎯 Rule-Based Extraction (Regex)
       Your custom patterns find specific fields.
       ↓
    5. ✅ Confidence & Validation
       Heuristics to check the quality of the extraction.
       ↓
    6. 📊 Output JSON
       Presents all extracted data in a structured format.
    ```
    """)
    st.info("This rule-based system is a great foundation. The next step is to replace the extraction logic with an ML model like LayoutLM to handle more diverse formats!")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #666;'>Built with your custom Python pipeline | UI by Streamlit</div>", unsafe_allow_html=True)