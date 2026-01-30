"""
Admin script to create new users.
Run this from command line: python -m utils.create_user
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.database_ops import create_user, init_db

def main():
    # Initialize DB first
    init_db()
    
    print("=== AgendAI User Creation ===")
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    email = input("Enter email: ").strip()
    
    if not username or not password or not email:
        print("❌ All fields are required!")
        return
    
    success, message = create_user(username, password, email)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

if __name__ == "__main__":
    main()