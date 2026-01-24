import streamlit as st
from streamlit_calendar import calendar
import json
import datetime
from PIL import Image
import google.generativeai as genai
import sys
import os

# --- PATH SETUP (BULLETPROOF) ---
# 1. Get path to Root
root_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get path to Config
config_dir = os.path.join(root_dir, 'config')

# 3. Add both to sys.path to ensure imports work
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if config_dir not in sys.path:
    sys.path.insert(0, config_dir)

# --- IMPORTS ---
from src.agent import get_agent
from tools.calendar_ops import list_events_json, add_event
# Robust Import: Try package import first, fallback to direct
try:
    from config.constants import EVENT_CATEGORIES 
except ImportError:
    try:
        from constants import EVENT_CATEGORIES
    except ImportError:
        # Fallback if config is totally missing (prevents crash)
        EVENT_CATEGORIES = {"Other": "#999999"}
        st.error("⚠️ Could not load config/constants.py. Defaulting to Grey.")

# --- PAGE SETUP ---
st.set_page_config(page_title="AgendAI", layout="wide")

st.markdown(
    "<h1 style='text-align: center;'>📅 AgendAI: Your Smart Schedule Assistant</h1>", 
    unsafe_allow_html=True
)

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    try:
        st.session_state.agent = get_agent()
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm AgendAI. How can I help you manage your schedule today?"})
    except Exception as e:
        st.error(f"Error initializing AI: {e}")

# --- HELPER: VISION EXTRACTION ---
def extract_events_from_image(image, user_hint=""):
    """
    Sends an image + user context to Gemini and asks for a strict JSON list with CATEGORIES.
    """
    vision_model = genai.GenerativeModel('gemini-2.0-flash') 
    
    today = datetime.date.today()
    
    # 1. Calculate THIS week's Monday
    start_of_week = today - datetime.timedelta(days=today.weekday())

    # --- INTELLIGENT DATE SHIFT ---
    if user_hint:
        hint_lower = user_hint.lower()
        if "next week" in hint_lower or "incoming week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
        elif "following week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
            
    monday_str = start_of_week.strftime("%Y-%m-%d")
    
    # Extract valid keys for the prompt
    valid_keys = ", ".join(EVENT_CATEGORIES.keys())
    
    prompt = f"""
    You are an expert at extracting events from schedule images.
    
    TASK:
    Analyze this visual schedule and extract ALL events into a JSON list.

    1. **DATE & TIME LOGIC:**
       - **Anchor:** Treat the Monday column (or start of week) as **{monday_str}**.
       - **Weekly View:** Vertical columns. Mon, Tue, Wed...
       - **Monthly View:** Grid. If specific times hidden, set "allDay": true.
    
    2. **EVENT DETAILS:**
       - **Title:** Extract exact text. If cut off, add "[TRUNCATED]".
       - **Recurrence:** Default to null. ONLY set if user hint explicitly says "repeat/weekly".
       
       - **CATEGORY (CRITICAL):** Do NOT extract the color from the image. 
         Analyze the Title/Context and assign one of these EXACT keys:
         [{valid_keys}]
         
         *Examples:*
         - "Dentist" -> "Health"
         - "Deep Learning", "Lecture" -> "Work_School"
         - "Soccer", "Gym" -> "Extracurricular"
         - "Meeting", "Sync" -> "Meetings"
         - If unsure -> "Other"

    3. **GRID RULES:**
       - **Double Booking:** If events overlap visually, **EXTRACT ALL OF THEM.**
    
    USER HINT: "{user_hint}"
    
    OUTPUT FORMAT (Strict JSON):
    [
      {{
        "title": "Event Title",
        "start": "YYYY-MM-DDTHH:MM:SS",
        "end": "YYYY-MM-DDTHH:MM:SS",
        "allDay": boolean,
        "category": "One_Of_The_Valid_Keys",
        "recurrence": "weekly" or null
      }}
    ]
    """
    
    try:
        response = vision_model.generate_content([prompt, image])
        text_data = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_data)
    except Exception as e:
        st.error(f"Vision Processing Error: {e}")
        return []

