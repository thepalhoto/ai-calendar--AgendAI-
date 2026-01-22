import sqlite3
import json
from tools.database_ops import get_db_connection

def add_event(title: str, start: str, end: str, allDay: bool, recurrence: str = None, color: str = "#3788d8") -> str:
    """
    Adds a new event.
    - If allDay is True, start/end must be 'YYYY-MM-DD'.
    - If allDay is False, start/end must be 'YYYY-MM-DDTHH:MM:SS+HH:MM'.
    - recurrence: Can be 'daily', 'weekly', 'monthly', 'yearly', or None.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SQLite stores booleans as 0 or 1
        is_all_day = 1 if allDay else 0
        
        # UPDATED QUERY: Added 'recurrence' to columns and values
        cursor.execute(
            """INSERT INTO events 
               (title, start, end, allDay, recurrence, backgroundColor, borderColor, resourceId) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, start, end, is_all_day, recurrence, color, color, "a")
        )
        
        conn.commit()
        conn.close()
        
        # Useful feedback for the AI/User
        rec_msg = f" (Repeats: {recurrence})" if recurrence else ""
        return f"Success: Event '{title}' added.{rec_msg} (Start: {start})"
    except Exception as e:
        return f"Error adding event: {str(e)}"

def list_events_json() -> str:
    """
    Returns ALL events in the exact JSON format required by the frontend calendar.
    This tool is used by the UI to populate the calendar.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            event_dict = {
                "id": row["id"],
                "title": row["title"],
                "start": row["start"],
                "end": row["end"],
                "allDay": bool(row["allDay"]),  # Convert 1/0 back to True/False
                "backgroundColor": row["backgroundColor"],
                "borderColor": row["borderColor"],
                "resourceId": row["resourceId"]
            }
            
            # Check if this event has a recurrence rule saved
            if row["recurrence"]:
                # The frontend calendar needs an 'rrule' object to show repeating events
                event_dict["rrule"] = {
                    "freq": row["recurrence"].lower(),  # e.g., 'weekly', 'daily'
                    "dtstart": row["start"]             # Recurrence needs to know when to start counting
                }
            
            events.append(event_dict)
            
        # Return as a JSON string
        return json.dumps(events)
    except Exception as e:
        print(f"Error listing events: {e}") # Helpful for debugging
        return "[]"

def delete_event(event_id: int) -> str:
    """
    Deletes an event by its ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT title FROM events WHERE id = ?", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            conn.close()
            return f"Error: Event ID {event_id} not found."
            
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()
        return f"Success: Event '{event['title']}' deleted."
    except Exception as e:
        return f"Error deleting event: {str(e)}"

def check_availability(check_datetime: str) -> str:
    """
    Simple check to see if any non-allDay event starts exactly at this time.
    Note: Complex overlapping checks are harder with mixed formats, 
    so for MVP we check exact start time matches.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if any event has this exact start time
        cursor.execute("SELECT title FROM events WHERE start = ?", (check_datetime,))
        event = cursor.fetchone()
        conn.close()
        
        if event:
            return f"Busy: There is an event '{event['title']}' starting at {check_datetime}."
        else:
            return "Free: No event starts exactly at this time."
    except Exception as e:
        return f"Error checking availability: {str(e)}"