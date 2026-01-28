"""
Document extraction module for processing schedule images via vision AI.
Separated from UI layer for reusability and testability.
"""

import datetime
import json
import io
import base64
from PIL import Image
from google import genai


def extract_events_from_image(
    image: Image.Image,
    genai_client,
    event_categories: dict,
    vision_model_name: str,
    get_vision_prompt_fn,
    user_hint: str = ""
) -> list:
    """
    Sends an image + user context to Gemini and extracts a JSON list with event categories.
    
    Args:
        image: PIL Image object to process
        genai_client: Initialized Google genai Client
        event_categories: Dict mapping category names to colors
        vision_model_name: Model to use for vision extraction
        get_vision_prompt_fn: Function that returns the vision prompt
        user_hint: Optional user context (e.g., "next week", "following week")
    
    Returns:
        List of extracted events as dicts, or empty list on error
    """
    if not genai_client:
        raise ValueError("API Key not configured for vision extraction.")
    
    today = datetime.date.today()
    
    # 1. Calculate THIS week's Monday
    start_of_week = today - datetime.timedelta(days=today.weekday())

    # 2. INTELLIGENT DATE SHIFT based on user hint
    if user_hint:
        hint_lower = user_hint.lower()
        if "next week" in hint_lower or "incoming week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
        elif "following week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
            
    monday_str = start_of_week.strftime("%Y-%m-%d")
    
    # 3. Extract valid keys for the prompt
    valid_keys = ", ".join(event_categories.keys())
    
    # 4. FETCH PROMPT FROM CONFIG
    prompt = get_vision_prompt_fn(monday_str, valid_keys, user_hint)
    
    # 5. Convert PIL Image to bytes
    # Handle RGBA/transparency by converting to RGB
    if image.mode in ('RGBA', 'LA', 'P'):
        # Create white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
        image = background
    
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='JPEG')
    image_bytes = image_bytes.getvalue()
    
    # 6. Encode image as base64
    image_b64 = base64.standard_b64encode(image_bytes).decode('utf-8')
    
    # 7. Send to Gemini and extract events
    response = genai_client.models.generate_content(
        model=vision_model_name,
        contents=[
            genai.types.Part.from_text(text=prompt),
            genai.types.Part(
                inline_data=genai.types.Blob(
                    mime_type='image/jpeg',
                    data=image_b64
                )
            )
        ]
    )
    text_data = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text_data)
