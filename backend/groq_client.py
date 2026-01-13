"""
Groq API Client Module
Handles AI-powered content structuring using Groq's Llama 3 model
"""
import json
import re
from groq import Groq
from typing import Dict, Optional
import config


class GroqClient:
    """Client for interacting with Groq API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client
        
        Args:
            api_key: Groq API key (defaults to config)
        """
        self.api_key = api_key or config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY in .env file")
        
        self.client = Groq(api_key=self.api_key)
        self.model = config.GROQ_MODEL
        self.temperature = config.GROQ_TEMPERATURE
        self.max_tokens = config.GROQ_MAX_TOKENS
    
    def structure_content_to_slides(self, content: str, max_slides: int = 15) -> Dict:
        """
        Convert text content into structured slide data using AI
        
        Args:
            content: Clean text content
            max_slides: Maximum number of slides to generate (default 15)
            
        Returns:
            Dictionary with 'slides' key containing list of slide objects
        """
        prompt = self._create_prompt(content, max_slides)
        
        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional PowerPoint designer. You create concise, engaging slide decks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response content
            response_text = response.choices[0].message.content
            
            # Parse JSON from response
            slides_data = self._parse_json_response(response_text)
            
            # Validate structure
            self._validate_slides_structure(slides_data)
            
            return slides_data
            
        except Exception as e:
            raise Exception(f"Error calling Groq API: {str(e)}")
    
    def _create_prompt(self, content: str, max_slides: int) -> str:
        """
        Create effective prompt for slide generation
        
        Args:
            content: Text content to convert
            max_slides: Max slides to request
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a professional PowerPoint designer. Convert the following content into a high-impact, professional slide deck.

IMPORTANT - STRUCTURE:
1. CONTENT SLIDES: Create EXACTLY ONE SLIDE FOR EVERY NUMBERED POINT in the input content.
2. If there are {max_slides} points, there must be EXACTLY {max_slides} slides in your response.
3. DO NOT generate an overarching "Title Slide" or "Summary Slide". Start directly with Point 1.
4. DO NOT group or summarize points. Every numbered item deserves its own slide.
5. **STRICT COUNT RULE**: You MUST generate EXACTLY {max_slides} slides in your JSON. Omitting slides is a critical failure.

Output ONLY valid JSON with a key "slides" containing a list, and a top-level key "suggested_bg_color" (use a deep, dark professional hex color like "0F172A").

Each slide must have:
- "title": A short, punchy heading (max 8 words).
  * IMPORTANT: The title MUST include the core subject of the slide (e.g., the name of the City, Country, Person, or Concept mentioned in the point). Never use a generic title if a specific one is available.
- "bullet_points": The main details from that point (2-3 brief, impactful points).
  * IMPORTANT: Ensure no key facts like location names, names of people, or specific nouns are omitted. If the content is a NUMERICAL PROBLEM or a QUESTION, you MUST include BOTH the full question and the step-by-step solution/answer in the bullet points. Do not summarize or omit the steps.
- "visual_query": A highly specific image description that MUST INCLUDE THE MAIN SUBJECT + a style keyword. Example: "A clear photo of a wind turbine in a field, cinematic lighting", "A portrait of Albert Einstein, professional black and white", or "A computer server room, blue lighting". Do NOT just ask for "blurred texture" unless the slide is purely abstract.
  * CRITICAL FOR NUMERICAL/MATH PROBLEMS - BE CONTEXT-AWARE:
    - IF the problem mentions SPECIFIC OBJECTS (cloth, eggs, money, shopkeeper, farmer, calendar, etc.), use that object in the visual query. Example: "Colorful fabric cloth rolls", "Fresh eggs in carton", "Indian rupee notes", "Shopkeeper at counter"
    - IF the problem is PURE ABSTRACT MATH (percentages, numbers, equations with no real-world context), you MUST use a DIFFERENT math concept for EACH slide. Add the slide number to your mental tracking:
      * Slide 1: "Geometric compass drawing circles on blueprint"
      * Slide 2: "Vintage abacus with wooden beads"
      * Slide 3: "Neon mathematical symbols glowing in dark"
      * Slide 4: "Graph paper with hand-drawn equations"
      * Slide 5: "Scientific calculator buttons closeup"
      * Slide 6: "Protractor measuring angles on desk"
      * Slide 7: "Chalkboard with colorful chalk formulas"
      * Slide 8: "Digital LED number display"
      * Slide 9: "Ruler and pencil on engineering drawing"
      * Slide 10: "Mathematical textbook open on table"
      * Slide 11: "Student solving problem on tablet"
      * Slide 12: "3D geometric shapes floating"
      * Slide 13: "Fibonacci spiral in nature"
      * Slide 14: "Binary code matrix background"
      * Slide 15: "Ancient counting stones"
      * Then continue with: "Math teacher at whiteboard", "Trigonometry triangle diagram", "Algebra symbols on paper", "Statistics graph chart", "Geometry set tools", etc.
  * ABSOLUTE RULE: NEVER use the same visual query twice. Track what you've used and always pick something new.
- "accent_color": A vibrant, high-contrast hex color (e.g., bright yellow "FDE047" or cyan "22D3EE").

Rules:
1. NO generic Title Slide. Start immediately with the first point.
2. One slide per numbered point.
3. **CRITICAL UNIQUENESS RULE**: You MUST ensure that NO TWO SLIDES have the same or similar visual_query. For example:
   - DO NOT use "A person holding a calculator" more than once
   - DO NOT use "A student at chalkboard" more than once
   - DO NOT use "A person with math symbols" more than once
   - If you've used "calculator", next time use "abacus", then "protractor", then "compass", etc.
   - Track mentally what you've already used and ALWAYS pick something completely different
4. You MUST generate EXACTLY {max_slides} slides total. Do not skip any numbered points.
5. For "suggested_bg_color", pick a VERY DARK professional hex color to ensure text pops.
6. Output ONLY the JSON object.

Content to convert:
{content}

Remember: Output ONLY the complete JSON object, nothing else."""
        
        return prompt
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON from AI response, handling potential formatting issues
        
        Args:
            response_text: Raw response from AI
            
        Returns:
            Parsed JSON dictionary
        """
        # Try to extract JSON from response
        # Sometimes AI might wrap JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from AI response: {str(e)}\nResponse: {response_text}")
    
    def _validate_slides_structure(self, slides_data: Dict) -> None:
        """
        Validate that slides data has correct structure
        
        Args:
            slides_data: Parsed slides dictionary
            
        Raises:
            ValueError: If structure is invalid
        """
        if not isinstance(slides_data, dict):
            raise ValueError("Slides data must be a dictionary")
        
        if 'slides' not in slides_data:
            raise ValueError("Slides data must contain 'slides' key")
        
        if 'suggested_bg_color' not in slides_data:
            slides_data['suggested_bg_color'] = "2E5A88" # Corporate Blue Default
            
        if not isinstance(slides_data['slides'], list):
            raise ValueError("'slides' must be a list")
        
        for i, slide in enumerate(slides_data['slides']):
            if not isinstance(slide, dict):
                raise ValueError(f"Slide {i} must be a dictionary")
            
            if 'title' not in slide:
                raise ValueError(f"Slide {i} missing 'title' field")
            
            if 'visual_query' not in slide:
                # Add default if missing
                slide['visual_query'] = slide['title']
            
            if 'layout' not in slide:
                slide['layout'] = 'center'
                
            if 'accent_color' not in slide:
                slide['accent_color'] = "6366f1" # Default purple indigo
            
            if not isinstance(slide.get('bullet_points', []), list):
                slide['bullet_points'] = []
    def generate_image_prompt(self, content: str) -> str:
        """
        Generate a vivid image description prompt based on content
        
        Args:
            content: Clean text content
            
        Returns:
            Short, vivid image prompt (max 15 words)
        """
        prompt = f"""Analyze the following content and create a short, vivid image generation prompt that captures its main theme.
The prompt should be suitable for a high-quality PowerPoint background.

Rules:
1. MAX 15 words.
2. Focus on a single, clear visual theme.
3. Use professional, modern artistic styles (e.g., "minimalist", "digital art", "professional").
4. Output ONLY the prompt string, nothing else. Do not wrap the prompt in quotes.

Content:
{content}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a creative visual designer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: Failed to generate image prompt: {str(e)}")
            return "Professional business presentation background, abstract design"
