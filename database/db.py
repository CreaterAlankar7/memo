import sqlite3
from datetime import datetime
from config import DB_PATH
from werkzeug.security import generate_password_hash, check_password_hash

def connect_db():
    return sqlite3.connect(DB_PATH, timeout=10)

def init_db():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            image TEXT,
            theme TEXT DEFAULT light,
            phone TEXT,
            name TEXT    
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            image TEXT,
            theme TEXT DEFAULT light
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            person TEXT,
            date TEXT,
            time TEXT,
            note TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS login_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user INTEGER,
        role TEXT,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''') 
        conn.commit()

# User & Admin Registration/Authentication
def register_user(username, password, phone, name):
    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password, phone, name) VALUES (?, ?, ?, ?)",
                        (username, generate_password_hash(password), phone, name))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def validate_user(username, password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        if user and check_password_hash(user[1], password):
            return user[0]  # return user_id
    return None

def validate_admin(username, password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM admin WHERE username=?", (username,))
        admin = cur.fetchone()
        if admin and check_password_hash(admin[1], password):
            return admin[0]
    return None

# Event operations
def add_event(user_id, title,person, date, time, note):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO events (user_id, title,person, date, time, note) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, title, person, date, time, note))
        conn.commit()

def get_user_events(user_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM events WHERE user_id=? ORDER BY date DESC", (user_id,))
        return cur.fetchall()

def get_all_events():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT e.*, u.username FROM events e JOIN users u ON e.user_id = u.id ORDER BY date DESC")
        return cur.fetchall()

def delete_event(event_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()

def save_login(user, role):
    login_time = datetime.now().strftime('%A, %d %B %Y at %I:%M %p')
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO login_history (user, role, login_time) VALUES (?, ?, ?)", (user, role, login_time))
        conn.commit()

def get_login_history():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT lh.user,
                   CASE 
                       WHEN lh.role = 'admin' THEN a.username
                       ELSE u.username
                   END AS username,
                   lh.role,
                   lh.login_time
            FROM login_history lh
            LEFT JOIN admin a ON lh.role = 'admin' AND lh.user = a.id
            LEFT JOIN users u ON lh.role = 'user' AND lh.user = u.id
            ORDER BY lh.login_time DESC
        """)
        return cur.fetchall()
    
def get_event_by_id(event_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
        return cur.fetchone()

def update_event(event_id, title, person, date, time, note):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''UPDATE events
                       SET title=?, person=?, date=?, time=?, note=?
                       WHERE id=?''',
                    (title, person, date, time, note, event_id))
        conn.commit()

def search_user_events(user_id, keyword):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT * FROM events
                       WHERE user_id=? AND (title LIKE ? OR person LIKE ? OR date LIKE ?)
                       ORDER BY date DESC''', (user_id, f"%{keyword}%", f"%{keyword}%",f"%{keyword}%"))
        return cur.fetchall()

def search_all_events(keyword):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT e.*, u.username FROM events e
                       JOIN users u ON e.user_id = u.id
                       WHERE title LIKE ? OR person LIKE ?
                       ORDER BY date DESC''', (f"%{keyword}%", f"%{keyword}%"))
        return cur.fetchall()

def get_user_profile(user_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, image, theme FROM users WHERE id=?", (user_id,))
        return cur.fetchone()

def update_user_profile(user_id, theme, image=None):
    with connect_db() as conn:
        cur = conn.cursor()
        if image:
            cur.execute("UPDATE users SET image=?, theme=? WHERE id=?",
                        ( theme, image, user_id))
        else:
            cur.execute("UPDATE users SET theme=? WHERE id=?",
                        ( theme, user_id))
        conn.commit()

def get_admin_profile(admin_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT username, password, image, theme FROM admin WHERE id=?", (admin_id,))
    data = cur.fetchone()
    conn.close()
    return {
        "username": data[0],
        "password": data[1],
        "image": data[2],
        "theme": data[3]
    }

def update_admin_profile(admin_id, image, theme):
    conn = connect_db()
    cur = conn.cursor()
    if image:
        cur.execute("UPDATE admin SET image=?, theme=? WHERE id=?", ( image, theme, admin_id))
    else:
        cur.execute("UPDATE admin SET theme=? WHERE id=?",( theme, admin_id))
    conn.commit()
    conn.close()

def get_user_theme(user_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT theme FROM users WHERE id=?", (user_id,))
        result = cur.fetchone()
        return result[0] if result else "light"

def get_admin_theme(admin_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT theme FROM admin WHERE id=?", (admin_id,))
        result = cur.fetchone()
        return result[0] if result else "light"

def get_all_users():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        return cur.fetchall()

def delete_user(user_id):
    with connect_db() as conn:
        cur = conn.cursor()
        # Delete user and all their events
        cur.execute("DELETE FROM events WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

def reset_user_password(user_id, hashed_password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()

def get_user_by_id(user_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cur.fetchone()

def update_user_password(user_id, hashed_password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()

# Get admin password hash by ID
def get_admin_password(admin_id):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password FROM admin WHERE id = ?", (admin_id,))
        row = cur.fetchone()
        return row[0] if row else None

# Update admin password by ID
def update_admin_password(admin_id, hashed_password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE admin SET password = ? WHERE id = ?", (hashed_password, admin_id))
        conn.commit()
