import json
from PIL import Image
from langfuse import observe
from tools.calendar_ops import add_event, _fetch_events_from_db
from tools.document_extraction import extract_events_from_image

class CalendarService:
    
    @staticmethod
    @observe(name="Service: Visual Import")
    def process_and_save_visual_import(uploaded_file, user_id, categories, model_name, prompt_fn, hint=""):
        """
        Coordinates the extraction of events from an image and saves them to the DB.
        """
        # 1. Convert Streamlit file to PIL Image
        img = Image.open(uploaded_file)
        
        # 2. Call the extraction tool
        extracted_events = extract_events_from_image(
            image=img,
            event_categories=categories,
            vision_model_name=model_name,
            get_vision_prompt_fn=prompt_fn,
            user_hint=hint  
        )
        
        # 3. Save to Database
        added_titles = []
        for event in extracted_events:
            cat = event.get("category", "Other")
            color = categories.get(cat, categories.get("Other", "#999999"))
    
            add_event(
                user_id=user_id,
                allDay=0,                
                title=event.get("title"),
                start=event.get("start"),
                end=event.get("end"),
                recurrence=event.get("recurrence"),      
                recurrence_end=event.get("recurrence_end"), 
                backgroundColor=color,   
                borderColor=color      
            )
            added_titles.append(event.get("title"))
            
        return added_titles

    @staticmethod
    def get_ui_events(user_id):
        """Fetches and parses events for the UI."""
        raw_events_json = _fetch_events_from_db(user_id)
        return json.loads(raw_events_json)