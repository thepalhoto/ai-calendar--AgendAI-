import sys
import os

# --- PATH SETUP & DEBUGGING ---
# 1. Get the current folder (tests)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Get the parent folder (project root)
parent_dir = os.path.dirname(current_dir)

# 3. Add to path
sys.path.insert(0, parent_dir)

print(f"DEBUG: Current Script Location: {current_dir}")
print(f"DEBUG: Calculated Project Root: {parent_dir}")

# 4. Check if 'tools' folder actually exists there
tools_path = os.path.join(parent_dir, 'tools')

if not os.path.exists(tools_path):
    print(f"\n❌ CRITICAL ERROR: Python cannot find a folder named 'tools' at:\n{tools_path}")
    print("Please check: Did you name the folder 'tool' (singular)? Is it inside another folder?")
    sys.exit(1)
else:
    print(f"✅ Found 'tools' folder at: {tools_path}")
    print(f"Files inside 'tools': {os.listdir(tools_path)}")
    
    # Check specifically for calendar_ops.py
    if 'calendar_ops.py' not in os.listdir(tools_path):
        print("\n❌ CRITICAL ERROR: Found the 'tools' folder, but 'calendar_ops.py' is missing!")
        print("Did you name it 'calendar_ops.txt' or something else?")
        sys.exit(1)

print("-" * 30)
# --- END DEBUGGING ---

# Now try the import
try:
    from tools.calendar_ops import add_event, list_events_json, delete_event
    print("✅ Import Successful! Proceeding with tests...\n")
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    sys.exit(1)

# 1. Add an All-Day Event (Date only)
print(add_event(
    title="Holiday", 
    start="2023-07-03", 
    end="2023-07-05", 
    allDay=True, 
    color="#FF6C6C"
))

# 2. Add a Timed Event (ISO Format)
print(add_event(
    title="Meeting", 
    start="2023-07-01T08:30:00+01:00", 
    end="2023-07-01T10:30:00+01:00", 
    allDay=False, 
    color="#3788d8"
))

# 3. Add a RECURRING Event (Weekly Team Sync)
print(add_event(
    title="Weekly Sync", 
    start="2023-07-07T10:00:00+01:00", 
    end="2023-07-07T11:00:00+01:00", 
    allDay=False, 
    recurrence="weekly",  # <--- Testing your new feature!
    color="#28a745"       # Green color
))

# 3. Check the JSON output
print("\nJSON Output for Calendar:")
print(list_events_json())