# src/api.py

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import os
from pathlib import Path
import uuid
import sys

# Import modules
sys.path.append(str(Path(__file__).resolve().parent))
from pipeline import process_invoice
from schema import InvoiceData 

app = FastAPI(
    title="Invoice Extraction API",
    description="Hybrid ML + Rule-Based Pipeline with LayoutLMv3",
    version="2.0"
)

# Create temp folder if not exists
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def cleanup_file(path: str):
    """Background task to remove temp file after processing"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error cleaning up {path}: {e}")

@app.post("/extract", response_model=InvoiceData) # <--- CONTRACT ENFORCED
async def extract_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload an invoice (PDF/JPG/PNG) and get structured data.
    """
    # 1. Generate unique filename to prevent collisions
    file_ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4()}{file_ext}"
    temp_path = UPLOAD_DIR / unique_name
    
    try:
        # 2. Save Uploaded File
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Process Logic
        result = process_invoice(str(temp_path), method='ml')
        
        # 4. Cleanup
        # We use background_tasks to delete the file AFTER the response is sent
        background_tasks.add_task(cleanup_file, str(temp_path))
        
        return result

    except Exception as e:
        # Cleanup even on error
        cleanup_file(str(temp_path))
        raise HTTPException(status_code=500, detail=str(e))