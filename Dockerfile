# Use an official Python runtime
FROM python:3.10-slim

# 1. Install system dependencies (Tesseract + OpenCV + POPPLER)
# Added poppler-utils because src/pdf_utils.py uses pdf2image
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# 2. Change Port to 7860 (Hugging Face default)
EXPOSE 7860

# 3. Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]