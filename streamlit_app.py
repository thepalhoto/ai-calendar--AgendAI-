import streamlit as st
from streamlit_calendar import calendar
import json
import datetime

# Import your Agent and Database tools
from src.agent import get_agent
from tools.calendar_ops import list_events_json

# --- PAGE SETUP ---
st.set_page_config(page_title="AgendAI", layout="wide")

st.title("📅 AgendAI: Your Smart Schedule Assistant")

# --- INITIALIZE SESSION STATE ---
# This keeps the chat history alive when the page refreshes
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize the Agent ONCE per session
if "agent" not in st.session_state:
    try:
        st.session_state.agent = get_agent()
        # Add a welcome message
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm AgendAI. How can I help you manage your schedule today?"})
    except Exception as e:
        st.error(f"Error initializing AI: {e}")

# --- LEFT COLUMN: CHAT INTERFACE ---
col1, col2 = st.columns([1, 2]) # 1/3 width for chat, 2/3 for calendar

with col1:
    st.subheader("💬 Chat")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Add a meeting, check schedule..."):
        # 1. Display User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Get AI Response
        with st.chat_message("assistant"):
            try:
                # We use the agent stored in session state
                response = st.session_state.agent.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
                # Force a rerun so the calendar updates immediately if the AI changed anything
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- RIGHT COLUMN: VISUAL CALENDAR ---
with col2:
    st.subheader("🗓️ Calendar View")
    
    # 1. Fetch the latest events from the DB
    events_json_str = list_events_json()
    events_list = json.loads(events_json_str)
    
    # 2. Configure the Calendar Visuals
    calendar_options = {
        "editable": False, # Read-only view (updates via Chat only)
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "initialView": "dayGridMonth",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "22:00:00",
    }
    
    # 3. Render the Calendar
    # The 'key' ensures it redraws correctly when events change
    calendar(events=events_list, options=calendar_options, key=str(len(st.session_state.messages)))