#!/usr/bin/env python3
"""Debug script to test imports"""
import sys
import traceback

print("=" * 60)
print("Testing imports...")
print("=" * 60)

try:
    print("1. Importing streamlit...")
    import streamlit as st
    print("   ✓ streamlit imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Importing streamlit_calendar...")
    from streamlit_calendar import calendar
    print("   ✓ streamlit_calendar imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Importing config.constants...")
    from config.constants import get_color_rules_text, LLM_MODEL_NAME, LLM_TEMPERATURE
    print("   ✓ config.constants imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Importing config.prompts...")
    from config.prompts import get_system_instruction
    print("   ✓ config.prompts imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("5. Importing src.agent...")
    from src.agent import get_agent
    print("   ✓ src.agent imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("6. Importing tools.calendar_ops...")
    from tools.calendar_ops import list_events_json
    print("   ✓ tools.calendar_ops imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("All imports successful!")
print("=" * 60)
