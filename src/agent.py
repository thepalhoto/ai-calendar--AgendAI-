import os
import sys
import datetime
from dotenv import load_dotenv
import traceback

# --- LANGFUSE SETUP (Optional, with fallback) ---
try:
    from langfuse import observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("Warning: Langfuse not available, observability disabled")
    # Create a no-op decorator
    def observe(**kwargs):
        def decorator(func):
            return func
        return decorator

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS ---
from tools.api_client import get_genai_client
from tools.calendar_ops import add_event, list_events_json, delete_event, check_availability, get_conflicts_report
from config.constants import get_color_rules_text, LLM_MODEL_NAME, LLM_TEMPERATURE
from config.prompts import get_system_instruction

# 1. Load environment
load_dotenv()

# 2. Get API client from centralized module
try:
    client = get_genai_client()
except ValueError as e:
    raise ValueError(f"Failed to initialize API client: {str(e)}")

# 3. Register Tools
tools_list = [add_event, list_events_json, delete_event, check_availability, get_conflicts_report]

# 4. Dynamic Date Setup
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")

# 5. Fetch Shared Rules
color_rules = get_color_rules_text()

# 6. Define the AI Persona
SYSTEM_INSTRUCTION = get_system_instruction(today_str, color_rules)

# --- OBSERVABILITY WRAPPER (CRITICAL FOR GROUPING) ---
class LangfuseWrapper:
    def __init__(self, chat_session):
        self.chat = chat_session

    @observe(as_type="generation", name="Agent Turn") 
    def send_message(self, message):
        # This function runs EVERY time you chat.
        # It creates a "Parent Span" that captures all tool calls inside it.
        try:
            response = self.chat.send_message(message)
            
            # Debug: Check what we got
            if response is None:
                print("DEBUG: Response is None from chat.send_message()")
                return None
            
            # The response should have a .text property
            # If it doesn't, it might only contain tool calls
            if hasattr(response, 'text'):
                return response
            
            # If no text attribute, create a wrapper with text property
            if hasattr(response, 'candidates') and response.candidates:
                # Extract text from parts
                text_content = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_content += part.text
                
                # Create a simple response object with text
                class TextResponse:
                    def __init__(self, txt):
                        self.text = txt or "No response generated"
                
                return TextResponse(text_content)
            
            print(f"DEBUG: Returning response with no text or candidates: {type(response)}")
            return response
            
        except Exception as e:
            error_msg = f"Error in send_message: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            # Return a response object with the error message
            class ErrorResponse:
                def __init__(self, txt):
                    self.text = txt
            return ErrorResponse(f"Error: {str(e)}")

def get_agent(user_id: int, username: str) -> LangfuseWrapper:
    """
    Initializes and returns the Gemini Chat Session with dynamic date awareness and user security.
    """
    # 1. Get current time context
    now = datetime.datetime.now()
    today_date = now.strftime("%A, %B %d, %Y")
    current_time = now.strftime("%H:%M")
    
    # 2. Define the dynamic context and security rule
    # We add the date here so the AI knows what "tomorrow" means relative to right now.
    security_instruction = f"""
    ### TEMPORAL CONTEXT:
    - Today's Date is: {today_date}
    - Current Time is: {current_time}

    ### PERSONALIZATION:
    - You are talking to {username}. Address them by name occasionally.

    ### SECURITY RULE:
    - The current user's ID is {user_id}.
    - You MUST use user_id={user_id} for EVERY tool call.
    - NEVER fetch or modify data for any other user ID.
    - When adding events, if the user gives a relative date (e.g. 'tomorrow'), 
      calculate the date based on {today_date}.
    """

    # 3. COMBINE THEM
    # Ensure SYSTEM_INSTRUCTION is defined globally or imported
    full_instruction = SYSTEM_INSTRUCTION + security_instruction

    # 4. Pass 'full_instruction' to the model
    chat = client.chats.create(
        model=LLM_MODEL_NAME,
        config=__import__("google").genai.types.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            system_instruction=full_instruction,
            tools=tools_list,
        )
    )
    
    return LangfuseWrapper(chat)