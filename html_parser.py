"""
HTML Parser Module
Cleans HTML content and extracts meaningful text for AI processing
"""
from bs4 import BeautifulSoup
from typing import List
import re


def is_html(content: str) -> bool:
    """
    Check if content contains HTML tags
    
    Args:
        content: String to check
        
    Returns:
        True if content appears to be HTML
    """
    # Check for common HTML tags
    html_pattern = r'<\s*(html|head|body|div|p|span|h[1-6]|a|img|script|style)'
    return bool(re.search(html_pattern, content, re.IGNORECASE))



def clean_html(html_content: str) -> str:
    """
    Clean HTML content and extract readable text
    If content is plain text, return it directly
    
    Args:
        html_content: Raw HTML string or plain text
        
    Returns:
        Clean text content ready for AI processing
    """
    # Check if content is actually HTML
    if not is_html(html_content):
        # It's plain text, just clean up whitespace
        lines = html_content.split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(clean_lines)
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # Extract text content
    text_lines = extract_text_content(soup)
    
    # Join lines with newlines
    clean_text = '\n'.join(text_lines)
    
    # Clean up extra whitespace
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
    
    return clean_text.strip()


def extract_text_content(soup: BeautifulSoup) -> List[str]:
    """
    Extract text content from BeautifulSoup object
    
    Args:
        soup: BeautifulSoup parsed HTML
        
    Returns:
        List of text lines
    """
    # Get all text
    text = soup.get_text(separator='\n')
    
    # Split into lines
    lines = text.split('\n')
    
    # Filter out empty lines and strip whitespace
    clean_lines = [line.strip() for line in lines if line.strip()]
    
    return clean_lines


def truncate_content(content: str, max_length: int = 3000) -> str:
    """
    Truncate content to fit within token limits
    
    Args:
        content: Text content
        max_length: Maximum character length
        
    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content
    
    # Truncate at word boundary
    truncated = content[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + "..."
