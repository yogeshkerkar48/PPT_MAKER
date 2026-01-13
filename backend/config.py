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

# Runware.ai Configuration (For AI Image Generation Backup)
RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY")
RUNWARE_MODEL_ID = "civitai:133005@471120"  # Juggernaut XL (Verified Stable)

# Redis Configuration (For Celery)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
