import sqlite3
import os

### Create a local database file and set up a table to store calendar events in the exact format required by the frontend.


# Define path to database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scheduler.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name (row['title'])
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated schema to match your JSON structure
    ## The agent itself must ensure that the data types and formats are correct when inserting data.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allDay INTEGER NOT NULL,            -- 0 for False, 1 for True
            title TEXT NOT NULL,
            start TEXT NOT NULL,                -- YYYY-MM-DD or ISO8601 Timestamp
            end TEXT NOT NULL,                  -- YYYY-MM-DD or ISO8601 Timestamp
            recurrence TEXT,                -- NEW: 'daily', 'weekly', 'monthly', 'yearly', or NULL
            backgroundColor TEXT,
            borderColor TEXT,
            resourceId TEXT DEFAULT 'a'
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

if __name__ == "__main__":
    init_db()