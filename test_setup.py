#!/usr/bin/env python3
"""
Diagnostic script to test the agent setup and API connectivity.
Run this to check if everything is properly configured.
"""

import os
import sys
import traceback

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- TEST 1: Check API Key ---
print("=" * 80)
print("TEST 1: Checking API Key")
print("=" * 80)
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    print(f"✓ API Key found (length: {len(api_key)})")
else:
    print("✗ API Key not found! Check your .env file")
    sys.exit(1)

# --- TEST 2: Test Client Initialization ---
print("\n" + "=" * 80)
print("TEST 2: Initializing Client")
print("=" * 80)
try:
    from google import genai
    client = genai.Client(api_key=api_key)
    print("✓ Client initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize client: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- TEST 3: Check Tools ---
print("\n" + "=" * 80)
print("TEST 3: Loading Tools")
print("=" * 80)
try:
    from tools.calendar_ops import (
        add_event, list_events_json, delete_event, 
        check_availability, get_conflicts_report
    )
    tools_list = [add_event, list_events_json, delete_event, check_availability, get_conflicts_report]
    print(f"✓ Loaded {len(tools_list)} tools:")
    for tool in tools_list:
        print(f"  - {tool.__name__}: {tool.__doc__.split(chr(10))[0]}")
except Exception as e:
    print(f"✗ Failed to load tools: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- TEST 4: Load Configuration ---
print("\n" + "=" * 80)
print("TEST 4: Loading Configuration")
print("=" * 80)
try:
    from config.constants import LLM_MODEL_NAME, LLM_TEMPERATURE
    from config.prompts import get_system_instruction
    import datetime
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    sys.instruction = get_system_instruction(today_str, "Test")
    
    print(f"✓ Configuration loaded")
    print(f"  - Model: {LLM_MODEL_NAME}")
    print(f"  - Temperature: {LLM_TEMPERATURE}")
except Exception as e:
    print(f"✗ Failed to load configuration: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- TEST 5: Create Chat Session ---
print("\n" + "=" * 80)
print("TEST 5: Creating Chat Session")
print("=" * 80)
try:
    from config.constants import get_color_rules_text
    
    color_rules = get_color_rules_text()
    sys_instruction = get_system_instruction(today_str, color_rules)
    
    chat = client.chats.create(
        model=LLM_MODEL_NAME,
        config=genai.types.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            system_instruction=sys_instruction,
            tools=tools_list,
        )
    )
    print("✓ Chat session created successfully")
    print(f"  - Chat object type: {type(chat)}")
except Exception as e:
    print(f"✗ Failed to create chat session: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- TEST 6: Send Test Message ---
print("\n" + "=" * 80)
print("TEST 6: Sending Test Message")
print("=" * 80)
try:
    test_message = "Hello! What date is today?"
    response = chat.send_message(test_message)
    
    print(f"✓ Message sent successfully")
    print(f"  - Response type: {type(response)}")
    print(f"  - Has .text: {hasattr(response, 'text')}")
    
    if hasattr(response, 'text'):
        print(f"  - Response text: {response.text[:100]}...")
    else:
        print(f"  - Response: {str(response)[:100]}...")
        
except Exception as e:
    print(f"✗ Failed to send message: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED!")
print("=" * 80)
