# utils/database.py

import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

DB_NAME = "workforce.db"

# --------------------------
# DB Connection
# --------------------------
def connect_db():
    """Return a SQLite connection."""
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# --------------------------
# Password Hashing Helper
# --------------------------
def hash_password(password: str) -> str:
    """Return SHA256 hash of a password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# --------------------------
# Initialize All Tables
# --------------------------
def initialize_all_tables():
    conn = connect_db()
    cur = conn.cursor()

    # Users (Auth)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Employees
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

    # Tasks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT,
        emp_id INTEGER,
        assigned_by TEXT,
        due_date TEXT,
        priority TEXT,
        status TEXT,
        remarks TEXT,
        FOREIGN KEY(emp_id) REFERENCES employees(Emp_ID)
    )
    """)

    # Mood Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        mood_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        mood TEXT,
        remarks TEXT,
        log_date TEXT,
        FOREIGN KEY(emp_id) REFERENCES employees(Emp_ID)
    )
    """)

    # Feedback
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT,
        rating INTEGER,
        log_date TEXT,
        FOREIGN KEY(sender_id) REFERENCES employees(Emp_ID),
        FOREIGN KEY(receiver_id) REFERENCES employees(Emp_ID)
    )
    """)

    # Attendance
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        date TEXT,
        check_in TEXT,
        check_out TEXT,
        status TEXT,
        FOREIGN KEY(emp_id) REFERENCES employees(Emp_ID)
    )
    """)

    # Notifications
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(emp_id) REFERENCES employees(Emp_ID)
    )
    """)

    conn.commit()
    conn.close()


# --------------------------
# AUTH HELPERS
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
    """Create default admin if no users exist."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, ("admin", hash_password("admin123"), "Admin"))
    conn.commit()
    conn.close()


# --------------------------
# EMPLOYEES CRUD
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
        emp.get("Location")
    ))
    conn.commit()
    conn.close()


def fetch_employees():
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM employees", conn)
    conn.close()
    return df


def update_employee(emp_id: int, updates: dict):
    conn = connect_db()
    cur = conn.cursor()
    for k, v in updates.items():
        cur.execute(f"UPDATE employees SET {k}=? WHERE Emp_ID=?", (v, emp_id))
    conn.commit()
    conn.close()


def delete_employee(emp_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE Emp_ID=?", (emp_id,))
    conn.commit()
    conn.close()


# --------------------------
# TASKS CRUD
# --------------------------
def add_task(task: dict):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks
        (task_name, emp_id, assigned_by, due_date, priority, status, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        task.get("task_name"),
        task.get("emp_id"),
        task.get("assigned_by"),
        task.get("due_date"),
        task.get("priority"),
        task.get("status", "Pending"),
        task.get("remarks", "")
    ))
    conn.commit()
    conn.close()


def fetch_tasks():
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM tasks", conn)
    conn.close()
    return df


def update_task(task_id: int, updates: dict):
    conn = connect_db()
    cur = conn.cursor()
    for k, v in updates.items():
        cur.execute(f"UPDATE tasks SET {k}=? WHERE task_id=?", (v, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
    conn.commit()
    conn.close()


# --------------------------
# MOOD TRACKER
# --------------------------
def add_mood_entry(emp_id: int, mood: str, remarks: str = ""):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mood_logs (emp_id, mood, remarks, log_date)
        VALUES (?, ?, ?, ?)
    """, (emp_id, mood, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def fetch_mood_logs():
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM mood_logs", conn)
    conn.close()
    return df


def fetch_mood():
    df = fetch_mood_logs()
    if df.empty:
        return df
    emp_map = fetch_employees().set_index("Emp_ID")["Name"].to_dict()
    df["username"] = df["emp_id"].map(emp_map).fillna(df["emp_id"].astype(str))
    df["date"] = pd.to_datetime(df["log_date"], errors="coerce")
    return df


# --------------------------
# FEEDBACK
# --------------------------
def add_feedback(sender_id: int, receiver_id: int, message: str, rating: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback (sender_id, receiver_id, message, rating, log_date)
        VALUES (?, ?, ?, ?, ?)
    """, (sender_id, receiver_id, message, rating, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def fetch_feedback():
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM feedback", conn)
    conn.close()
    return df


def delete_feedback(feedback_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM feedback WHERE feedback_id=?", (feedback_id,))
    conn.commit()
    conn.close()


# --------------------------
# ATTENDANCE
# --------------------------
def add_attendance(emp_id: int, date: str, check_in: str, check_out: str, status: str):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO attendance (emp_id, date, check_in, check_out, status)
        VALUES (?, ?, ?, ?, ?)
    """, (emp_id, date, check_in, check_out, status))
    conn.commit()
    conn.close()


def fetch_attendance(emp_id=None):
    conn = connect_db()
    if emp_id:
        df = pd.read_sql("SELECT * FROM attendance WHERE emp_id=?", conn, params=(emp_id,))
    else:
        df = pd.read_sql("SELECT * FROM attendance", conn)
    conn.close()
    return df


# --------------------------
# NOTIFICATIONS
# --------------------------
def add_notification(emp_id: int, message: str):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notifications (emp_id, message, created_at)
        VALUES (?, ?, ?)
    """, (emp_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def fetch_notifications(emp_id: int):
    conn = connect_db()
    df = pd.read_sql("SELECT * FROM notifications WHERE emp_id=? ORDER BY created_at DESC", conn, params=(emp_id,))
    conn.close()
    return df


def mark_notification_read(notif_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE notif_id=?", (notif_id,))
    conn.commit()
    conn.close()
