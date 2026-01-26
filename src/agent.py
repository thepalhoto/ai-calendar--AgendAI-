import os
import sys
import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from langfuse import observe  # <--- Standard import

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS ---
from tools.calendar_ops import add_event, list_events_json, delete_event, check_availability, get_conflicts_report
from config.constants import get_color_rules_text, LLM_MODEL_NAME, LLM_TEMPERATURE
from config.prompts import get_system_instruction

# 1. Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("API Key not found! Check your .env file.")

genai.configure(api_key=api_key)

# 2. Register Tools
tools_list = [add_event, list_events_json, delete_event, check_availability, get_conflicts_report]

# 3. Dynamic Date Setup
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")

# 4. Fetch Shared Rules
color_rules = get_color_rules_text()

# 5. Define the AI Persona
SYSTEM_INSTRUCTION = get_system_instruction(today_str, color_rules)

# --- OBSERVABILITY WRAPPER (CRITICAL FOR GROUPING) ---
class LangfuseWrapper:
    def __init__(self, chat_session):
        self.chat = chat_session

    @observe(as_type="generation", name="Agent Turn") 
    def send_message(self, message):
        # This function runs EVERY time you chat.
        # It creates a "Parent Span" that captures all tool calls inside it.
        return self.chat.send_message(message)

def get_agent():
    """
    Initializes and returns the Gemini Chat Session WRAPPED for tracing.
    """
    generation_config = {
        "temperature": LLM_TEMPERATURE,
    }

    model = genai.GenerativeModel(
        model_name=LLM_MODEL_NAME, 
        tools=tools_list,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=generation_config
    )
    
    chat = model.start_chat(enable_automatic_function_calling=True)
    
    # Return the Wrapper, not the raw chat
    return LangfuseWrapper(chat)