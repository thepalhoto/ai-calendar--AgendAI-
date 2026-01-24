import sqlite3
import os

# 1. Search for the DB in common locations
base_dir = os.path.dirname(os.path.abspath(__file__))
paths_to_check = [
    os.path.join(base_dir, 'scheduler.db'),         # Root
    os.path.join(base_dir, 'data', 'scheduler.db')  # Data folder
]

db_path = None
for path in paths_to_check:
    if os.path.exists(path):
        db_path = path
        break

print(f"--- DATABASE DIAGNOSTIC ---")

if not db_path:
    print("❌ ERROR: Database file NOT found in root or 'data/' folder.")
    print("   -> The app will likely create a new empty one if you run it.")
else:
    print(f"✅ Found Database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check Columns
        cursor.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📊 Columns: {columns}")
        
        if 'resourceId' not in columns:
            print("⚠️ WARNING: 'resourceId' column is MISSING! Re-creating table...")
            # Auto-fix Schema
            cursor.execute("ALTER TABLE events ADD COLUMN resourceId TEXT DEFAULT 'a'")
            conn.commit()
            print("✅ 'resourceId' column added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error reading DB: {e}")