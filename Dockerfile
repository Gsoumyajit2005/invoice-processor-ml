# Use an official Python runtime
FROM python:3.10-slim

# Install system dependencies (Tesseract + OpenCV)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn python-multipart

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]