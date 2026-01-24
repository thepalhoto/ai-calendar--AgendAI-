# config/constants.py

# Centralized color palette
# Keys are optimized for AI classification (No special characters)
EVENT_CATEGORIES = {
    "Work_School": "#0a9905",       # Green
    "Health": "#0080FF",            # Light Blue
    "Exams_Deadlines": "#FF0000",   # Red
    "Extracurricular": "#e3e627",   # Yellow
    "Meetings": "#03399e",          # Dark Blue
    "Birthdays": "#5a0070",         # Purple
    "Other": "#999999"              # Grey
}

def get_color_rules_text():
    """
    Helper for the Chat Agent to know the rules too.
    """
    rules = "### COLOR RULES:\n"
    for cat, hex_code in EVENT_CATEGORIES.items():
        rules += f"- **{cat}:** {hex_code}\n"
    return rules