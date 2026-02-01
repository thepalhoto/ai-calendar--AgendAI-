import json
from PIL import Image
from config.constants import EVENT_CATEGORIES, VISION_MODEL_NAME
from config.prompts import get_vision_prompt
from tools.document_extraction import extract_events_from_image 
from tools.calendar_ops import add_event, _fetch_events_from_db, get_conflicts_report
from tools.database_ops import verify_user, create_user

# Langfuse setup
try:
    from langfuse import observe
except ImportError:
    def observe(name=None):
        def decorator(func): return func
        return decorator

class CalendarService:
    
    @staticmethod
    def authenticate(username, password):
        return verify_user(username, password)

    @staticmethod
    def register_user(username, password, email):
        return create_user(username, password, email)

    @staticmethod
    def get_conflict_report(user_id):
        return get_conflicts_report(user_id)

    @staticmethod
    def get_ui_events(user_id):
        """Fetches events and ensures they are in a format Streamlit-Calendar likes."""
        events = _fetch_events_from_db(user_id)
        
        # If your tool returns a JSON string, decode it here ONCE.
        if isinstance(events, str):
            try:
                return json.loads(events)
            except json.JSONDecodeError:
                return []
        return events if events else []

    @observe(name="Service: Visual Import")
    @staticmethod # Only one is needed
    def process_visual_import_workflow(image, user_id, agent, hint):
        """Orchestrates extraction, DB saving, and Agent notification."""
        
        # 1. Extraction
        events = extract_events_from_image(
            image=image,
            event_categories=EVENT_CATEGORIES,
            vision_model_name=VISION_MODEL_NAME,
            get_vision_prompt_fn=get_vision_prompt,
            user_hint=hint
        )

        if not events:
            return "No events found in the image."

        # 2. Saving to DB
        added_titles = []
        for event in events:
            res = add_event(
                title=event['title'], 
                start=event['start'], 
                end=event['end'], 
                allDay=event.get('allDay', False),
                user_id=user_id,
                color=event.get('color', '#3788d8')
            )
            if "Success" in res:
                added_titles.append(event['title'])

        # 3. Agent Notification
        if added_titles:
            sync_text = f"SYSTEM UPDATE: User uploaded an image. I've automatically added these to the DB: {', '.join(added_titles)}."
            agent.send_message(sync_text)
            return f"✅ Imported {len(added_titles)} events: {', '.join(added_titles)}"
        
        return "Processed image, but couldn't save events to the database."