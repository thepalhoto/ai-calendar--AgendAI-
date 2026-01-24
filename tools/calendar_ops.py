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
    Analyzes the database for ALL types of overlapping events:
    1. Single vs Single
    2. Recurring vs Recurring (Series overlap)
    3. Single vs Recurring (Specific instance overlap)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()
        conn.close()

        events = [dict(row) for row in rows]
        conflicts = []
        
        # --- HELPER: Parse Date & STRIP Timezone ---
        def parse_dt(dt_str):
            if "T" in dt_str:
                dt = datetime.fromisoformat(dt_str)
                return dt.replace(tzinfo=None) # Force naive for comparison
            return datetime.strptime(dt_str, "%Y-%m-%d")

        # --- HELPER: Check Time Overlap (Independent of Date) ---
        def time_ranges_overlap(e1, e2):
            # If either is All Day, they strictly overlap in time (covering the whole day)
            if e1['allDay'] or e2['allDay']:
                return True
            
            # Extract Time components
            start1 = parse_dt(e1['start']).time()
            end1 = parse_dt(e1['end']).time()
            start2 = parse_dt(e2['start']).time()
            end2 = parse_dt(e2['end']).time()
            
            # Standard overlap logic: (StartA < EndB) and (EndA > StartB)
            return start1 < end2 and end1 > start2

        # Compare every unique pair
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                e1 = events[i]
                e2 = events[j]
                
                # OPTIMIZATION: If times don't overlap, dates don't matter.
                # (Unless they are multi-day events, but we assume single-day for this scope)
                if not time_ranges_overlap(e1, e2):
                    continue

                # --- CASE 1: TWO RECURRING SERIES ---
                if e1['recurrence'] == 'weekly' and e2['recurrence'] == 'weekly':
                    d1 = parse_dt(e1['start'])
                    d2 = parse_dt(e2['start'])
                    # Conflict if they are on the SAME WEEKDAY (e.g. both Mondays)
                    if d1.weekday() == d2.weekday():
                         conflicts.append(f"⚠️ **Recurring Conflict:** '{e1['title']}' and '{e2['title']}' both repeat on {d1.strftime('%A')}s.")

                # --- CASE 2: TWO SINGLE EVENTS ---
                elif not e1['recurrence'] and not e2['recurrence']:
                    d1 = parse_dt(e1['start'])
                    d2 = parse_dt(e2['start'])
                    if d1.date() == d2.date():
                        conflicts.append(f"❌ **Date Conflict:** '{e1['title']}' overlaps with '{e2['title']}' on {d1.strftime('%Y-%m-%d')}.")

                # --- CASE 3: MIXED (One Single, One Recurring) ---
                # This catches: "Dentist" (Single) vs "Class" (Weekly)
                else:
                    # Identify which is which
                    single = e1 if not e1['recurrence'] else e2
                    recurring = e1 if e1['recurrence'] else e2
                    
                    s_date = parse_dt(single['start']).date()
                    r_start_date = parse_dt(recurring['start']).date()
                    
                    # 1. Does the single event fall on the correct WEEKDAY?
                    if s_date.weekday() == r_start_date.weekday():
                        # 2. Is the single event AFTER the series started?
                        if s_date >= r_start_date:
                            # 3. If series has an end date, is the single event BEFORE it?
                            has_end = recurring['recurrence_end']
                            if not has_end or s_date <= parse_dt(has_end).date():
                                conflicts.append(f"⚠️ **Instance Conflict:** '{single['title']}' ({s_date}) overlaps with recurring '{recurring['title']}'.")

        if not conflicts:
            return "✅ No conflicts found."
        
        return "\n\n".join(conflicts)

    except Exception as e:
        return f"Error calculating conflicts: {str(e)}"