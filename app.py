"""
Workforce Intelligence System
- Role-based workforce analytics platform
- Modular architecture
- Streamlit native pages
- 2026–2028 ready
"""

import streamlit as st
import pandas as pd
import datetime
import random

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Workforce Intelligence System",
    page_icon="🏢",
    layout="wide"
)

# -------------------------
# Local utilities
# -------------------------
from utils import database as db
from utils.auth import require_login, logout_user, show_role_badge

# -------------------------
# Initialize Database
# -------------------------
try:
    db.initialize_all_tables()
    db.create_default_admin()
except Exception as e:
    st.error("❌ Database initialization failed")
    st.exception(e)
    st.stop()

# -------------------------
# Authentication
# -------------------------
require_login()
role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "Unknown")

# -------------------------
# Sidebar (after login)
# -------------------------
if st.session_state.get("logged_in"):
    with st.sidebar:
        st.title("🏢 Workforce System")
        st.write(f"👤 **{username}**")
        show_role_badge()
        st.divider()
        logout_user()  # single logout button

# -------------------------
# Load Employees
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    df = pd.DataFrame()
    st.error("❌ Failed to load employees.")
    st.exception(e)

# -------------------------
# Auto-generate demo employees if DB empty
# -------------------------
if df.empty:
    st.info("Generating demo workforce data...")

    def generate_employees(n=80):
        depts = ["HR", "IT", "Sales", "Finance", "Marketing", "Support"]
        roles = {
            "HR": ["HR Manager", "HR Executive"],
            "IT": ["Developer", "SysAdmin", "IT Manager"],
            "Sales": ["Sales Executive", "Sales Manager"],
            "Finance": ["Accountant", "Finance Manager"],
            "Marketing": ["Marketing Executive", "Marketing Manager"],
            "Support": ["Support Executive", "Support Manager"]
        }
        skills = [
            "Python", "SQL", "Excel", "Power BI",
            "Communication", "Leadership", "Analytics", "JavaScript"
        ]

        names_m = ["John", "Alex", "Michael", "David", "Chris", "Liam"]
        names_f = ["Sophia", "Emma", "Chloe", "Ava", "Mia", "Isabella"]

        employees = []
        for _ in range(n):
            gender = random.choice(["Male", "Female"])
            name = random.choice(names_m if gender == "Male" else names_f)
            dept = random.choice(depts)

            employees.append({
                "Name": name,
                "Age": random.randint(22, 60),
                "Gender": gender,
                "Department": dept,
                "Role": random.choice(roles[dept]),
                "Skills": ", ".join(random.sample(skills, 3)),
                "Join_Date": (
                    datetime.datetime.now() - datetime.timedelta(days=random.randint(200, 3000))
                ).strftime("%Y-%m-%d"),
                "Resign_Date": "",
                "Status": "Active",
                "Salary": random.randint(30000, 120000),
                "Location": random.choice(
                    ["Bangalore", "Delhi", "Mumbai", "Chennai", "Hyderabad"]
                )
            })

        return pd.DataFrame(employees)

    gen_df = generate_employees()
    for _, row in gen_df.iterrows():
        db.add_employee(row.to_dict())

    st.success("✅ Demo workforce created successfully")
    st.rerun()


# -------------------------
# Dashboard Metrics
# -------------------------
st.title("📊 Workforce Intelligence Dashboard")
st.caption("Central overview of workforce data")

c1, c2, c3 = st.columns(3)
c1.metric("Total Employees", len(df))
c2.metric("Active Employees", (df["Status"] == "Active").sum())
c3.metric("Departments", df["Department"].nunique())

st.subheader("👩‍💼 Recent Employees")
st.dataframe(
    df[["Emp_ID", "Name", "Department", "Role", "Status", "Join_Date"]]
    .sort_values("Join_Date", ascending=False)
    .head(10),
    use_container_width=True
)

st.info(
    "📂 Use the **left sidebar** to navigate modules like Tasks, Attendance, "
    "Mood Tracker, Projects, Analytics, Feedback, Skills & Roles, and Notifications."
)
