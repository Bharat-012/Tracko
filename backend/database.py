import sqlite3
from passlib.context import CryptContext

DATABASE_NAME = "bus_tracker.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Create Buses Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS buses (
            bus_id TEXT PRIMARY KEY,
            driver_name TEXT,
            route_stops TEXT,
            status TEXT
        )
    ''')
    
    # Seed Admin User if not exists
    cursor = c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        print("Seeding default admin user...")
        hashed_pw = pwd_context.hash("admin123")
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                  ("admin", hashed_pw, "admin"))

    # Seed Default Driver
    cursor = c.execute("SELECT * FROM users WHERE username = 'driver'")
    if not cursor.fetchone():
        print("Seeding default driver user...")
        hashed_pw = pwd_context.hash("driver123")
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                  ("driver", hashed_pw, "driver"))

    # Seed Default Student
    cursor = c.execute("SELECT * FROM users WHERE username = 'student'")
    if not cursor.fetchone():
        print("Seeding default student user...")
        hashed_pw = pwd_context.hash("student123")
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                  ("student", hashed_pw, "student"))

    # Seed Simulated Buses
    simulated_buses = [
        ("KA-01-FA-1234", "driver", "Rt 101: Malleshwaram -> College", "active"),
        ("KA-05-SI-5678", "driver", "Rt 202: Indiranagar -> College", "active")
    ]
    for bus_id, driver, route, status in simulated_buses:
        cursor = c.execute("SELECT * FROM buses WHERE bus_id = ?", (bus_id,))
        if not cursor.fetchone():
             print(f"Seeding simulated bus {bus_id}...")
             c.execute("INSERT INTO buses (bus_id, driver_name, route_stops, status) VALUES (?, ?, ?, ?)", 
                       (bus_id, driver, route, status))

    conn.commit()
    conn.close()

def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def get_users_by_role(role):
    conn = get_db_connection()
    users = conn.execute("SELECT username FROM users WHERE role = ?", (role,)).fetchall()
    conn.close()
    return [user["username"] for user in users]

def create_user(username, password, role):
    conn = get_db_connection()
    hashed_pw = pwd_context.hash(password)
    try:
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                     (username, hashed_pw, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def create_bus(bus_id, driver_name, route_stops):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO buses (bus_id, driver_name, route_stops, status) VALUES (?, ?, ?, ?)", 
                     (bus_id, driver_name, route_stops, "offline"))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_bus(bus_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM buses WHERE bus_id = ?", (bus_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting bus: {e}")
        return False
    finally:
        conn.close()

def get_all_buses():
    conn = get_db_connection()
    buses = conn.execute("SELECT * FROM buses").fetchall()
    conn.close()
    return [dict(bus) for bus in buses]

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
