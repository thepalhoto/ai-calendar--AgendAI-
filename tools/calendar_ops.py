### calendar_ops.py 23/01 23:40

import sqlite3
import json
from tools.database_ops import get_db_connection
from datetime import datetime

def add_event(title: str, start: str, end: str, allDay: bool, recurrence: str = None, recurrence_end: str = None, color: str = "#3788d8") -> str:
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
        
        cursor.execute(
        """INSERT INTO events 
           (title, start, end, allDay, recurrence, recurrence_end, backgroundColor, borderColor, resourceId) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, start, end, is_all_day, recurrence, recurrence_end, color, color, "a")
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
            
            # --- FIX START: HANDLE RECURRENCE DURATION ---
            if row["recurrence"]:
                # 1. Build the Recurrence Rule
                rule = {
                    "freq": row["recurrence"].lower(),
                    "dtstart": row["start"] # Essential for the rule to know where to begin
                }
                
                if "recurrence_end" in row.keys() and row["recurrence_end"]:
                    rule["until"] = row["recurrence_end"]

                event_dict["rrule"] = rule
                
                # 2. CALCULATE DURATION
                # FullCalendar ignores "end" for recurring events and needs "duration" (HH:mm)
                try:
                    # Parse strings to datetime objects
                    # Handle both ISO format (with T) and simple date format
                    if "T" in row["start"]:
                        s = datetime.fromisoformat(row["start"])
                        e = datetime.fromisoformat(row["end"])
                    else:
                        s = datetime.strptime(row["start"], "%Y-%m-%d")
                        e = datetime.strptime(row["end"], "%Y-%m-%d")
                    
                    # Calculate difference
                    delta = e - s
                    
                    # Convert to HH:mm format (e.g., 1.5 hours -> "01:30")
                    total_seconds = int(delta.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    
                    event_dict["duration"] = f"{hours:02}:{minutes:02}"
                    
                except Exception as e:
                    print(f"Error calculating duration for {row['title']}: {e}")
            # --- FIX END ---
            
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

def get_conflicts_report() -> str:
    """
    Analyzes the database for overlapping events.
    Smartly groups recurring conflicts so they aren't listed 50 times.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()
        conn.close()

        events = [dict(row) for row in rows]
        conflicts = []
        
        # --- FIX: Helper to parse time strings AND REMOVE TIMEZONES ---
        def parse_dt(dt_str):
            if "T" in dt_str:
                # Handle ISO format
                dt = datetime.fromisoformat(dt_str)
                # FORCE NAIVE: Remove timezone info so we can compare with everything else
                return dt.replace(tzinfo=None)
            
            # Handle plain dates (always naive)
            return datetime.strptime(dt_str, "%Y-%m-%d")

        # Compare every event against every other event (distinct pairs)
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                e1 = events[i]
                e2 = events[j]
                
                # --- CHECK 1: TWO RECURRING SERIES (The "Smart" Check) ---
                if e1['recurrence'] == 'weekly' and e2['recurrence'] == 'weekly':
                    # Do they start on the same weekday?
                    d1 = parse_dt(e1['start'])
                    d2 = parse_dt(e2['start'])
                    
                    if d1.weekday() == d2.weekday():
                        # Do times overlap?
                        # Normalize to arbitrary date to compare times only
                        t1_start = d1.time()
                        t1_end = parse_dt(e1['end']).time()
                        t2_start = d2.time()
                        t2_end = parse_dt(e2['end']).time()
                        
                        if t1_start < t2_end and t1_end > t2_start:
                             conflicts.append(f"⚠️ **Recurring Conflict:** '{e1['title']}' overlaps with '{e2['title']}' every {d1.strftime('%A')}.")
                             continue # Found a conflict, move to next pair

                # --- CHECK 2: TWO SINGLE EVENTS ---
                if not e1['recurrence'] and not e2['recurrence']:
                    start1, end1 = parse_dt(e1['start']), parse_dt(e1['end'])
                    start2, end2 = parse_dt(e2['start']), parse_dt(e2['end'])
                    
                    if start1 < end2 and end1 > start2:
                        conflicts.append(f"❌ **Date Conflict:** '{e1['title']}' clashes with '{e2['title']}' on {start1.strftime('%Y-%m-%d')}.")

        if not conflicts:
            return "✅ No conflicts found."
        
        return "\n\n".join(conflicts)

    except Exception as e:
        return f"Error calculating conflicts: {str(e)}"