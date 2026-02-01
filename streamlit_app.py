import streamlit as st
from streamlit_calendar import calendar
import os
import sys

# --- 1. PATH SETUP FIRST ---
# Get the absolute path to the directory where streamlit_app.py lives
root_dir = os.path.dirname(os.path.abspath(__file__))

# Define all key directories
config_dir = os.path.join(root_dir, 'config')
services_dir = os.path.join(root_dir, 'services')
tools_dir = os.path.join(root_dir, 'tools')

# Add them to sys.path
for d in [root_dir, config_dir, services_dir, tools_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

# --- 2. CUSTOM IMPORTS SECOND ---
# Now that Python knows where 'services' and 'tools' are, we can import them
from services.calendar_service import CalendarService
from src.agent import get_agent

# Langfuse observability
try:
    from langfuse import observe
    langfuse_available = True
except ImportError:
    # Fallback: no-op decorator if langfuse unavailable
    def observe(name):
        def decorator(func):
            return func
        return decorator
    langfuse_available = False

# Robust Import: Try package import first, fallback to direct
# UPDATED: Now imports VISION_MODEL_NAME from constants
try:
    from config.constants import EVENT_CATEGORIES, VISION_MODEL_NAME 
    from config.prompts import get_vision_prompt
except ImportError:
    try:
        from config.constants import EVENT_CATEGORIES, VISION_MODEL_NAME
        from config.prompts import get_vision_prompt
    except ImportError:
        # Fallback if config is totally missing (prevents crash)
        EVENT_CATEGORIES = {"Other": "#999999"}
        VISION_MODEL_NAME = "gemini-2.0-flash" # Fallback default
        st.error("⚠️ Could not load config. Defaulting to Grey & Default Vision Model.")

# --- AUTHENTICATION ---
# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False

# Login/Signup Form (shown if not authenticated)
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>📅 AgendAI</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Toggle between Login and Signup
        tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                st.subheader("Login to your calendar")
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if username and password:
                        authenticated, user_id = CalendarService.authenticate(username, password)
                        if authenticated:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user_id
                            st.session_state.username = username
                            st.success(f"Welcome back, {username}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
                    else:
                        st.warning("Please enter both username and password")
        
        with tab2:
            with st.form("signup_form"):
                st.subheader("Create a new account")
                new_username = st.text_input("Username", key="signup_username", 
                                            help="Choose a unique username")
                new_email = st.text_input("Email", key="signup_email",
                                         help="Enter a valid email address")
                new_password = st.text_input("Password", type="password", key="signup_password",
                                            help="Choose a strong password")
                confirm_password = st.text_input("Confirm Password", type="password", 
                                                key="signup_confirm",
                                                help="Re-enter your password")
                signup_submit = st.form_submit_button("Create Account", use_container_width=True)
                
                if signup_submit:
                    # Validation
                    if not new_username or not new_email or not new_password:
                        st.error("❌ All fields are required")
                    elif len(new_username) < 3:
                        st.error("❌ Username must be at least 3 characters")
                    elif len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords don't match")
                    elif '@' not in new_email or '.' not in new_email:
                        st.error("❌ Please enter a valid email address")
                    else:
                        # Try to create user
                        success, message = CalendarService.register_user(new_username, new_password, new_email)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("👉 Please go to the Login tab to sign in")
                        else:
                            st.error(f"❌ {message}")
    
    st.stop()  # Don't show rest of app until logged in

# --- PAGE SETUP ---
st.set_page_config(page_title="AgendAI", layout="wide")

st.markdown(
    "<h1 style='text-align: center;'>📅 AgendAI: Your Smart Schedule Assistant</h1>", 
    unsafe_allow_html=True
)


# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.session_state.authenticated and "agent" not in st.session_state:
    try:
        # Pass the user_id to the agent so it can use it for tools
        st.session_state.agent = get_agent(st.session_state.user_id, st.session_state.username)
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"Hello {st.session_state.username}! I'm AgendAI. How can I help you manage your schedule today?"
        })
    except Exception as e:
        st.error(f"Error initializing AI: {e}")

# --- SIDEBAR SETUP ---
with st.sidebar:
    # User info and logout at the top
    st.markdown(f"👤 **{st.session_state.username}**")
    if st.button("🚪 Logout"):
        # 1. Wipe the entire temporary whiteboard
        st.session_state.clear() 
        # 2. Force the app to restart from the beginning (login screen)
        st.rerun()
    
    st.markdown("---")
    
# 1. VISUAL IMPORT
    st.header("📷 Visual Import")
    
    uploaded_file = st.file_uploader("Upload schedule image", type=["png", "jpg", "jpeg", "webp"])
    user_hint = st.text_input("Context (Optional)", placeholder="e.g., 'Weekly starting Monday'")
    
    if uploaded_file is not None:
        if st.button("Process Image", type="primary"): 
            with st.spinner("Analyzing the document..."):
                try:
                    # 1. Convert Streamlit object to raw bytes/PIL Image HERE
                    # This keeps the backend "Streamlit-free"
                    from PIL import Image
                    img = Image.open(uploaded_file)
    
                    # 2. Call the service. The service now returns a single status message.
                    # We pass the agent so the service can update it internally.
                    success_msg = CalendarService.process_visual_import_workflow(
                        image=img,
                        user_id=st.session_state.user_id,
                        agent=st.session_state.agent,
                        hint=user_hint
                    )
                    
                    # 3. Handle UI feedback
                    st.success(success_msg)
                    st.session_state.messages.append({"role": "assistant", "content": success_msg})
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Vision Processing Error: {e}")

    st.markdown("---")

    # 2. AUDIT
    st.subheader("🛡️ Audit")
    
    if st.button("Check for Conflicts"):
        with st.spinner("Analyzing schedule logic..."):
            try:
                report = CalendarService.get_conflict_report(st.session_state.user_id)
                
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
                    
                    # Send message and get response
                    response = st.session_state.agent.send_message(prompt)
                    
                    # Handle response
                    if response is None:
                        response_text = "I received no response. Please check the logs."
                        st.error("Response was None - Check agent logs")
                    elif hasattr(response, 'text'):
                        response_text = response.text
                        if response_text is None:
                            response_text = "I couldn't generate a response text. Tool may have been called."
                    else:
                        response_text = str(response)
                    
                    response_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    import traceback
                    error_msg = f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                    st.error(error_msg)
                    print(error_msg)

# --- MAIN PAGE: CALENDAR ---
try:
    # Use the service to get a clean list of events (it handles the JSON parsing)
    events_list = CalendarService.get_ui_events(st.session_state.user_id)
    
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
    
    calendar(events=events_list, options=calendar_options, key="agenda_calendar")

except Exception as e:
    st.error(f"Error loading calendar: {e}")
    import traceback
    st.error(traceback.format_exc())