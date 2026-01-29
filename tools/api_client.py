"""
Centralized API client initialization for Google GenAI.

This module handles all external API connections and credentials.
It ensures a single point of control for API clients across the application.
"""

import os
from dotenv import load_dotenv
from google import genai

# Load environment variables once at import time
load_dotenv()

# Get API key
_api_key = os.getenv("GOOGLE_API_KEY")
if not _api_key:
    raise ValueError("API Key not found! Check your .env file.")

# Initialize and cache the genai client
_genai_client = genai.Client(api_key=_api_key)


def get_genai_client():
    """
    Returns the initialized Google GenAI client.
    
    This is the single entry point for all GenAI API access throughout the application.
    The client is initialized once and reused.
    
    Returns:
        genai.Client: Initialized Google GenAI client
        
    Raises:
        ValueError: If API key is not configured
    """
    return _genai_client