# --- SIDEBAR SETUP ---
with st.sidebar:
    # 1. VISUAL IMPORT
    st.header("📷 Visual Import")
    
    uploaded_file = st.file_uploader("Upload schedule image", type=["png", "jpg", "jpeg", "webp"])
    user_hint = st.text_input("Context (Optional)", placeholder="e.g., 'Weekly starting Monday'")
    
    if uploaded_file is not None:
        if st.button("Process Image", type="primary"): 
            with st.spinner("👀 Reading document..."):
                image = Image.open(uploaded_file)
                extracted_events = extract_events_from_image(image, user_hint)
                
                added_titles = [] 
                
                if extracted_events:
                    progress_bar = st.progress(0)
                    for i, event in enumerate(extracted_events):
                        try:
                            title = event.get("title", "Untitled")
                            
                            # --- COLOR ASSIGNMENT LOGIC ---
                            # 1. Get the category AI found (e.g. "Work_School")
                            ai_category = event.get("category", "Other")
                            
                            # 2. Map to Hex Code (e.g. "#0a9905")
                            # Fallback to Grey if the AI hallucinates a new key
                            final_color = EVENT_CATEGORIES.get(ai_category, EVENT_CATEGORIES["Other"])
                            
                            # 3. Force add with the specific color
                            add_event(
                                title=title,
                                start=event.get("start"),
                                end=event.get("end"),
                                allDay=event.get("allDay", False),
                                recurrence=event.get("recurrence", None),
                                recurrence_end=event.get("recurrence_end", None),
                                color=final_color 
                            )
                            added_titles.append(f"{title} ({ai_category})")
                        except Exception as e:
                            st.error(f"Failed to add {title}: {e}")
                        
                        progress_bar.progress((i + 1) / len(extracted_events))
                    
                    st.success(f"✅ Imported {len(added_titles)} events.")
                    
                    if added_titles:
                        sync_text = f"SYSTEM UPDATE: Visual Import used. Added: {', '.join(added_titles)}."
                        try:
                            st.session_state.agent.send_message(sync_text)
                            st.session_state.messages.append({"role": "assistant", "content": f"I've processed your image. Based on the titles, I categorized and colored **{len(added_titles)}** events."})
                        except Exception as e:
                            print(f"Sync Error: {e}")
                    
                    st.rerun()
                else:
                    st.warning("No events found in the image.")

    st.markdown("---")

    # 2. AUDIT
    st.subheader("🛡️ Audit")
    
    if st.button("Check for Conflicts"):
        with st.spinner("Analyzing schedule logic..."):
            try:
                from tools.calendar_ops import get_conflicts_report
                report = get_conflicts_report()
                
                if "No conflicts" in report:
                    st.success(report)
                else:
                    with st.expander("Conflicts Detected!", expanded=True):
                        st.markdown(report)
            except ImportError:
                st.error("Function 'get_conflicts_report' not found.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    # 3. CHAT HISTORY
    st.header("💬 Chat Assistant")
    
    messages_container = st.container()
    
    with messages_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 4. CHAT INPUT
    if prompt := st.chat_input("Add a meeting, check schedule..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with messages_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with messages_container:
            with st.chat_message("assistant"):
                try:
                    response_placeholder = st.empty()
                    response_placeholder.markdown("Thinking...")
                    response = st.session_state.agent.send_message(prompt)
                    response_placeholder.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- MAIN PAGE: CALENDAR ---
st.subheader("🗓️ Calendar View")

events_json_str = list_events_json()
events_list = json.loads(events_json_str)

calendar_options = {
    "editable": False,
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay,listMonth"
    },
    "initialView": "dayGridMonth",
    "slotMinTime": "00:00:00",
    "slotMaxTime": "24:00:00",
    "height": "650px",
}

calendar(events=events_list, options=calendar_options, key=str(len(st.session_state.messages)))