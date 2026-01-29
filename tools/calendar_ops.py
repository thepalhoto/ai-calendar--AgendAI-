import sqlite3
import json
from tools.database_ops import get_db_connection
from datetime import datetime

# --- LANGFUSE SETUP (Optional, with fallback) ---
try:
    from langfuse import observe
except ImportError:
    def observe(**kwargs):
        def decorator(func):
            return func
        return decorator

# --- SHARED HELPER: DATE PARSING ---

def parse_dt(dt_str: str) -> datetime:
    """
    Parses a date string into a datetime object.
    Handles both ISO format (with 'T') and simple 'YYYY-MM-DD'.
    Returns a timezone-naive datetime for consistent comparison/calculation.
    """
    try:
        if "T" in dt_str:
            dt = datetime.fromisoformat(dt_str)
            return dt.replace(tzinfo=None)
        else:
            return datetime.strptime(dt_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"Warning: Could not parse date '{dt_str}': {e}")
        return datetime.now() 

# --- INTERNAL DATABASE FUNCTION (NO OBSERVABILITY) ---

def _fetch_events_from_db() -> str:
    """
    Internal function to fetch events from database.
    Called by both list_events_json (with observability) and UI (without).
    No @observe decorator - raw database access only.
    
    Returns:
        str: JSON string of events
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
                "allDay": bool(row["allDay"]), 
                "backgroundColor": row["backgroundColor"],
                "borderColor": row["borderColor"],
                "resourceId": row["resourceId"]
            }
            
            # --- HANDLE RECURRENCE DURATION ---
            if row["recurrence"] and row["recurrence"].lower() != "none":
                rule = {
                    "freq": row["recurrence"].lower(),
                    "dtstart": row["start"] 
                }
                
                if "recurrence_end" in row.keys() and row["recurrence_end"] and row["recurrence_end"] != "None":
                    rule["until"] = row["recurrence_end"]

                event_dict["rrule"] = rule
                
                # 2. CALCULATE DURATION
                try:
                    s = parse_dt(row["start"])
                    e = parse_dt(row["end"])
                    
                    delta = e - s
                    total_seconds = int(delta.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    
                    event_dict["duration"] = f"{hours:02}:{minutes:02}"
                    
                except Exception as e:
                    print(f"Error calculating duration for {row['title']}: {e}")
            
            events.append(event_dict)
            
        return json.dumps(events)
    except Exception as e:
        print(f"Error fetching events: {e}") 
        return "[]"

# --- CORE FUNCTIONS ---

@observe(as_type="tool")
def add_event(title: str, start: str, end: str, allDay: bool, recurrence: str = None, recurrence_end: str = None, color: str = "#3788d8") -> str:
    """
    Adds a new event.
    Forces dates to be 'Naive' (Floating) to prevent DST shifts.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        def make_naive_iso(dt_str):
            if "T" in dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
            
            dt_naive = dt.replace(tzinfo=None)
            
            if "T" in dt_str:
                return dt_naive.isoformat()
            return dt_naive.strftime("%Y-%m-%d")

        clean_start = make_naive_iso(start)
        clean_end = make_naive_iso(end)

        cursor.execute(
            "SELECT id FROM events WHERE title = ? AND start = ?", 
            (title, clean_start)
        )
        if cursor.fetchone():
            conn.close()
            return f"Skipped: Event '{title}' already exists at {clean_start}."

        is_all_day = 1 if allDay else 0
        
        cursor.execute(
        """INSERT INTO events 
           (title, start, end, allDay, recurrence, recurrence_end, backgroundColor, borderColor, resourceId) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, clean_start, clean_end, is_all_day, recurrence, recurrence_end, color, color, "a")
    )
        
        conn.commit()
        conn.close()
        
        rec_msg = f" (Repeats: {recurrence})" if recurrence else ""
        return f"Success: Event '{title}' added.{rec_msg} (Start: {clean_start})"
    except Exception as e:
        return f"Error adding event: {str(e)}"

@observe(as_type="tool")
def list_events_json() -> str:
    """
    Fetches ALL events from the database and formats them into the specific JSON structure 
    required by the frontend calendar widget.

    This is the AGENT-FACING function. It calls the internal _fetch_events_from_db() 
    and is decorated with @observe so Agent calls are tracked in Langfuse.

    ---------------------------------------------------------------------------
    CRITICAL EFFICIENCY RULES (DO NOT CALL UNLESS NECESSARY)
    ---------------------------------------------------------------------------
    You should NOT call this tool for every single user message. Only use it when
    you strictly need to 'read' the schedule to answer a question or perform an ID lookup.

    WHEN TO CALL THIS TOOL:
      1. User asks "What am I doing today?", "Show my schedule", or "Do I have free time?".
      2. User asks to "Delete [Event Name]" -> You MUST call this to find the Event ID first.
      3. User asks "Do I have any conflicts?" -> You need the list to check.
      4. User asks for a summary of past/future events.

    WHEN TO SKIP THIS TOOL (SAVE RESOURCES):
      1. User says "Add a meeting at 2pm" -> Just call `add_event` directly. Do NOT check availability first unless asked.
      2. User says "Hello" or "Who are you?" -> No database access needed.
      3. User provides a SYSTEM UPDATE (Visual Import) -> The events are already added.

    ---------------------------------------------------------------------------
    
    Returns:
        str: A JSON string representing a list of event objects (via _fetch_events_from_db).
    """
    return _fetch_events_from_db()

@observe(as_type="tool")
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

@observe(as_type="tool")
def check_availability(check_datetime: str) -> str:
    """
    Simple check to see if any non-allDay event starts exactly at this time.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM events WHERE start = ?", (check_datetime,))
        event = cursor.fetchone()
        conn.close()
        
        if event:
            return f"Busy: There is an event '{event['title']}' starting at {check_datetime}."
        else:
            return "Free: No event starts exactly at this time."
    except Exception as e:
        return f"Error checking availability: {str(e)}"

@observe(as_type="tool")
def get_conflicts_report() -> str:
    """
    Analyzes the database for overlapping events.
    Handles 'Split Series' by checking if recurrence ranges actually overlap.
    Calls _fetch_events_from_db internally for fresh data.
    """
    try:
        # Get fresh data without additional observability noise
        events_json = _fetch_events_from_db()
        events = json.loads(events_json)
        
        conflicts = []
        
        def time_ranges_overlap(e1, e2):
            if e1['allDay'] or e2['allDay']:
                return True
            
            start1 = parse_dt(e1['start']).time()
            end1 = parse_dt(e1['end']).time()
            start2 = parse_dt(e2['start']).time()
            end2 = parse_dt(e2['end']).time()
            
            return start1 < end2 and end1 > start2

        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                e1 = events[i]
                e2 = events[j]
                
                if not time_ranges_overlap(e1, e2):
                    continue

                d1 = parse_dt(e1['start'])
                d2 = parse_dt(e2['start'])

                # --- CASE 1: TWO RECURRING SERIES ---
                if e1['recurrence'] == 'weekly' and e2['recurrence'] == 'weekly':
                    if d1.weekday() == d2.weekday():
                        s1_date = d1.date()
                        s2_date = d2.date()
                        
                        e1_end_date = parse_dt(e1['recurrence_end']).date() if e1.get('recurrence_end') else datetime.max.date()
                        e2_end_date = parse_dt(e2['recurrence_end']).date() if e2.get('recurrence_end') else datetime.max.date()
                        
                        if s1_date <= e2_end_date and e1_end_date >= s2_date:
                             conflicts.append(f"⚠️ **Recurring Conflict:** '{e1['title']}' and '{e2['title']}' both repeat on {d1.strftime('%A')}s.")

                # --- CASE 2: TWO SINGLE EVENTS ---
                elif not e1['recurrence'] and not e2['recurrence']:
                    if d1.date() == d2.date():
                        conflicts.append(f"❌ **Date Conflict:** '{e1['title']}' overlaps with '{e2['title']}' on {d1.strftime('%Y-%m-%d')}.")

                # --- CASE 3: MIXED (One Single, One Recurring) ---
                else:
                    single = e1 if not e1['recurrence'] else e2
                    recurring = e1 if e1['recurrence'] else e2
                    
                    s_date = parse_dt(single['start']).date()
                    r_start_date = parse_dt(recurring['start']).date()
                    
                    if s_date.weekday() == r_start_date.weekday():
                        if s_date >= r_start_date:
                            has_end = recurring['recurrence_end']
                            if not has_end or s_date <= parse_dt(has_end).date():
                                conflicts.append(f"⚠️ **Instance Conflict:** '{single['title']}' ({s_date}) overlaps with recurring '{recurring['title']}'.")

        if not conflicts:
            return "✅ No conflicts found."
        
        return "\n\n".join(conflicts)

    except Exception as e:
        return f"Error calculating conflicts: {str(e)}"