# AI Agent Tools

This document outlines the function-calling tools available to the AgendAI Agent. These tools allow the LLM to interact with the database, the calendar, and the extracted documents.

## 1. Calendar Operations (`calendar_ops.py`)

### `add_event`
**Purpose:** Adds a new event to the user's calendar.  
**Parameters:**
- `title` (str): The name of the event.
- `start` (str): Start time in ISO format (`YYYY-MM-DDTHH:MM:SS`).
- `end` (str): End time in ISO format.
- `allDay` (bool): `true` if the event lasts all day, `false` otherwise.
- `recurrence` (str, optional): RRULE string (e.g., `weekly`, `daily`).
- `recurrence_end` (str, optional): Date when recurrence stops (`YYYY-MM-DD`).
- `color` (str, optional): Hex color code for the event (e.g., `#3788d8`).
**Returns:**
- `str`: Success message ("Success: Event added at ID 5") or error message.

### `list_events_json`
**Purpose:** Retrieves a list of events for the current user, useful for checking the schedule or finding an ID to delete.
**Parameters:**
- `start_date` (str, optional): Filter start date (`YYYY-MM-DD`).
- `end_date` (str, optional): Filter end date.
**Returns:**
- `str (JSON)`: A JSON string containing a list of event objects (ID, title, start, end).

### `delete_event`
**Purpose:** Removes an event from the calendar by its unique ID.
**Parameters:**
- `event_id` (int): The unique ID of the event to delete.
**Returns:**
- `str`: Success message ("Event 102 deleted") or error ("Event not found").

### `check_availability`
**Purpose:** Checks if a specific time slot is free.
**Parameters:**
- `start_time` (str): ISO start time.
- `end_time` (str): ISO end time.
**Returns:**
- `str`: "Available" or a message listing the conflicting event (e.g., "Conflict with 'Lunch'").

### `get_conflicts_report`
**Purpose:** Runs a full audit of the user's schedule to find any overlapping events.
**Parameters:**
- None (Uses current user context).
**Returns:**
- `str`: A human-readable report listing all conflicts found (e.g., "Conflict detected: 'Meeting' overlaps with 'Gym' on 2023-10-15").

---

## 2. Vision & Extraction (`document_extraction.py`)

### `extract_events_from_image`
**Purpose:** Uses Gemini 2.0 Flash (Multimodal) to analyze an image of a schedule and extract structured event data.
**Parameters:**
- `image` (PIL.Image): The uploaded image file.
- `user_hint` (str): Detailed context (e.g., "This schedule starts next Monday").
**Returns:**
- `list[dict]`: A list of event dictionaries ready to be passed to `add_event`.
  ```json
  [
    {"title": "Math 101", "start": "...", "category": "Work_School"}
  ]
  ```

---

## 3. Database Operations (`database_ops.py`)

### `create_user`
**Purpose:** Registers a new user in the system.
**Parameters:**
- `username` (str): Unique username.
- `password` (str): Raw password (hashed internally before storage).
- `email` (str): User email.
**Returns:**
- `bool`: `True` if successful, `False` if username already exists.

### `verify_user`
**Purpose:** Authenticates a user login attempt.
**Parameters:**
- `username` (str)
- `password` (str)
**Returns:**
- `tuple`: `(bool, user_id)` — Success status and the User ID (if successful).
