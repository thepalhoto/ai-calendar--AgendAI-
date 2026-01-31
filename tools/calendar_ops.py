import sqlite3
import json
from tools.database_ops import get_db_connection
from datetime import datetime, timedelta

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

def _fetch_events_from_db(user_id: int) -> str:
    """
    Internal function to fetch events from database.
    Includes fix for All-Day event rendering and duration calculation.
    """
    try:
        conn = get_db_connection()
        # Ensure row_factory is Row so we can access by column name
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM events WHERE user_id = ?", (user_id,))
            
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            # Basic data mapping
            is_all_day = bool(row["allDay"])
            start_str = row["start"]
            end_str = row["end"]

            # --- FIX: EXCLUSIVE END DATE FOR ALL-DAY EVENTS ---
            # If it's all-day, FullCalendar needs the 'end' to be the start of the NEXT day
            if is_all_day and end_str:
                try:
                    # Parse current end (e.g., "2026-02-01 23:59:59" or "2026-02-01")
                    # We only care about the date part for the shift
                    end_dt = parse_dt(end_str) 
                    # Add 1 day and set to midnight
                    actual_end = (end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    end_str = actual_end
                except Exception as e:
                    print(f"Error adjusting allDay end date: {e}")

            event_dict = {
                "id": row["id"],
                "title": row["title"],
                "start": start_str,
                "end": end_str,
                "allDay": is_all_day, 
                "backgroundColor": row["backgroundColor"],
                "borderColor": row["borderColor"],
                "resourceId": row["resourceId"],
                "recurrence": row["recurrence"],
                "recurrence_end": row["recurrence_end"]
            }
            
            # --- HANDLE RECURRENCE DURATION ---
            if row["recurrence"] and row["recurrence"].lower() != "none":
                # Map user-friendly strings to RRule constants
                freq_map = {
                    "daily": "daily",
                    "weekly": "weekly",
                    "monthly": "monthly",
                    "yearly": "yearly"
                }
                
                selected_freq = freq_map.get(row["recurrence"].lower(), "daily")

                # IMPORTANT: RRule often needs the start date without the "-" or ":" 
                # for some versions, but let's try the standardized dict first.
                rule = {
                    "freq": selected_freq,
                    "dtstart": row["start"] 
                }
                
                if "recurrence_end" in row.keys() and row["recurrence_end"] and str(row["recurrence_end"]) != "None":
                    rule["until"] = row["recurrence_end"]

                event_dict["rrule"] = rule
                
                # FullCalendar needs a 'duration' if using rrule, or it defaults to 0
                try:
                    s = parse_dt(row["start"])
                    e = parse_dt(row["end"])
                    
                    delta = e - s
                    # For all-day events, ensure duration is at least 24 hours
                    if is_all_day:
                        event_dict["duration"] = "24:00"
                    else:
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
def add_event(title: str, start: str, end: str, allDay: bool, user_id: int, 
              recurrence: str = None, recurrence_end: str = None, color: str = "#3788d8") -> str:
    """
    Adds a new event for a specific user.
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
            "SELECT id FROM events WHERE title = ? AND start = ? AND user_id = ?", 
            (title, clean_start, user_id)
        )
        if cursor.fetchone():
            conn.close()
            return f"Skipped: Event '{title}' already exists at {clean_start}."

        is_all_day = 1 if allDay else 0
        
        cursor.execute(
        """INSERT INTO events 
           (user_id, title, start, end, allDay, recurrence, recurrence_end, backgroundColor, borderColor, resourceId) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, title, clean_start, clean_end, is_all_day, recurrence, recurrence_end, color, color, "a")
        )
        
        conn.commit()
        conn.close()
        
        rec_msg = f" (Repeats: {recurrence})" if recurrence else ""
        return f"Success: Event '{title}' added.{rec_msg} (Start: {clean_start})"
    except Exception as e:
        return f"Error adding event: {str(e)}"

@observe(as_type="tool")
def list_events_json(user_id: int) -> str:
    """Fetches events ONLY for the specific user_id provided."""
    return _fetch_events_from_db(user_id)

