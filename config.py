"""
Configuration module for HTML to PowerPoint converter
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TEMPERATURE = 0.3
GROQ_MAX_TOKENS = 8000  # Significant increase for 51-slide JSON structures

# File Upload Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_FORMATS = ["image/png", "image/jpeg", "image/jpg"]

# Content Processing Configuration
MAX_HTML_LENGTH = 20000  # Increased to handle ~50-100 points
MAX_RETRIES = 3
API_TIMEOUT = 30  # seconds

# PowerPoint Configuration
DEFAULT_SLIDE_WIDTH = 10  # inches
DEFAULT_SLIDE_HEIGHT = 7.5  # inches
TITLE_FONT_SIZE = 44
CONTENT_FONT_SIZE = 24
BULLET_FONT_SIZE = 20

# AI Image Generation Configuration (Multiple services to avoid rate limits)
POLLINATIONS_MODEL = "turbo"  # Changed from flux to turbo (faster, different quota)
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?model={model}&width=1280&height=720&nologo=true&private=true"

# Alternative AI Image Generators (completely different services)
ALTERNATIVE_AI_URLS = [
    # Pollinations with turbo model (different quota than flux)
    "https://image.pollinations.ai/prompt/{prompt}?model=turbo&width=1280&height=720&nologo=true",
    # Pollinations without model specification (uses default)
    "https://image.pollinations.ai/prompt/{prompt}?width=1280&height=720",
    # Direct Pollinations endpoint
    "https://pollinations.ai/p/{prompt}",
]

# Serper.dev Configuration (Google Images)
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_URL = "https://google.serper.dev/images"
