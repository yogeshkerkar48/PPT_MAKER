"""
FastAPI Application - Cinematic PPT Generator V4.4 (Async/Celery)
Main entry point for the API service on Port 8001
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import json
from pathlib import Path
from typing import Optional
from celery.result import AsyncResult
import redis

# Import custom modules
from html_parser import clean_html
from celery_app import celery_app, generate_pptx_task, OUTPUT_DIR
import config

# Document Extraction Imports
import docx
from pypdf import PdfReader

# Initialize FastAPI app
app = FastAPI(
    title="Cinematic PPT Generator API (Async)",
    description="AI-powered service to convert content into professional PowerPoint presentations asynchronously",
    version="4.4.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

# Redis client for cancellation flags
redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)

async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text content from various file formats"""
    content = ""
    filename = file.filename.lower()
    try:
        file_content = await file.read()
        file_bytes = io.BytesIO(file_content)
        
        if filename.endswith('.pdf'):
            reader = PdfReader(file_bytes)
            content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif filename.endswith('.docx'):
            doc = docx.Document(file_bytes)
            content = "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith('.txt'):
            content = file_content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")
    return content

@app.get("/")
async def root():
    return {"message": "Cinematic PPT Generator Async API v4.4 (Port 8001)", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "healthy", "config": {"groq": bool(config.GROQ_API_KEY), "serper": bool(config.SERPER_API_KEY)}}

@app.post("/generate-pptx")
async def generate_pptx_endpoint(
    html_content: Optional[str] = Form(None),
    max_slides: int = Form(50),
    file: Optional[UploadFile] = File(None)
):
    try:
        # 1. Ingest Content
        raw_text = ""
        if file and file.filename:
            raw_text = await extract_text_from_file(file)
        elif html_content:
            raw_text = clean_html(html_content)
        else:
            raise HTTPException(status_code=400, detail="No content provided.")

        # 2. Trigger Celery Task
        task = generate_pptx_task.delay(raw_text, max_slides)
        
        return {"task_id": task.id, "message": "Presentation generation started."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a background task"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.info if task_result.status != 'FAILURE' else str(task_result.info)
    }
    
    return JSONResponse(
        content=response, 
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.post("/cancel-task/{task_id}")
async def cancel_task(task_id: str):
    """Interrupt/Cancel a running background task"""
    try:
        # 1. Set manual flag in Redis (for Windows solo pool fix)
        # Expires in 1 hour (3600s) to clean up automatically
        redis_client.setex(f"cancel_{task_id}", 3600, "1")
        
        # 2. Standard Celery revoke (for non-Windows or standard behavior)
        celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')
        
        return {"message": f"Task {task_id} cancellation signal sent (Redis + Celery)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{task_id}")
async def download_pptx(task_id: str):
    """Download the generated PPTX file"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.status == 'SUCCESS':
        result = task_result.result
        filename = result.get('filename')
        output_path = Path(result.get('output_path'))
        
        if output_path.exists():
            return FileResponse(
                path=output_path,
                filename=filename,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        else:
            raise HTTPException(status_code=404, detail="File not found on server.")
    else:
        raise HTTPException(status_code=400, detail=f"Task is not finished. Status: {task_result.status}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
