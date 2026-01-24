import streamlit as st
from streamlit_calendar import calendar
import json
import datetime
from PIL import Image
import google.generativeai as genai

# Import your Agent and Database tools
from src.agent import get_agent
from tools.calendar_ops import list_events_json, add_event

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

# --- HELPER: VISION EXTRACTION (Updated Prompt) ---
def extract_events_from_image(image, user_hint=""):
    """
    Sends an image + user context to Gemini and asks for a strict JSON list.
    """
    vision_model = genai.GenerativeModel('gemini-2.0-flash') 
    
    today = datetime.date.today()
    
    # 1. Calculate THIS week's Monday
    start_of_week = today - datetime.timedelta(days=today.weekday())

    # --- INTELLIGENT DATE SHIFT ---
    # If the user hints at the future, move the anchor date forward in Python
    # so the AI doesn't have to guess.
    if user_hint:
        hint_lower = user_hint.lower()
        if "next week" in hint_lower or "incoming week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
        elif "following week" in hint_lower:
            start_of_week += datetime.timedelta(days=7)
            
    monday_str = start_of_week.strftime("%Y-%m-%d")
    
    prompt = f"""
    You are an expert at extracting events from schedule images (Monthly, Weekly, or Daily).
    
    TASK:
    Analyze this visual schedule, DETECT the type (Monthly/Weekly/Daily), and extract ALL events into a JSON list.

    1. **AUTO-DETECT CALENDAR TYPE:**
       - **Weekly/Grid:** Vertical columns for days, Time on the left axis.
       - **Monthly:** Standard 7-column grid (Sun-Sat or Mon-Sun) with numeric dates in boxes.
       - **Daily:** A single day column with a time axis.

    2. **DATE & TIME LOGIC:**
       - **Anchor:** Treat the **Monday column** (or start of week) in this image as being **{monday_str}**.
       - **Weekly View (Default):**
         - Assume the FIRST column of events is MONDAY.
         - Subsequent columns are Tue, Wed, Thu, Fri, etc.
       - **Monthly View:**
         - If specific times are NOT visible in the box, set "allDay": true.
       - **Daily View:** Treat as a Weekly view with only one day column.
    
    3. **EVENT DETAILS:**
       - **Colors:** Extract the DOMINANT color of the event box (Hex code). Default to null if black/white.
       - **Truncated Text:** If a title seems cut off (e.g., "Intro to Comp..."), flag it by adding "[TRUNCATED]" to the title so the user knows.
       - **Recurrence:** Default to null (NO recurrence).
          - ONLY set recurrence if the User Hint EXPLICITLY uses words like "repeat", "recurring", or "every week".
          - **CRITICAL:** Phrases like "next week", "this week", or "incoming week" define the DATE range, NOT the recurrence. Do not make events recurring just because the view is weekly.
    
    4. **GRID RULES (for Weekly/Daily):**
       - The leftmost axis is TIME. Use box height to calculate exact start/end.
       - **Double Booking Resolution:**
         - If the image visually shows two distinct blocks occupying the SAME time slot (overlapping or side-by-side), **EXTRACT ALL OF THEM.**
         - **Action:** Create a separate JSON object for every distinct event box you see.
         - **Do NOT filter** or pick a "winner". It is perfectly fine to return multiple events starting at the exact same time.
    
    USER HINT: "{user_hint}"
    (Use this hint to override assumptions, e.g., "Recurrence is weekly", "Start date is...").
    
    OUTPUT FORMAT (Strict JSON):
    [
      {{
        "title": "Event Title",
        "start": "YYYY-MM-DDTHH:MM:SS",
        "end": "YYYY-MM-DDTHH:MM:SS",
        "allDay": boolean,
        "backgroundColor": "#HexCode",
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
    # ==========================================
    # 1. TOP SECTION: VISUAL IMPORT
    # ==========================================
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
                            add_event(
                                title=title,
                                start=event.get("start"),
                                end=event.get("end"),
                                allDay=event.get("allDay", False),
                                recurrence=event.get("recurrence", None),
                                recurrence_end=event.get("recurrence_end", None)
                            )
                            added_titles.append(title)
                        except Exception as e:
                            st.error(f"Failed to add {title}: {e}")
                        
                        progress_bar.progress((i + 1) / len(extracted_events))
                    
                    st.success(f"✅ Imported {len(added_titles)} events.")
                    
                    # --- SYNC WITH AGENT MEMORY ---
                    if added_titles:
                        sync_text = f"SYSTEM UPDATE: Visual Import tool used. Events added: {', '.join(added_titles)}."
                        try:
                            st.session_state.agent.send_message(sync_text)
                            st.session_state.messages.append({"role": "assistant", "content": f"I've processed your image and added **{len(added_titles)}** new events to the calendar."})
                        except Exception as e:
                            print(f"Sync Error: {e}")
                    
                    st.rerun()
                else:
                    st.warning("No events found in the image.")

    st.markdown("---")

    # ==========================================
    # 2. MIDDLE SECTION: AUDIT (Conflict Check)
    # ==========================================
    st.subheader("🛡️ Audit")
    
    if st.button("Check for Conflicts"):
        with st.spinner("Analyzing schedule logic..."):
            try:
                from tools.calendar_ops import get_conflicts_report
                report = get_conflicts_report()
                
                if "No conflicts" in report:
                    st.success(report)
                else:
                    # Use an expander for long conflict reports so it doesn't clutter
                    with st.expander("Conflicts Detected!", expanded=True):
                        st.markdown(report)
            except ImportError:
                st.error("Function 'get_conflicts_report' not found. Did you update calendar_ops.py?")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    # ==========================================
    # 3. BOTTOM SECTION: CHAT HISTORY
    # ==========================================
    st.header("💬 Chat Assistant")
    
    # Container for chat messages (scrollable area)
    messages_container = st.container()
    
    with messages_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # ==========================================
    # 4. PINNED FOOTER: CHAT INPUT
    # ==========================================
    # Chat Input (Pins to bottom automatically)
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
    "slotMinTime": "06:00:00",
    "slotMaxTime": "22:00:00",
    "height": "650px",
}

calendar(events=events_list, options=calendar_options, key=str(len(st.session_state.messages)))