import sqlite3
import os
import bcrypt
from typing import Tuple, Dict, Optional

### Create a local database file and set up tables for users and calendar events.


# Define path to database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scheduler.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name (row['title'])
    return conn

def init_db():
    """Initialize database with users and events tables"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create events table with user_id foreign key
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            allDay INTEGER NOT NULL,
            title TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            recurrence TEXT,
            recurrence_end TEXT,
            backgroundColor TEXT,
            borderColor TEXT,
            resourceId TEXT DEFAULT 'a',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

def migrate_add_user_id():
    """Migration: Add user_id column to existing events table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user_id column exists
    cursor.execute("PRAGMA table_info(events)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print("Migrating: Adding user_id column to events table...")
        cursor.execute("ALTER TABLE events ADD COLUMN user_id INTEGER")
        # Set all existing events to user_id = 1 (first user)
        cursor.execute("UPDATE events SET user_id = 1 WHERE user_id IS NULL")
        conn.commit()
        print("Migration complete!")
    
    conn.close()

# --- USER AUTHENTICATION FUNCTIONS ---

def create_user(username: str, password: str, email: str) -> Tuple[bool, str]:
    """
    Create a new user with hashed password.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        
        conn.commit()
        conn.close()
        return True, f"User '{username}' created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists"
        elif "email" in str(e):
            return False, "Email already exists"
        return False, str(e)
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def verify_user(username: str, password: str) -> Tuple[bool, Optional[int]]:
    """
    Verify user credentials.
    
    Returns:
        (authenticated: bool, user_id: int or None)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, password_hash FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return False, None
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return True, user['user_id']
        
        return False, None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False, None

def get_user_info(user_id: int) -> Optional[Dict]:
    """Get user information by user_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, username, email, created_at FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None

if __name__ == "__main__":
    init_db()
    migrate_add_user_id()