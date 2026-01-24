import sqlite3
import json
from tools.database_ops import get_db_connection
from datetime import datetime

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
            return dt.replace(tzinfo=None) # Force naive for consistency
        else:
            return datetime.strptime(dt_str, "%Y-%m-%d")
    except ValueError as e:
        # Fallback for unexpected formats, prevents crash
        print(f"Warning: Could not parse date '{dt_str}': {e}")
        return datetime.now() 

# --- CORE FUNCTIONS ---

def add_event(title: str, start: str, end: str, allDay: bool, recurrence: str = None, recurrence_end: str = None, color: str = "#3788d8") -> str:
    """
    Adds a new event.
    - If allDay is True, start/end must be 'YYYY-MM-DD'.
    - If allDay is False, start/end must be 'YYYY-MM-DDTHH:MM:SS'.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. IDEMPOTENCY CHECK (OPTIONAL BUT RECOMMENDED)
        # Check if an exact duplicate exists to prevent "double click" imports
        cursor.execute(
            "SELECT id FROM events WHERE title = ? AND start = ?", 
            (title, start)
        )
        if cursor.fetchone():
            conn.close()
            return f"Skipped: Event '{title}' already exists at {start}."

        # 2. INSERT
        is_all_day = 1 if allDay else 0
        
        cursor.execute(
        """INSERT INTO events 
           (title, start, end, allDay, recurrence, recurrence_end, backgroundColor, borderColor, resourceId) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, start, end, is_all_day, recurrence, recurrence_end, color, color, "a")
    )
        
        conn.commit()
        conn.close()
        
        rec_msg = f" (Repeats: {recurrence})" if recurrence else ""
        return f"Success: Event '{title}' added.{rec_msg} (Start: {start})"
    except Exception as e:
        return f"Error adding event: {str(e)}"

def list_events_json() -> str:
    """
    Returns ALL events in the exact JSON format required by the frontend calendar.
    Includes 'duration' for recurring events to fix visual shortening.
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
            if row["recurrence"]:
                # 1. Build Rule
                rule = {
                    "freq": row["recurrence"].lower(),
                    "dtstart": row["start"] 
                }
                
                if "recurrence_end" in row.keys() and row["recurrence_end"]:
                    rule["until"] = row["recurrence_end"]

                event_dict["rrule"] = rule
                
                # 2. CALCULATE DURATION (Refactored)
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
        print(f"Error listing events: {e}") 
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

def get_conflicts_report() -> str:
    """
    Analyzes the database for overlapping events.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()
        conn.close()

        events = [dict(row) for row in rows]
        conflicts = []
        
        # --- HELPER: Check Time Overlap (Independent of Date) ---
        def time_ranges_overlap(e1, e2):
            if e1['allDay'] or e2['allDay']:
                return True
            
            # Refactored to use shared parse_dt
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

                # Refactored to use shared parse_dt
                d1 = parse_dt(e1['start'])
                d2 = parse_dt(e2['start'])

                # --- CASE 1: TWO RECURRING SERIES ---
                if e1['recurrence'] == 'weekly' and e2['recurrence'] == 'weekly':
                    if d1.weekday() == d2.weekday():
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