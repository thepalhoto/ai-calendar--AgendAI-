#!/usr/bin/env python3
"""
Test specifically for tool calling to see if the agent properly calls tools.
"""

import os
import sys
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from google import genai
from tools.calendar_ops import add_event, list_events_json

# Load API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# Create a simple chat for tool testing
chat = client.chats.create(
    model="gemini-flash-latest",
    config=genai.types.GenerateContentConfig(
        temperature=0.0,
        tools=[add_event],
    )
)

# Try a message that should trigger a tool call
message = "Add an event called 'Test Meeting' on 2026-01-27 from 10:00 to 11:00"
print(f"\nSending message: {message}\n")

response = chat.send_message(message)

print(f"Response type: {type(response)}")
print(f"Has text: {hasattr(response, 'text')}")
print(f"Text: {response.text}")
print(f"Candidates: {len(response.candidates) if response.candidates else 0}")

if response.candidates:
    candidate = response.candidates[0]
    print(f"Candidate content: {candidate.content}")
    print(f"Candidate parts: {candidate.content.parts if candidate.content else 'No content'}")
    
    if candidate.content and candidate.content.parts:
        for i, part in enumerate(candidate.content.parts):
            print(f"  Part {i}: {type(part).__name__}")
            if hasattr(part, 'function_call'):
                print(f"    Function call: {part.function_call}")
