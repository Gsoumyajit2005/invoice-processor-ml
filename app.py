import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd
import sys

# --------------------------------------------------
# Pipeline import (PURE DATA ONLY)
# --------------------------------------------------
sys.path.append("src")
from pipeline import process_invoice


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

        uploaded_file = st.file_uploader(
            "Upload JPG, PNG, or PDF",
            type=["jpg", "jpeg", "png", "pdf"]
        )

        if uploaded_file:
            st.caption(f"File: {uploaded_file.name}")

            if uploaded_file.type == "application/pdf":
                st.info("PDF uploaded (preview not available)")
            else:
                image = Image.open(uploaded_file)

                st.image(
                    image,
                    width=350,
                    caption="Uploaded Invoice"
                )


    # -----------------------------
    # RIGHT — Processing + Results
    # -----------------------------
    with col_right:
        st.subheader("2. Extraction Results")

        if uploaded_file and st.button("✨ Extract Data", type="primary"):
            with st.spinner("Running invoice extraction pipeline..."):
                try:
                    temp_dir = Path("temp")
                    temp_dir.mkdir(exist_ok=True)
                    temp_path = temp_dir / uploaded_file.name

                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    method = "ml" if "ML" in extraction_method else "rules"
                    result = process_invoice(str(temp_path), method=method)

                    # Hard guard — prevents DeltaGenerator bugs forever
                    if not isinstance(result, dict):
                        st.error("Pipeline returned invalid data.")
                        st.stop()

                    st.session_state.data = result
                    st.session_state.format_info = detect_invoice_format(
                        result.get("raw_text", "")
                    )
                    st.session_state.processed_count += 1

                    st.success("Extraction Complete")

                    # --- AI Detection Overlay Visualization ---
                    raw_predictions = result.get("raw_predictions")
                    if raw_predictions and uploaded_file.type != "application/pdf":
                        # Reload the original image for annotation
                        uploaded_file.seek(0)
                        overlay_image = Image.open(uploaded_file).convert("RGB")
                        draw = ImageDraw.Draw(overlay_image)

                        # Draw red rectangles around each detected entity's bounding boxes
                        for entity_name, entity_data in raw_predictions.items():
                            bboxes = entity_data.get("bbox", [])
                            for box in bboxes:
                                # bbox format: [x, y, width, height]
                                x, y, w, h = box
                                draw.rectangle(
                                    [x, y, x + w, y + h],
                                    outline="red",
                                    width=2
                                )

                        st.image(overlay_image, caption="AI Detection Overlay", use_container_width=True)

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
                st.dataframe(pd.DataFrame(items), use_container_width=True)
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
                use_container_width=True
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
