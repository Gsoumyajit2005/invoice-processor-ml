from fastapi import FastAPI, UploadFile, File, HTTPException
from src.pipeline import process_invoice
import shutil
import os
import uvicorn

app = FastAPI(title="Invoice Extraction API", version="1.0")

@app.post("/extract")
async def extract_invoice(file: UploadFile = File(...), method: str = 'ml'):
    """
    Endpoint to process an uploaded invoice file.
    """
    temp_file_path = f"temp_{file.filename}"
    
    try:
        # Save uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run pipeline
        result = process_invoice(temp_file_path, method=method, save_results=False)
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)