@observe(as_type="tool")
def delete_event(event_id: int, user_id: int) -> str:
    """Deletes an event (only if it belongs to the user)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT title FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
        event = cursor.fetchone()
        
        if not event:
            conn.close()
            return f"Error: Event ID {event_id} not found or you don't have permission."
            
        cursor.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
        conn.commit()
        conn.close()
        return f"Success: Event '{event['title']}' deleted."
    except Exception as e:
        return f"Error deleting event: {str(e)}"

@observe(as_type="tool")
def check_availability(check_datetime: str, user_id: int) -> str:
    """Check availability for a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM events WHERE start = ? AND user_id = ?", (check_datetime, user_id))
        event = cursor.fetchone()
        conn.close()
        
        if event:
            return f"Busy: There is an event '{event['title']}' starting at {check_datetime}."
        else:
            return "Free: No event starts exactly at this time."
    except Exception as e:
        return f"Error checking availability: {str(e)}"

@observe(as_type="tool")
def get_conflicts_report(user_id: int) -> str:
    """Analyzes conflicts for a specific user"""
    try:
        events_json = _fetch_events_from_db(user_id)
        events = json.loads(events_json)
        if not events:
            return "✅ No conflicts found."

        conflicts = []
        conflict_pairs = set()

        def normalize_recurrence(value):
            if not value:
                return None
            lowered = str(value).lower().strip()
            return None if lowered in ("none", "null", "") else lowered

        def parse_date_only(value):
            if not value:
                return None
            lowered = str(value).lower().strip()
            if lowered in ("none", "null", ""):
                return None
            return parse_dt(value).date()

        def add_months(date_obj, months):
            year = date_obj.year + (date_obj.month - 1 + months) // 12
            month = (date_obj.month - 1 + months) % 12 + 1
            # Clamp day to last day of month
            from calendar import monthrange
            day = min(date_obj.day, monthrange(year, month)[1])
            return date_obj.replace(year=year, month=month, day=day)

        def iter_occurrences(event, horizon_end):
            start_dt = parse_dt(event["start"])
            end_dt = parse_dt(event["end"])
            duration = end_dt - start_dt

            if event.get("allDay"):
                start_dt = start_dt.replace(hour=0, minute=0, second=0)
                duration = timedelta(hours=23, minutes=59, seconds=59)

            rec = normalize_recurrence(event.get("recurrence"))
            rec_end = parse_date_only(event.get("recurrence_end")) or horizon_end.date()

            current_date = start_dt.date()
            last_date = min(rec_end, horizon_end.date())

            if not rec:
                yield (start_dt, start_dt + duration)
                return

            while current_date <= last_date:
                occ_start = datetime.combine(current_date, start_dt.time())
                occ_end = occ_start + duration
                yield (occ_start, occ_end)

                if rec == "daily":
                    current_date = current_date + timedelta(days=1)
                elif rec == "weekly":
                    current_date = current_date + timedelta(days=7)
                elif rec == "monthly":
                    current_date = add_months(current_date, 1)
                elif rec == "yearly":
                    current_date = add_months(current_date, 12)
                else:
                    # Unknown recurrence: treat as non-recurring
                    break

        def overlaps(a_start, a_end, b_start, b_end):
            return a_start < b_end and a_end > b_start

        # Determine horizon end to prevent infinite expansion
        max_start = max(parse_dt(e["start"]) for e in events)
        max_rec_end = None
        for e in events:
            rec_end = parse_date_only(e.get("recurrence_end"))
            if rec_end:
                rec_end_dt = datetime.combine(rec_end, datetime.max.time())
                max_rec_end = max(rec_end_dt, max_rec_end) if max_rec_end else rec_end_dt
        horizon_end = max_rec_end if max_rec_end else (max_start + timedelta(days=30))
        horizon_end = max(horizon_end, max_start + timedelta(days=30))

        # Build occurrences list
        occurrences = []
        for event in events:
            for occ_start, occ_end in iter_occurrences(event, horizon_end):
                occurrences.append({
                    "event_id": event["id"],
                    "title": event["title"],
                    "start": occ_start,
                    "end": occ_end,
                })

        # Sweep line to detect overlaps efficiently
        occurrences.sort(key=lambda x: x["start"])
        active = []

        for occ in occurrences:
            active = [a for a in active if a["end"] > occ["start"]]
            for a in active:
                if overlaps(a["start"], a["end"], occ["start"], occ["end"]):
                    pair = tuple(sorted((a["event_id"], occ["event_id"])))


                    if pair not in conflict_pairs:
                        conflict_pairs.add(pair)
                        conflicts.append(
                            f"⚠️ **Conflict:** '{a['title']}' overlaps with '{occ['title']}' (e.g., {occ['start'].strftime('%Y-%m-%d %H:%M')})."
                        )
            active.append(occ)

        if not conflicts:
            return "✅ No conflicts found."

        return "\n\n".join(conflicts)

    except Exception as e:
        return f"Error calculating conflicts: {str(e)}"
