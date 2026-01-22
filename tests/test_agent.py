import sys
import os

# --- PATH SETUP (BULLETPROOF) ---
# 1. Get the folder where THIS script lives (e.g., .../tests)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Get the Parent Folder (Project Root)
# This moves up one level from 'tests' to 'ai-calendar--AgendaAI-'
project_root = os.path.dirname(current_dir)

# 3. Add the Project Root to Python's search path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"DEBUG: Project Root added to path: {project_root}")
# --------------------------------

try:
    from src.agent import get_agent
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Could not import 'src.agent'.\nReason: {e}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def run_chat():
    print("--- AgendaAI Terminal Interface (Type 'quit' to exit) ---")
    
    try:
        chat = get_agent()
        print("✅ Agent connected. System ready.")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Exiting...")
            break
            
        try:
            # Send message to Gemini
            response = chat.send_message(user_input)
            print(f"AI: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_chat()