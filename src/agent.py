import os
import sys
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# --- PATH SETUP (BULLETPROOF) ---
# 1. Get the path to the 'src' folder
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the path to the Root folder (one level up)
root_dir = os.path.dirname(current_dir)
# 3. Force add Root to the system path if it's not there
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# --- IMPORTS (Must be after Path Setup) ---
from tools.calendar_ops import add_event, list_events_json, delete_event, check_availability
from config.constants import get_color_rules_text, LLM_MODEL_NAME, LLM_TEMPERATURE
from config.prompts import get_system_instruction  # <--- NEW IMPORT

# 1. Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("API Key not found! Check your .env file.")

genai.configure(api_key=api_key)

# 2. Register Tools
tools_list = [add_event, list_events_json, delete_event, check_availability]

# 3. Dynamic Date Setup
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")

# 4. Fetch Shared Rules
color_rules = get_color_rules_text()

# 5. Define the AI Persona (System Prompt)
# We now fetch this from the config file, passing in the dynamic date and color rules
SYSTEM_INSTRUCTION = get_system_instruction(today_str, color_rules)

def get_agent():
    """
    Initializes and returns the Gemini Chat Session with tools enabled.
    """
    # Define generation config
    generation_config = {
        "temperature": LLM_TEMPERATURE,
    }

    model = genai.GenerativeModel(
        model_name=LLM_MODEL_NAME, # Use constant
        tools=tools_list,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=generation_config
    )
    
    chat = model.start_chat(enable_automatic_function_calling=True)
    return chat