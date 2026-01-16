# utils/database.py
"""
Database utilities for Workforce Intelligence System
- SQLite backend
- Tables: users, employees, tasks, mood_logs, feedback, attendance, notifications, projects
- Safe, future-ready for analytics & reporting
"""

import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

DB_NAME = "workforce.db"


# --------------------------
# DB Connection
# --------------------------
def connect_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# --------------------------
# Password Hashing
# --------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# --------------------------
# Initialize All Tables
# --------------------------
def initialize_all_tables():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        Emp_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT,
        Age INTEGER,
        Gender TEXT,
        Department TEXT,
        Role TEXT,
        Skills TEXT,
        Join_Date TEXT,
        Resign_Date TEXT,
        Status TEXT,
        Salary REAL,
        Location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT,
        emp_id INTEGER,
        assigned_by TEXT,
        due_date TEXT,
        priority TEXT,
        status TEXT,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        mood_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        mood TEXT,
        remarks TEXT,
        log_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT,
        rating INTEGER,
        log_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        date TEXT,
        check_in TEXT,
        check_out TEXT,
        status TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        message TEXT,
        type TEXT DEFAULT 'General',
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        owner_emp_id INTEGER,
        status TEXT,
        progress INTEGER DEFAULT 0,
        start_date TEXT,
        due_date TEXT
    )
    """)

    conn.commit()
    conn.close()


# --------------------------
# AUTH
# --------------------------
def get_user_by_username(username: str):
    conn = connect_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_default_admin():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            ("admin", hash_password("admin123"), "Admin")
        )
    conn.commit()
    conn.close()


def get_emp_id_by_user_id(user_id: int):
    """
    Safely fetch Emp_ID mapped to a user.
    Returns None if not found.
    """
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT Emp_ID FROM employees LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# --------------------------
# EMPLOYEES
# --------------------------
def add_employee(emp: dict):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO employees
        (Name, Age, Gender, Department, Role, Skills, Join_Date, Resign_Date, Status, Salary, Location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        emp.get("Name"),
        emp.get("Age"),
        emp.get("Gender"),
        emp.get("Department"),
        emp.get("Role"),
        emp.get("Skills"),
        emp.get("Join_Date"),
        emp.get("Resign_Date", ""),
        emp.get("Status", "Active"),
        emp.get("Salary", 0),
        emp.get("Location", ""),
    ))
    conn.commit()
    conn.close()


def fetch_employees():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM employees", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_employee(emp_id: int, updates: dict):
    if not updates:
        return
    conn = connect_db()
    cur = conn.cursor()
    for key, val in updates.items():
        cur.execute(f"UPDATE employees SET {key}=? WHERE Emp_ID=?", (val, emp_id))
    conn.commit()
    conn.close()


# --------------------------
# TASKS
# --------------------------
def fetch_tasks():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM tasks", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# --------------------------
# MOOD
# --------------------------
def add_mood_entry(emp_id: int, mood: str, remarks=""):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO mood_logs (emp_id,mood,remarks,log_date) VALUES (?,?,?,?)",
        (emp_id, mood, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_mood_logs():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM mood_logs", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# --------------------------
# FEEDBACK
# --------------------------
def add_feedback(sender_id, receiver_id, message, rating):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (sender_id,receiver_id,message,rating,log_date) VALUES (?,?,?,?,?)",
        (sender_id, receiver_id, message, rating, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_feedback():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM feedback", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def update_feedback(feedback_id, message, rating):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE feedback SET message=?, rating=? WHERE feedback_id=?",
        (message, rating, feedback_id)
    )
    conn.commit()
    conn.close()


def delete_feedback(feedback_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM feedback WHERE feedback_id=?", (feedback_id,))
    conn.commit()
    conn.close()


# --------------------------
# ATTENDANCE
# --------------------------
def add_attendance(emp_id, date, check_in, check_out, status):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (emp_id,date,check_in,check_out,status) VALUES (?,?,?,?,?)",
        (emp_id, date, check_in, check_out, status)
    )
    conn.commit()
    conn.close()


def fetch_attendance(emp_id=None):
    conn = connect_db()
    try:
        if emp_id:
            df = pd.read_sql("SELECT * FROM attendance WHERE emp_id=?", conn, params=(emp_id,))
        else:
            df = pd.read_sql("SELECT * FROM attendance", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# --------------------------
# NOTIFICATIONS
# --------------------------
def add_notification(emp_id, message, notif_type="General"):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (emp_id,message,type,created_at) VALUES (?,?,?,?)",
        (emp_id, message, notif_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def fetch_notifications(emp_id=None):
    if emp_id is None:
        emp_id = 0
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT notif_id AS id,
                   emp_id,
                   message,
                   type,
                   is_read,
                   created_at
            FROM notifications
            WHERE emp_id=?
            ORDER BY created_at DESC
            """,
            conn,
            params=(emp_id,)
        )
        if not df.empty:
            df["title"] = "Notification"
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def mark_notification_read(notif_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE notif_id=?", (notif_id,))
    conn.commit()
    conn.close()


def delete_notification(notif_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE notif_id=?", (notif_id,))
    conn.commit()
    conn.close()


# --------------------------
# PROJECTS
# --------------------------
def fetch_projects():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT * FROM projects", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df
# --------------------------
# BULK INSERT FUNCTIONS (CSV IMPORT)
# --------------------------

def bulk_add_attendance(df):
    """
    Import attendance records from a DataFrame.
    Required columns: emp_id, date, check_in, check_out, status
    """
    import sqlite3
    conn = sqlite3.connect("workforce.db")
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO attendance (emp_id, date, check_in, check_out, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            int(row['emp_id']),
            row['date'],
            row['check_in'],
            row['check_out'],
            row['status']
        ))
    conn.commit()
    conn.close()


def bulk_add_employees(df):
    """
    Import employee records from a DataFrame.
    Required columns: emp_id, name, role, status
    """
    import sqlite3
    conn = sqlite3.connect("workforce.db")
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO employees (Emp_ID, Name, Role, Status)
            VALUES (?, ?, ?, ?)
        """, (
            int(row['emp_id']),
            row['name'],
            row['role'],
            row['status']
        ))
    conn.commit()
    conn.close()


def bulk_add_feedback(df):
    """
    Import feedback records from a DataFrame.
    Required columns: sender_id, receiver_id, message, rating, log_date
    """
    import sqlite3
    conn = sqlite3.connect("workforce.db")
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO feedback (sender_id, receiver_id, message, rating, log_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            int(row['sender_id']) if row['sender_id'] else None,
            int(row['receiver_id']),
            row['message'],
            int(row['rating']),
            row['log_date']
        ))
    conn.commit()
    conn.close()


def bulk_add_notifications(df):
    """
    Import notifications from a DataFrame.
    Required columns: id, title, message, type, is_read, created_at
    """
    import sqlite3
    conn = sqlite3.connect("workforce.db")
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO notifications (id, title, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(row['id']),
            row['title'],
            row['message'],
            row['type'],
            int(row['is_read']),
            row['created_at']
        ))
    conn.commit()
    conn.close()
