import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd
import sys
from src.report_generator import generate_bulk_html_report

# PDF to image conversion
try:
    from pdf2image import convert_from_bytes
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# --------------------------------------------------
# Pipeline import (PURE DATA ONLY)
# --------------------------------------------------
from src.pipeline import process_invoice
from src.database import init_db

# Initialize database (cached to run only once per session)
@st.cache_resource
def initialize_database_once():
    """Run DB init only once per session/restart"""
    init_db()

initialize_database_once()

# --------------------------------------------------
# Mock format detection (UI-level, safe)
# --------------------------------------------------
def detect_invoice_format(raw_text: str):
    if raw_text and "SDN BHD" in raw_text:
        return {
            "name": "Retail Invoice (MY)",
            "confidence": 95,
            "supported": True,
            "indicators": ["Detected 'SDN BHD' suffix"]
        }
    return {
        "name": "Unknown Format",
        "confidence": 20,
        "supported": False,
        "indicators": ["No known company suffix detected"]
    }


# --------------------------------------------------
# Streamlit Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="Smart Invoice Processor",
    page_icon="🧾",
    layout="wide"
)

# --------------------------------------------------
# Custom CSS
# --------------------------------------------------
st.markdown(
    """
    <style>
    /* Fix Hugging Face iframe glitch */
    .stApp > header {visibility: hidden;}
    .main .block-container {padding-top: 2rem;}
    img { max-width: 100%; height: auto; }
    /* Disable spinner blur */
    .st-emotion-cache-16idsys { filter: none !important; transition: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Header (v2 style)
# --------------------------------------------------
st.title("🧾 Smart Invoice Processor (Hybrid ML Pipeline)")
st.markdown(
    "**System Status:** 🟢 Online &nbsp;&nbsp;|&nbsp;&nbsp; "
    "**Model:** LayoutLMv3 + Rules &nbsp;&nbsp;|&nbsp;&nbsp; "
    "**Pipeline:** OCR → ML → Validation"
)

st.divider()

# --------------------------------------------------
# Sidebar (v1 depth, cleaner)
# --------------------------------------------------
with st.sidebar:
    st.header("ℹ️ About")
    st.info(
        "End-to-end invoice processing system that extracts structured data "
        "from scanned images and PDFs using ML + rule-based validation."
    )

    st.header("⚙️ Extraction Mode")
    extraction_method = st.selectbox(
        "Choose extraction method",
        ("ML-Based (LayoutLMv3)", "Rule-Based (Regex)")
    )

    st.header("📊 Stats")
    if "processed_count" not in st.session_state:
        st.session_state.processed_count = 0
    st.metric("Invoices Processed", st.session_state.processed_count)


# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    ["🚀 Upload & Process", "📚 Sample Invoices", "ℹ️ How It Works"]
)

# ==================================================
# TAB 1 — Upload & Process (v2 layout + v1 features)
# ==================================================
with tab1:
    col_left, col_right = st.columns([1, 1])

    # -----------------------------
    # LEFT — Upload + Preview
    # -----------------------------
    with col_left:
        st.subheader("1. Upload Invoice")

        # 1. Allow Multiple Files
        uploaded_files = st.file_uploader(
            "Upload Invoices (Bulk Supported)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True 
        )

        if "bulk_results" not in st.session_state:
            st.session_state.bulk_results = None

        if uploaded_files and st.button("✨ Process All Files", type="primary"):
            all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner(f"Processing {len(uploaded_files)} documents..."):
                temp_dir = Path("temp")
                temp_dir.mkdir(exist_ok=True)

                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing file {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
                    # Save temp file
                    temp_path = temp_dir / uploaded_file.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Run Pipeline
                    try:
                        # Use 'ml' method as per the requirement
                        result = process_invoice(str(temp_path), method='ml')
                        all_results.append(result)
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                
                    # Update Progress
                    progress_bar.progress((i + 1) / len(uploaded_files))

            st.success("✅ Bulk Processing Complete!")
            st.session_state.bulk_results = all_results
            
        if st.session_state.bulk_results:
            # Generate Report
            html_report = generate_bulk_html_report(st.session_state.bulk_results)
    
            # Download Button for the HTML
            st.download_button(
                label="📥 Download Bulk HTML Report",
                data=html_report,
                file_name="bulk_invoice_report.html",
                mime="text/html"
            )
        
            # Display Summary Table in UI
            st.subheader("Summary")
            df = pd.DataFrame(st.session_state.bulk_results)
            if not df.empty:
                # Select clean columns for display
                cols = [c for c in ["vendor", "date", "total_amount", "validation_status"] if c in df.columns]
                st.dataframe(df[cols], width='stretch')
        # Preview first file (if any files selected)
        if uploaded_files:
            first_file = uploaded_files[0]
            st.caption(f"Preview: {first_file.name}" + (f" (+{len(uploaded_files)-1} more)" if len(uploaded_files) > 1 else ""))
            
            # Handle PDF preview
            if first_file.type == "application/pdf":
                if PDF_SUPPORT:
                    pdf_bytes = first_file.read()
                    first_file.seek(0)  # Reset for later processing
                    pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
                    if pages:
                        pdf_preview_image = pages[0]
                        st.session_state.pdf_preview = pdf_preview_image
                        st.image(pdf_preview_image, width=250, caption="PDF Preview (Page 1)")
                else:
                    st.warning("PDF preview requires pdf2image. Install with: `pip install pdf2image`")
            else:
                image = Image.open(first_file)
                first_file.seek(0)  # Reset for later processing
                st.image(image, width=250, caption="Uploaded Invoice")


    # -----------------------------
    # RIGHT — Processing + Results
    # -----------------------------
    with col_right:
        st.subheader("2. Extraction Results")

        # Single-file extraction (original functionality)
        # Works when exactly 1 file is uploaded
        if uploaded_files and len(uploaded_files) == 1:
            single_file = uploaded_files[0]
            if st.button("✨ Extract Data", type="primary"):
                with st.spinner("Running invoice extraction pipeline..."):
                    try:
                        temp_dir = Path("temp")
                        temp_dir.mkdir(exist_ok=True)
                        temp_path = temp_dir / single_file.name

                        with open(temp_path, "wb") as f:
                            f.write(single_file.getbuffer())

                        method = "ml" if "ML" in extraction_method else "rules"
                        
                        # CALL PIPELINE
                        result = process_invoice(str(temp_path), method=method)

                        # --- SMART STATUS NOTIFICATIONS ---
                        db_status = result.get('_db_status', 'disabled')
                        
                        if db_status == 'saved':
                            st.success("✅ Extraction & Storage Complete")
                            st.toast("Invoice saved to Database!", icon="💾")
                        elif db_status == 'queued':
                            st.success("✅ Extraction Complete")
                            st.toast("Saving to database...", icon="💾")
                        elif db_status == 'duplicate':
                            st.success("✅ Extraction Complete") 
                            st.toast("Duplicate invoice (already in database)", icon="⚠️")
                        elif db_status == 'disabled':
                            st.success("✅ Extraction Complete")
                            if not st.session_state.get('_db_warning_shown', False):
                                st.toast("Database disabled (Demo Mode)", icon="ℹ️")
                                st.session_state['_db_warning_shown'] = True
                        else:
                            st.success("✅ Extraction Complete")

                        # Hard guard
                        if not isinstance(result, dict):
                            st.error("Pipeline returned invalid data.")
                            st.stop()
                            
                        if '_db_status' in result:
                            del result['_db_status']

                        st.session_state.data = result
                        st.session_state.format_info = detect_invoice_format(
                            result.get("raw_text", "")
                        )
                        st.session_state.processed_count += 1

                        # --- AI Detection Overlay Visualization ---
                        raw_predictions = result.get("raw_predictions")
                        if raw_predictions:
                            if single_file.type == "application/pdf":
                                if "pdf_preview" in st.session_state:
                                    overlay_image = st.session_state.pdf_preview.copy().convert("RGB")
                                else:
                                    overlay_image = None
                            else:
                                single_file.seek(0)
                                overlay_image = Image.open(single_file).convert("RGB")
                            
                            if overlay_image:
                                draw = ImageDraw.Draw(overlay_image)
                                for entity_name, entity_data in raw_predictions.items():
                                    bboxes = entity_data.get("bbox", [])
                                    for box in bboxes:
                                        x, y, w, h = box
                                        draw.rectangle([x, y, x + w, y + h], outline="red", width=2)

                                overlay_image.thumbnail((800, 800))
                                st.image(overlay_image, caption="AI Detection Overlay", width="content")

                    except Exception as e:
                        st.error(f"Pipeline error: {e}")

        # -----------------------------
        # Render Results
        # -----------------------------
        if "data" in st.session_state:
            data = st.session_state.data

            # Validation banner (v2 style)
            status = data.get("validation_status", "unknown")
            if status == "passed":
                st.success("✅ Data Validation Passed")
            elif status == "failed":
                st.error("❌ Data Validation Failed")
            else:
                st.warning("⚠️ Validation Not Performed")

            # Key metrics (clean & focused)
            m1, m2, m3 = st.columns(3)
            m1.metric("Vendor", data.get("vendor") or "N/A")
            m2.metric("Date", data.get("date") or "N/A")
            total = data.get("total_amount")
            m3.metric("Total Amount", f"${total}" if total else "N/A")

            st.divider()

            # Secondary fields
            s1, s2 = st.columns(2)
            s1.metric("Receipt / Invoice #", data.get("receipt_number") or "N/A")

            bill_to = data.get("bill_to")
            if isinstance(bill_to, dict):
                bill_to = bill_to.get("name")
            s2.metric("Bill To", bill_to or "N/A")

            # Line items
            st.subheader("🛒 Line Items")
            items = data.get("items", [])
            if items:
                st.dataframe(pd.DataFrame(items), width='stretch')
            else:
                st.info("No line items extracted.")

            # -----------------------------
            # Advanced / Engineer View
            # -----------------------------
            with st.expander("🔍 Advanced Details"):
                format_info = st.session_state.format_info
                st.write("**Detected Format:**", format_info["name"])
                st.write("**Detection Confidence:**", f"{format_info['confidence']}%")
                for ind in format_info["indicators"]:
                    st.write(f"• {ind}")

                st.markdown("---")
                st.write("**Semantic Hash:**", data.get("semantic_hash", "N/A"))

            with st.expander("📄 Full JSON Output"):
                st.json(data)

            st.download_button(
                "💾 Download JSON",
                json.dumps(data, indent=2),
                file_name=f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

            html_report = generate_bulk_html_report([data])
            st.download_button(
                "📥 Download HTML Report",
                html_report,
                file_name=f"invoice_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html"
            )

            with st.expander("📝 Raw OCR Text"):
                st.text(data.get("raw_text", "No OCR text available"))


# ==================================================
# TAB 2 — Samples
# ==================================================
with tab2:
    st.header("📚 Sample Invoices")

    sample_dir = Path("data/samples")
    if sample_dir.exists():
        samples = list(sample_dir.glob("*"))
        if samples:
            st.image(
                Image.open(samples[0]),
                caption=samples[0].name,
                width=250
            )
        else:
            st.info("No sample invoices found.")
    else:
        st.warning("Sample directory not found.")


# ==================================================
# TAB 3 — How It Works
# ==================================================
with tab3:
    st.header("ℹ️ System Architecture")
    st.markdown(
        """
        Input Handling

JPG / PNG / PDF detection

OCR & Layout Parsing

Tesseract + LayoutLMv3

Hybrid Extraction

ML predictions with rule-based fallback

Validation

Schema & consistency checks

Output

Structured JSON + UI visualization
        """
    )
