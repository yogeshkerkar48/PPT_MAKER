import os
import redis
import uuid
import urllib.parse
import io
import json
import re
import httpx
import shutil
from pathlib import Path
from typing import List
from PIL import Image
import docx
from pypdf import PdfReader
from celery import Celery
from celery.result import AsyncResult

from runware import Runware
from runware.types import IImageInference
from html_parser import clean_html, truncate_content
from groq_client import GroqClient
from pptx_generator import generate_pptx
import config

# Initialize Celery
celery_app = Celery(
    "ppt_generator",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL
)

# Celery Configuration
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

BASE_DIR = Path(__file__).resolve().parent
# Redis Client for manual cancellation flags
redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)

TEMP_DIR = BASE_DIR / "temp_images"
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = BASE_DIR / "output_presentations"
OUTPUT_DIR.mkdir(exist_ok=True)


async def generate_image_runware_async(prompt: str) -> str:
    """Generate image using Runware.ai SDK as backup"""
    if not config.RUNWARE_API_KEY:
        return None
    try:
        runware = Runware(api_key=config.RUNWARE_API_KEY)
        await runware.connect()
        
        request = IImageInference(
            positivePrompt=prompt,
            model=config.RUNWARE_MODEL_ID,
            numberResults=1,
            width=1280,
            height=704, # Must be multiple of 64
            outputType="URL"
        )
        
        images = await runware.imageInference(requestImage=request)
        
        if images and len(images) > 0:
            return images[0].imageURL
        return None
    except Exception as e:
        print(f"Runware Generation Error: {e}")
        return None

def fix_duplicate_queries(slides: List[dict]):
    """Fixes duplicate visual queries to ensure variety"""
    seen = set()
    fallbacks = [
        "geometric compass drawing circles", "vintage abacus with wooden beads", 
        "neon mathematical symbols glowing", "graph paper with equations",
        "scientific calculator closeup", "protractor measuring angles",
        "chalkboard with colorful formulas", "digital LED number display",
        "ruler and pencil on engineering drawing", "mathematical textbook open",
        "student solving problem on tablet", "3D geometric shapes floating",
        "Fibonacci spiral in nature", "binary code matrix", "ancient counting stones",
        "math teacher at whiteboard", "trigonometry triangle diagram",
        "algebra symbols on paper", "statistics graph chart", "geometry set tools"
    ]
    fb_idx = 0
    for slide in slides:
        q = slide.get('visual_query', '')
        if q in seen:
            slide['visual_query'] = fallbacks[fb_idx % len(fallbacks)]
            fb_idx += 1
        seen.add(slide.get('visual_query', ''))

def count_numbered_points(text: str) -> int:
    """Detect the number of numbered points in the text (e.g., 1., 2), 3.)"""
    # Look for lines starting with digits followed by . or )
    pattern = r'^\s*\d+[\.\)]\s+'
    matches = re.findall(pattern, text, re.MULTILINE)
    return len(matches)

import asyncio

def is_task_cancelled(task) -> bool:
    """Check if the task has been revoked in Redis (Soft Cancellation for Windows)"""
    task_id = task.request.id
    # 1. Check for manual Redis flag (Fastest for Windows solo pool)
    if redis_client.exists(f"cancel_{task_id}"):
        return True
    # 2. Check standard Celery revocation status
    return AsyncResult(task_id, app=celery_app).status == 'REVOKED'

@celery_app.task(name="generate_pptx_task", bind=True)
def generate_pptx_task(self, raw_text, max_slides):
    """Celery task to generate PPTX in the background"""
    return asyncio.run(generate_pptx_workflow(self, raw_text, max_slides))

async def generate_pptx_workflow(self, raw_text, max_slides):
    try:
        self.update_state(state='PROGRESS', meta={'message': 'Cleaning content...'})
        clean_text = truncate_content(raw_text, config.MAX_HTML_LENGTH)
        
        # Detection of points...
        detected_points = count_numbered_points(clean_text)
        if detected_points > 0:
            print(f"Detected {detected_points} points. Enforcing strict 1:1 mapping (overriding max_slides={max_slides}).")
            max_slides = detected_points
        
        if is_task_cancelled(self): return {'status': 'CANCELLED'}

        groq_client = GroqClient()
        slides_data = groq_client.structure_content_to_slides(clean_text, max_slides=max_slides)
        
        if is_task_cancelled(self): return {'status': 'CANCELLED'}
        
        fix_duplicate_queries(slides_data.get('slides', []))
        
        slide_images = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            client.headers.update({"User-Agent": "Mozilla/5.0"})
            
            for i, slide in enumerate(slides_data['slides']):
                self.update_state(state='PROGRESS', meta={
                    'message': f'Processing slide {i+1} of {len(slides_data["slides"])}',
                    'current': i + 1,
                    'total': len(slides_data["slides"])
                })
                
                # SOFT CANCELLATION CHECK
                if is_task_cancelled(self):
                    print(f"Task {self.request.id} revoked. Aborting...")
                    return {'status': 'CANCELLED', 'message': 'Generation stopped by user.'}
                
                query = slide.get('visual_query', slide['title'])
                slide_img_path = None
                
                # PURE RUNWARE AI GENERATION
                print(f"Generating AI image for: {query}...")
                
                # CHECK BEFORE RUNWARE
                if is_task_cancelled(self): return {'status': 'CANCELLED'}
                
                gen_url = await generate_image_runware_async(query)
                
                # CHECK AFTER RUNWARE
                if is_task_cancelled(self): return {'status': 'CANCELLED'}
                
                if gen_url:
                    try:
                        resp = await client.get(gen_url, timeout=30.0)
                        if resp.status_code == 200:
                            img = Image.open(io.BytesIO(resp.content))
                            out = io.BytesIO()
                            img.save(out, format="PNG")
                            path = TEMP_DIR / f"runware_{i}_{uuid.uuid4().hex[:6]}.png"
                            with open(path, "wb") as f: f.write(out.getvalue())
                            slide_img_path = str(path)
                        else:
                            print(f"Runware download failed with status: {resp.status_code}")
                    except Exception as e:
                        print(f"Runware download error: {e}")
                else:
                    print(f"Runware generation failed for: {query}")

                slide_images.append(slide_img_path)

        self.update_state(state='PROGRESS', meta={'message': 'Finalizing PowerPoint...'})
        bg_color = slides_data.get('suggested_bg_color', "#0F172A")
        pptx_buffer = generate_pptx(slides_data, bg_color, slide_images)
        
        filename = f"presentation_{uuid.uuid4().hex[:8]}.pptx"
        output_path = OUTPUT_DIR / filename
        with open(output_path, "wb") as f:
            f.write(pptx_buffer.getvalue())
            
        return {'status': 'SUCCESS', 'filename': filename, 'output_path': str(output_path)}

    except Exception as e:
        # Just log and raise; Celery will handle the FAILURE state correctly
        print(f"Task Workflow Error: {str(e)}")
        raise e
