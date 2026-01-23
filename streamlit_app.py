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

# --- HELPER: VISION EXTRACTION (Improved Version) ---
def extract_events_from_image(image, user_hint=""):
    """
    Sends an image + user context to Gemini and asks for a strict JSON list.
    """
    vision_model = genai.GenerativeModel('gemini-2.0-flash') 
    
    today = datetime.date.today()
    
    # Anchor date for Monday calculation
    start_of_week = today - datetime.timedelta(days=today.weekday())
    monday_str = start_of_week.strftime("%Y-%m-%d")
    
    prompt = f"""
    You are an expert at extracting academic schedules from grid-based images.
    
    TASK:
    Analyze this visual schedule and extract ALL events into a JSON list.
    
    CRITICAL GRID RULES:
    1. **Time Axis:** The leftmost column shows time slots (e.g., 08H00, 08H30). Use these to determine the EXACT start and end time of every block. 
       - If a block starts halfway between 08H00 and 09H00, it is 08:30.
       - The height of the box indicates duration. A tall box means a long event.
    2. **Day Axis:** The columns from left to right usually represent Monday, Tuesday, Wednesday, Thursday, Friday.
       - Assume the First Event Column = Monday, unless headers say otherwise.
    3. **No Merging:** If two blocks are visually distinct (separated by white space), they are DIFFERENT events. Do not merge them even if they have the same name.
    
    USER HINT: "{user_hint}"
    (Use this hint to override assumptions, e.g., "This schedule starts on Tuesday").
    
    ANCHOR DATE:
    - Assume "Monday" corresponds to: {monday_str}
    - Calculate the specific date for each column based on this anchor.
    
    OUTPUT FORMAT (Strict JSON):
    [
      {{
        "title": "Course Name - Room",
        "start": "YYYY-MM-DDTHH:MM:SS",
        "end": "YYYY-MM-DDTHH:MM:SS",
        "recurrence": "weekly" (default to weekly for academic schedules unless specified otherwise)
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

# --- SIDEBAR: CHAT & UPLOAD ---
with st.sidebar:
    st.header("💬 Chat Assistant")
    
    # Container for chat messages
    messages_container = st.container()
    
    with messages_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # --- DOCUMENT INGESTION WIDGET ---
    st.markdown("---")
    st.subheader("📷 Visual Import")
    
    uploaded_file = st.file_uploader("Upload schedule image", type=["png", "jpg", "jpeg", "webp"])
    user_hint = st.text_input("Context (Optional)", placeholder="e.g., 'Weekly starting Monday'")
    
    if uploaded_file is not None:
        if st.button("Process Image"):
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
                            st.session_state.messages.append({"role": "assistant", "content": f"📸 Processed image. Added: **{', '.join(added_titles)}**."})
                        except Exception as e:
                            print(f"Sync Error: {e}")
                    
                    st.rerun()
                else:
                    st.warning("No events found in the image.")

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