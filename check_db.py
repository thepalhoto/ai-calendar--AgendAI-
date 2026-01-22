import sqlite3
import os

# 1. Calculate absolute path to DB
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'data', 'scheduler.db')

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # <--- THIS WAS MISSING!
cursor = conn.cursor()

try:
    cursor.execute("SELECT * FROM events")
    rows = cursor.fetchall()

    print(f"--- Database Content ({len(rows)} events) ---")
    for row in rows:
        # Now this will work because 'row' behaves like a dict
        print(dict(row))
except Exception as e:
    print(f"Error: {e}")

conn.close()