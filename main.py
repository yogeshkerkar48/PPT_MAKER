"""
FastAPI Application - HTML to PowerPoint Converter
Main entry point for the API service
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
from typing import Optional
import httpx
import urllib.parse
import uuid
import re
import shutil
from serpapi import GoogleSearch
from PIL import Image
import io

# Import custom modules
from html_parser import clean_html, truncate_content
from groq_client import GroqClient
from pptx_generator import generate_pptx
import config

# Document Extraction Imports
import docx
from pypdf import PdfReader

async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text content from various file formats"""
    content = ""
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.pdf'):
            reader = PdfReader(file.file)
            content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif filename.endswith('.docx'):
            doc = docx.Document(file.file)
            content = "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith('.txt'):
            content = (await file.read()).decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please use PDF, DOCX, or TXT.")
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text from document: {str(e)}")
    
    return content

# Initialize FastAPI app
app = FastAPI(
    title="HTML to PowerPoint Converter",
    description="AI-powered service to convert HTML content into professional PowerPoint presentations",
    version="1.0.0"
)

# Add CORS middleware with comprehensive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

# Middleware to strip /api prefix if present (Robustness for Nginx/Proxy mismatches)
@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        new_path = request.url.path[4:] # Remove /api
        scope = request.scope
        scope["path"] = new_path
        # Update raw_path as well just in case
        if "raw_path" in scope:
            scope["raw_path"] = new_path.encode("utf-8")
        request = Request(scope, request.receive)
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HTML to PowerPoint Converter API",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/generate-pptx",
            "docs": "/docs"
        }
    }



# Ensure temp directory exists at an absolute path
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp_images"
TEMP_DIR.mkdir(exist_ok=True)

