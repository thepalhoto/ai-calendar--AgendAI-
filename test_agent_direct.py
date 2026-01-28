#!/usr/bin/env python3
"""
Test the actual agent with the Langfuse wrapper to see if that's causing issues.
"""

import os
import sys
import datetime
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

load_dotenv()

# Import the actual agent
from src.agent import get_agent

print("Initializing agent...")
agent = get_agent()
print(f"Agent type: {type(agent)}")
print(f"Agent chat: {agent.chat}")

# Test sending a message
test_messages = [
    "Hello, what date is today?",
    "Add an event called 'Birthday' on 2026-01-27 for the whole day",
]

for msg in test_messages:
    print(f"\n{'='*80}")
    print(f"Message: {msg}")
    print('='*80)
    
    try:
        response = agent.send_message(msg)
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")
        
        if response is not None:
            if hasattr(response, 'text'):
                print(f"Text: {response.text}")
            else:
                print(f"No .text attribute, full response: {str(response)}")
        else:
            print("Response is None!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
