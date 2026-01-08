"""
Standalone CLI script - HTML to PowerPoint Converter
Generates professional presentations from files or text locally.
"""
import argparse
import asyncio
import os
import uuid
import urllib.parse
import io
import json
import httpx
from pathlib import Path
from typing import Optional, List
from PIL import Image

# Document Extraction Imports
import docx
from pypdf import PdfReader

# Import custom modules
from html_parser import clean_html, truncate_content
from groq_client import GroqClient
from pptx_generator import generate_pptx
import config

async def search_images_serper(query: str, client: httpx.AsyncClient) -> List[dict]:
    """Search images using Serper.dev"""
    url = config.SERPER_URL
    start_query = query + " -site:shutterstock.com -site:instagram.com -site:facebook.com -site:tiktok.com -site:pinterest.com -site:dreamstime.com -site:123rf.com -site:alamy.com -site:istockphoto.com -site:gettyimages.com"
    payload = json.dumps({
        "q": start_query,
        "gl": "us",
        "hl": "en",
        "num": 20
    })
    headers = {
        'X-API-KEY': config.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = await client.post(url, headers=headers, data=payload, timeout=20.0)
        if response.status_code == 200:
             results = response.json()
             return results.get('images', [])
        else:
             print(f"Serper API Error: {response.status_code} - {response.text}")
             return []
    except Exception as e:
        print(f"Serper Search Error: {e}")
        return []

async def extract_text_from_file(file_path: Path) -> str:
    """Extract text content from various file formats"""
    content = ""
    filename = file_path.name.lower()
    
    try:
        if filename.endswith('.pdf'):
            reader = PdfReader(str(file_path))
            content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif filename.endswith('.docx'):
            doc = docx.Document(str(file_path))
            content = "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            raise ValueError(f"Unsupported file format: {filename}. Please use PDF, DOCX, or TXT.")
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise
    
    return content

async def main_async():
    parser = argparse.ArgumentParser(description="AI-powered PPT Generator CLI")
    parser.add_argument("--input", type=str, help="Path to input file (PDF, DOCX, TXT)")
    parser.add_argument("--text", type=str, help="Raw text or HTML content")
    parser.add_argument("--output", type=str, help="Output PPTX filename", default=None)
    parser.add_argument("--color", type=str, help="Target background color (hex)", default=None)
    parser.add_argument("--max-slides", type=int, help="Maximum number of slides", default=60)
    
    args = parser.parse_args()

    # Step 0: Setup Directories
    BASE_DIR = Path(__file__).resolve().parent
    TEMP_DIR = BASE_DIR / "temp_images"
    TEMP_DIR.mkdir(exist_ok=True)

    try:
        # Step 1: Get Content
        raw_text = ""
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: File {args.input} does not exist.")
                return
            print(f"Ingesting file: {input_path.name}")
            raw_text = await extract_text_from_file(input_path)
        elif args.text:
            print("Using manual text/HTML input")
            raw_text = clean_html(args.text)
        else:
            print("Error: Please provide either --input or --text")
            return

        print("Step 1: Cleaning and truncating content...")
        clean_text = truncate_content(raw_text, config.MAX_HTML_LENGTH)
        
        # Step 2: Use Groq AI to structure content
        print("Step 2: Structuring content with AI...")
        groq_client = GroqClient()
        slides_data = groq_client.structure_content_to_slides(clean_text, max_slides=args.max_slides)
        
        if not slides_data.get('slides'):
            print("Error: AI failed to generate slides")
            return
        
        # CRITICAL: Deduplicate visual queries
        print("Step 2.5: Deduplicating visual queries...")
        used_queries = set()
        math_alternatives = [
            "geometric compass drawing circles",
            "vintage abacus with wooden beads",
            "neon mathematical symbols glowing",
            "graph paper with equations",
            "scientific calculator buttons",
            "protractor measuring angles",
            "chalkboard with chalk formulas",
            "digital LED number display",
            "ruler and pencil on drawing",
            "mathematical textbook open",
            "student solving on tablet",
            "3D geometric shapes floating",
            "Fibonacci spiral in nature",
            "binary code matrix",
            "ancient counting stones",
            "math teacher at whiteboard",
            "trigonometry triangle diagram",
            "algebra symbols on paper",
            "statistics graph chart",
            "geometry set tools on desk"
        ]
        math_alt_index = 0
        
        for slide in slides_data['slides']:
            query = slide.get('visual_query', '').lower().strip()
            
            # Check for duplicates
            if query in used_queries:
                print(f"  Duplicate detected: '{query}' - replacing...")
                # Use next math alternative
                new_query = math_alternatives[math_alt_index % len(math_alternatives)]
                slide['visual_query'] = new_query
                used_queries.add(new_query.lower())
                math_alt_index += 1
            else:
                used_queries.add(query)
        
        print(f"Generated {len(slides_data['slides'])} slides")

        # Determine background color
        bg_color = slides_data.get('suggested_bg_color', args.color or "2E5A88")
        print(f"Applying Theme Color: {bg_color}")

        # Step 3: Handle Images
        slide_images = []
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            
            for i, slide in enumerate(slides_data['slides']):
                slide_img_path = None
                query = slide.get('visual_query', slide['title'])
                

                try:
                    print(f"Slide {i+1}: Searching for professional visual: '{query}'...")
                    images = await search_images_serper(query, client)
                    print(f"Slide {i+1}: Found {len(images)} images.")
                    
                    # Fallback Strategy
                    if not images:
                        print(f"Slide {i+1}: Specific search failed. Trying broad cinematic search...")
                        fallback_query = f"professional cinematic {query} backdrop"
                        images = await search_images_serper(fallback_query, client)
                        
                    if not images:
                        print(f"Slide {i+1}: Broad search failed. Trying abstract safety search...")
                        safety_query = f"abstract professional {bg_color} cinematic background"
                        images = await search_images_serper(safety_query, client)

                    # ULTIMATE AI GENERATION (Guaranteed)
                    img_url = None
                    if not images:
                        print(f"Slide {i+1}: All searches failed. Using ULTIMATE fallback (AI Generation)...")
                        safe_prompt = urllib.parse.quote(query)
                        img_url = config.POLLINATIONS_URL.format(prompt=safe_prompt, model=config.POLLINATIONS_MODEL)

                    if images or img_url:
                        image_pool = images[:3]
                        download_success = False
                        
                        for img_obj in image_pool:
                            try:
                                current_url = img_obj.get("imageUrl") or img_obj.get("original")
                                if not current_url:
                                    continue
                                print(f"Attempting download: {current_url}")
                                resp = await client.get(current_url, timeout=15.0, headers=headers)
                                if resp.status_code == 200:
                                    # Enhancement: Validate content type and size
                                    if len(resp.content) < 1024:
                                        print(f"Skipping: Content too small ({len(resp.content)} bytes)")
                                        continue
                                    
                                    try:
                                        img = Image.open(io.BytesIO(resp.content))
                                        img.verify() # Validates image integrity
                                        img = Image.open(io.BytesIO(resp.content)) # Re-open
                                    except Exception as e:
                                        print(f"Skipping: Invalid image data - {e}")
                                        continue

                                    output = io.BytesIO()
                                    img.save(output, format="PNG")
                                    png_bytes = output.getvalue()
                                    
                                    filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                    slide_img_path = str(TEMP_DIR / filename)
                                    with open(slide_img_path, "wb") as f:
                                        f.write(png_bytes)
                                    download_success = True
                                    print(f"Slide {i+1}: Image secured.")
                                    break
                            except Exception as e:
                                print(f"Slide {i+1}: Download error: {e}")

                        if not download_success:
                            print(f"Slide {i+1}: Generating AI backdrop...")
                            # Simplify the prompt for better AI generation success
                            simple_prompt = query.replace("A photo of", "").replace("cinematic lighting", "").replace("natural lighting", "").replace("professional black and white", "").strip()
                            safe_prompt = urllib.parse.quote(f"professional {simple_prompt} high quality photography")
                            
                            # Try primary AI generator
                            gen_url = config.POLLINATIONS_URL.format(prompt=safe_prompt, model=config.POLLINATIONS_MODEL)
                            ai_success = False
                            
                            try:
                                resp = await client.get(gen_url, timeout=30.0, headers=headers)
                                
                                # Check if response contains rate limit error
                                if resp.status_code == 200:
                                    # Check content type first
                                    content_type = resp.headers.get("content-type", "").lower()
                                    
                                    # If it's an image, validate it's not the error image
                                    if "image" in content_type and len(resp.content) > 1024:
                                        try:
                                            img = Image.open(io.BytesIO(resp.content))
                                            img.verify()
                                            img = Image.open(io.BytesIO(resp.content))
                                            
                                            # CRITICAL: Detect Pollinations rate limit image
                                            # The error image has specific characteristics
                                            width, height = img.size
                                            
                                            # STRICT CHECK: We requested 1280x720, anything else is an error
                                            # Rate limit images come in various sizes (1024x576, 800x600, etc.)
                                            if width != 1280 or height != 720:
                                                print(f"Slide {i+1}: Detected invalid image size ({width}x{height}), expected 1280x720, skipping...")
                                                ai_success = False
                                            else:
                                                output = io.BytesIO()
                                                img.save(output, format="PNG")
                                                png_bytes = output.getvalue()
                                                
                                                filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                                slide_img_path = str(TEMP_DIR / filename)
                                                with open(slide_img_path, "wb") as f:
                                                    f.write(png_bytes)
                                                print(f"Slide {i+1}: AI visual generated successfully.")
                                                ai_success = True
                                        except Exception as img_err:
                                            print(f"Slide {i+1}: Primary AI validation failed: {img_err}")
                                    else:
                                        print(f"Slide {i+1}: Invalid content type or size from AI")
                            except Exception as gen_err:
                                print(f"Slide {i+1}: Primary AI request failed: {gen_err}")
                            
                            # Try alternative AI generators if primary failed
                            if not ai_success and not slide_img_path:
                                for alt_idx, alt_url_template in enumerate(config.ALTERNATIVE_AI_URLS):
                                    try:
                                        alt_url = alt_url_template.format(prompt=safe_prompt)
                                        print(f"Slide {i+1}: Trying alternative AI generator {alt_idx + 1}...")
                                        resp = await client.get(alt_url, timeout=30.0, headers=headers)
                                        if resp.status_code == 200 and len(resp.content) > 1024:
                                            try:
                                                img = Image.open(io.BytesIO(resp.content))
                                                img.verify()
                                                img = Image.open(io.BytesIO(resp.content))
                                                
                                                output = io.BytesIO()
                                                img.save(output, format="PNG")
                                                png_bytes = output.getvalue()
                                                
                                                filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                                slide_img_path = str(TEMP_DIR / filename)
                                                with open(slide_img_path, "wb") as f:
                                                    f.write(png_bytes)
                                                print(f"Slide {i+1}: Alternative AI {alt_idx + 1} succeeded.")
                                                break
                                            except Exception as img_err:
                                                print(f"Slide {i+1}: Alt AI {alt_idx + 1} validation failed")
                                    except Exception as alt_err:
                                        print(f"Slide {i+1}: Alt AI {alt_idx + 1} request failed")
                                
                        # ULTIMATE FALLBACK: Create a simple gradient background if everything failed
                        if not slide_img_path:
                            print(f"Slide {i+1}: Creating fallback gradient background...")
                            try:
                                from PIL import ImageDraw
                                # Create a gradient image
                                width, height = 1280, 720
                                img = Image.new('RGB', (width, height))
                                draw = ImageDraw.Draw(img)
                                
                                # Use slide index to vary colors
                                colors = [
                                    ((15, 23, 42), (30, 41, 59)),  # Dark blue
                                    ((17, 24, 39), (31, 41, 55)),  # Dark gray
                                    ((22, 30, 46), (37, 47, 63)),  # Navy
                                    ((20, 25, 40), (35, 40, 55)),  # Deep blue
                                ]
                                color_pair = colors[i % len(colors)]
                                
                                for y in range(height):
                                    r = int(color_pair[0][0] + (color_pair[1][0] - color_pair[0][0]) * y / height)
                                    g = int(color_pair[0][1] + (color_pair[1][1] - color_pair[0][1]) * y / height)
                                    b = int(color_pair[0][2] + (color_pair[1][2] - color_pair[0][2]) * y / height)
                                    draw.line([(0, y), (width, y)], fill=(r, g, b))
                                
                                output = io.BytesIO()
                                img.save(output, format="PNG")
                                png_bytes = output.getvalue()
                                
                                filename = f"slide_{i}_{uuid.uuid4().hex}.png"
                                slide_img_path = str(TEMP_DIR / filename)
                                with open(slide_img_path, "wb") as f:
                                    f.write(png_bytes)
                                print(f"Slide {i+1}: Fallback gradient created.")
                            except Exception as fallback_err:
                                print(f"Slide {i+1}: Even fallback failed: {fallback_err}")
                except Exception as e:
                    print(f"Search failed for slide {i}: {str(e)}")

                slide_images.append(slide_img_path)

        # Step 4: Generate PowerPoint
        print("Step 4: Generating PowerPoint presentation...")
        pptx_buffer = generate_pptx(slides_data, bg_color, slide_images)
        
        # Save locally
        output_filename = args.output or f"presentation_{uuid.uuid4().hex[:8]}.pptx"
        with open(output_filename, "wb") as f:
            f.write(pptx_buffer.getvalue())
            
        print(f"\nSuccess! Presentation saved as: {output_filename}")
        
    except Exception as e:
        print(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main_async())
