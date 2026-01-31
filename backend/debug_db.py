
import sqlite3
import database
from passlib.context import CryptContext

try:
    conn = database.get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    print(f"Found {len(users)} users.")
    for user in users:
        print(f"User: {user['username']}, Role: {user['role']}")
        print(f"Hash: {user['password_hash']}")
        print(f"Hash Length: {len(user['password_hash'])}")
        
        # Try verifying
        try:
             res = database.verify_password("admin123", user['password_hash'])
             print(f"Verify 'admin123': {res}")
        except Exception as e:
             print(f"Verify Error: {e}")
             
    conn.close()
except Exception as e:
    print(f"Script Error: {e}")