@app.post("/generate-pptx")
async def generate_pptx_endpoint(
    html_content: Optional[str] = Form(None, description="HTML or plain text content"),
    background_color: Optional[str] = Form(None, description="Optional background color (AI will override)"),
    file: Optional[UploadFile] = File(None, description="PDF, DOCX, or TXT file to convert"),
    image: Optional[UploadFile] = File(None, description="Deprecated manual upload")
):
    """
    Generate PowerPoint presentation from file or text
    """
    temp_image_path = None
    
    try:
        # Step 1: Get Content (File or Manual)
        raw_text = ""
        if file and file.filename:
            print(f"Ingesting file: {file.filename}")
            raw_text = await extract_text_from_file(file)
        elif html_content and html_content.strip():
            print("Using manual text/HTML input")
            raw_text = clean_html(html_content)
        else:
            raise HTTPException(status_code=400, detail="Please provide either a document file or text content.")

        print("Step 1: Cleaning and truncating content...")
        clean_text = truncate_content(raw_text, config.MAX_HTML_LENGTH)
        
        # Step 2: Use Groq AI to structure content
        print("Step 2: Structuring content with AI...")
        groq_client = GroqClient()
        slides_data = groq_client.structure_content_to_slides(clean_text)
        
        if not slides_data.get('slides'):
            raise HTTPException(status_code=500, detail="AI failed to generate slides")
        
        print(f"Generated {len(slides_data['slides'])} slides")

        # Determine background color (Prioritize AI suggestion)
        bg_color = slides_data.get('suggested_bg_color', background_color or "2E5A88")
        print(f"Applying Theme Color: {bg_color}")

        # Step 3: Handle Images (Per Slide via SerpAPI)
        slide_images = [] # List of image paths corresponding to slides
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            
            for i, slide in enumerate(slides_data['slides']):
                slide_img_path = None
                
                # Use SerpAPI to find a relevant professional visual
                query = slide.get('visual_query', slide['title'])
                
                try:
                    search_params = {
                        "q": query,
                        "engine": config.SERPAPI_ENGINE,
                        "ijn": "0",
                        "api_key": config.SERPAPI_API_KEY,
                        "safe": config.SERPAPI_SAFE_SEARCH,
                        "isz": config.SERPAPI_IMG_SIZE
                    }
                    print(f"Slide {i+1}: Searching for professional visual: '{query}'...")
                    search = GoogleSearch(search_params)
                    results = search.get_dict()
                    
                    if "error" in results:
                         print(f"SerpAPI Error: {results['error']}")
                         
                    images = results.get("images_results", [])
                    print(f"Slide {i+1}: Found {len(images)} images.")
                    
                    # FALLBACK: If specific search fails, try a BROAD search with just keywords
                    # LAYERED FALLBACK STRATEGY
                    # 1. Broad Cinematic Search
                    if not images:
                        print(f"Slide {i+1}: Specific search failed. Trying broad cinematic search...")
                        fallback_query = f"professional cinematic {query} backdrop"
                        search = GoogleSearch({"q": fallback_query, "engine": "google_images", "api_key": config.SERPAPI_API_KEY})
                        results = search.get_dict()
                        images = results.get("images_results", [])
                        
                    # 2. Abstract Theme Search
                    if not images:
                        print(f"Slide {i+1}: Broad search failed. Trying abstract safety search...")
                        safety_query = f"abstract professional {bg_color} cinematic background"
                        search = GoogleSearch({"q": safety_query, "engine": "google_images", "api_key": config.SERPAPI_API_KEY})
                        results = search.get_dict()
                        images = results.get("images_results", [])

                    # 3. ULTIMATE AI GENERATION (Guaranteed)
                    img_url = None
                    if not images:
                        print(f"Slide {i+1}: All searches failed. Using ULTIMATE fallback (AI Generation)...")
                        safe_prompt = urllib.parse.quote(query)
                        img_url = config.POLLINATIONS_URL.format(prompt=safe_prompt, model=config.POLLINATIONS_MODEL)
                        print(f"Generated AI image URL: {img_url}")

                    if images or img_url:
                        # Try top 3 images from results if download fails or is invalid
                        image_pool = images[:3]
                        download_success = False
                        
                        for img_obj in image_pool:
                            try:
                                current_url = img_obj.get("original")
                                print(f"Attempting download: {current_url}")
                                resp = await client.get(current_url, timeout=15.0, headers=headers)
                                if resp.status_code == 200:
                                    # VALIDATE & CONVERT TO PNG (Ensures compatibility)
                                    try:
                                        img = Image.open(io.BytesIO(resp.content))
                                        # Convert and save as PNG to guarantee python-pptx compatibility
                                        output = io.BytesIO()
                                        img.save(output, format="PNG")
                                        png_bytes = output.getvalue()
                                        
                                        filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                        slide_img_path = str(TEMP_DIR / filename)
                                        with open(slide_img_path, "wb") as f:
                                            f.write(png_bytes)
                                        download_success = True
                                        print(f"Slide {i+1}: Image secured and converted to PNG.")
                                        break # Success!
                                    except Exception as img_err:
                                        print(f"Slide {i+1}: Invalid image data from {current_url}. Error: {img_err}")
                            except Exception as e:
                                print(f"Slide {i+1}: Download error for {current_url}: {e}")

                        # ULTIMATE FALLBACK: AI Generation if no search image worked
                        if not download_success:
                            print(f"Slide {i+1}: Search imagery failed validation. Generating AI backdrop...")
                            safe_prompt = urllib.parse.quote(f"cinematic high-quality {query} professional photography background")
                            gen_url = config.POLLINATIONS_URL.format(prompt=safe_prompt, model=config.POLLINATIONS_MODEL)
                            try:
                                resp = await client.get(gen_url, timeout=25.0, headers=headers)
                                if resp.status_code == 200:
                                    # Convert Gen image to PNG for safety
                                    img = Image.open(io.BytesIO(resp.content))
                                    output = io.BytesIO()
                                    img.save(output, format="PNG")
                                    png_bytes = output.getvalue()
                                    
                                    filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                    slide_img_path = str(TEMP_DIR / filename)
                                    with open(slide_img_path, "wb") as f:
                                        f.write(png_bytes)
                                    print(f"Slide {i+1}: AI visual generated and converted to PNG.")
                            except Exception as gen_err:
                                print(f"Slide {i+1}: AI generation also failed (critical): {gen_err}")
                    else:
                        print(f"Slide {i+1}: No image source available at all.")
                except Exception as e:
                    print(f"SerpAPI/Download failed for slide {i}: {str(e)}")

                slide_images.append(slide_img_path)

        # Step 4: Generate PowerPoint
        print("Step 4: Generating PowerPoint presentation...")
        pptx_buffer = generate_pptx(slides_data, bg_color, slide_images)
        
        # Return file as a standard Response (more reliable for downloads than StreamingResponse)
        filename = f"presentation_{uuid.uuid4().hex[:8]}.pptx"
        content = pptx_buffer.getvalue()
        
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating presentation: {str(e)}")
    
    finally:
        # We'll leave the file for now so you can verify it in the temp_images folder
        # if you continue to see issues.
        pass




@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "groq_api_configured": bool(config.GROQ_API_KEY)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
